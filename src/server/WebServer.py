import json
import machine
import network
import select
import socket
import time

from src.connectivity.mqtt_manager import MqttManager
from src.server.DnsServer import DnsServer

class WebServer:
    SERVER_PORT = 80
    STATUS_IDLE = 'idle'
    STATUS_CONNECTING = 'connecting'
    STATUS_CONNECTED = 'connected'
    STATUS_FAILED = 'failed'

    PORTAL_IP = '192.168.4.1'
    PORTAL_URL = f'http://{PORTAL_IP}/'

    API_ENDPOINT = '/api'

    POLL_TIMEOUT_MS = 500
    RESTART_DELAY_MS = 5_000

    def __init__(self, network_manager, config_store) -> None:
        self.network_manager = network_manager
        self.config_store = config_store
        self.pending_config = None
        self.failure_reason = None
        self.restart_at = None
        self.connection_status = self.STATUS_IDLE

    def start(self) -> None:
        """Run the server loop, handling one client at a time

        Servers both the web page (TCP) and the DNS answers (UDP) of the captive portal
        """
        server_socket = self._setup_web_server()
        routes = self._configure_servers_assets()

        dns_server = DnsServer(self.PORTAL_IP)
        dns_socket = dns_server.start()

        # Wakes up when either socket has something to read
        poller = select.poll()
        poller.register(server_socket, select.POLLIN)
        poller.register(dns_socket, select.POLLIN)

        print(f'Web server listening on port {self.SERVER_PORT}')

        while True:
            for ready_socket, _ in poller.poll(self.POLL_TIMEOUT_MS):
                if ready_socket == dns_socket:
                    dns_server.handle()
                else:
                    self._handle_client(server_socket, routes)

            if self.pending_config is not None:
                config = self.pending_config
                self.pending_config = None
                self._try_connect(config)

            if self._should_restart():
                machine.reset()

    def _setup_web_server(self) -> socket.socket:
        """Create the listening TCP socket on SERVER_PORT

        :return: The server socket ready for accept()
        """
        print("Starting web server...")

        # Create a web-server with TCP over IPv4
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Allow rebinding the port right after a restart, instead of failing with EADDRINUSE
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # '' all interfaces, allowing clients on the AP to reach the server
        server_socket.bind(('', self.SERVER_PORT))

        # How many connection can wait in the queue while one is being server
        server_socket.listen(5)
        return server_socket

    def _handle_client(self, server_socket, routes) -> None:
        """Accept one client and server its request

        :param server_socket: The listening socket that has a client waiting
        :param routes: Maps a path to (file_path, content_type) for static files
        """
        conn, _ = server_socket.accept()
        conn.settimeout(5)  # Limits how long recv()/sendall() on this client may wait

        try:
            method, path, body = self._read_request(conn)
            self._handle_request(method, path, body, routes, conn)
        except Exception as error:
            print(f'HTTP server error: {error}')
        finally:
            conn.close()

    def _handle_request(self, method, path, body, routes, conn) -> None:
        """Route a parsed HTTP request to the matching handler

        :param method: HTTP verb (e.g. 'GET' or 'POST')
        :param path: Requested path (e.g. '/api/status')
        :param body: Request body as a string, empty for GET requests
        :param routes: Maps a path to (file_path, content_type) for static files
        :param conn: The client socket returned by accept()
        """
        # Form submission from the setup page
        if method == 'POST' and path == f'{self.API_ENDPOINT}/setup':
            self._handle_setup(conn, body)
            return

        # Polled by the frontend for connection result
        if method == 'GET' and path == f'{self.API_ENDPOINT}/status':
            self._handle_status(conn)
            return

        # Unknown GET paths include the connectivity check of the phones, sends them to set up page
        if method == 'GET' and path not in routes:
            self._send_redirect(conn, self.PORTAL_URL)
            return

        if method != 'GET':
            self._send_not_found(conn)
            return

        file_path, content_type = routes[path]

        try:
            file = open(file_path, 'rb')
        except OSError:
            self._send_not_found(conn)
            return

        with file:
            self.send_response(conn, '200 OK', content_type)
            self._send_file(conn, file)

    def _handle_setup(self, conn, body) -> None:
        """Handles POST /setup: validate the credentials and queue a connection attempt

        :param conn: The client socket retuned by accept()
        :param body: The request body expected '{"wifi": {...}, "mqtt": {...}, "sensor": {...}}'
        """
        try:
            form = json.loads(body)
        except ValueError:
            # Malformed JSON
            self.send_response(conn, '400 Bad Request', 'text/plain')
            conn.sendall(b'Invalid JSON')
            return

        if not isinstance(form, dict):
            self.send_response(conn, "400 Bad Request", "text/plain")
            conn.sendall(b'Expected a JSON object')
            return

        wifi = self._parse_wifi(form)
        mqtt = self._parse_mqtt(form)
        sensor = self._parse_sensor(form)

        if wifi is None or mqtt is None or sensor is None:
            self.send_response(conn, '400 Bad Request', 'text/plain')
            conn.sendall(b'Missing required fields')
            return

        self.pending_config = {'wifi': wifi, 'mqtt': mqtt, 'sensor': sensor}
        self.failure_reason = None
        self.connection_status = self.STATUS_CONNECTING
        self.send_response(conn, '202 Accepted', 'text/plain')
        conn.sendall(b'Connecting')

    def _handle_status(self, conn) -> None:
        """Handles GET /status with a 200 HTTP status code and the status and the failure reason in JSON"""
        payload = json.dumps({
            'status': self.connection_status,
            'reason': self.failure_reason
        })
        self.send_response(conn, '200 OK', 'application/json')
        conn.sendall(payload.encode())

    def _try_connect(self, config) -> None:
        """Attempts to establish a connection to the Wi-Fi network and saves the config on success"""
        wlan = network.WLAN(network.WLAN.IF_STA)
        wlan.active(True)

        wifi = config['wifi']

        try:
            connected = self.network_manager.connect_to_network(wlan, wifi['ssid'], wifi['password'])
        except OSError as error:
            print(f'Wi-Fi connect error: {error}')
            connected = False

        if not connected:
            wlan.active(False)
            self._fail('wifi')
            return

        if not self._test_mqtt(config['mqtt']):
            wlan.active(False)
            self._fail('mqtt')
            return

        self.config_store.save_config('mqtt', config['mqtt'])
        self.config_store.save_config('sensor', config['sensor'])
        self.config_store.save_config('wifi', wifi)
        self.connection_status = self.STATUS_CONNECTED
        self.restart_at = time.ticks_add(time.ticks_ms(), self.RESTART_DELAY_MS)

    def _should_restart(self) -> bool:
        """Whether the restart deadline set after as successful setup has passed"""
        return self.restart_at is not None and time.ticks_diff(time.ticks_ms(), self.restart_at) >= 0

    @staticmethod
    def _parse_wifi(form) -> dict | None:
        """Return the validated wifi section or None"""
        wifi = form.get('wifi') if isinstance(form, dict) else None

        if not isinstance(wifi, dict) or not wifi.get('ssid') or not wifi.get('password'):
            return None

        return { 'ssid': wifi['ssid'], 'password': wifi['password'] }

    @staticmethod
    def _parse_mqtt(form) -> dict | None:
        """Return the validated mqtt section or None"""
        mqtt = form.get('mqtt') if isinstance(form, dict) else None

        if not isinstance(mqtt, dict) or not mqtt.get('server'):
            return None

        try:
            port = int(mqtt.get('port', 1883))
        except (TypeError, ValueError):
            return None

        return {
            'server': mqtt['server'],
            'port': port,
            'username': mqtt.get('username', ''),
            'password': mqtt.get('password', ''),
        }

    @staticmethod
    def _parse_sensor(form) -> dict | None:
        """Return the validated sensor section or None"""
        sensor = form.get('sensor') if isinstance(form, dict) else None

        if not isinstance(sensor, dict) or not sensor.get('plant_name'):
            return None

        return { 'plant_name': sensor['plant_name'] }

    @staticmethod
    def _test_mqtt(mqtt_config) -> bool:
        """Checks that the broker accepts the given MQTT settings"""
        mqtt = MqttManager.from_config(mqtt_config)

        if not mqtt.connect():
            return False

        mqtt.disconnect()
        return True

    def _fail(self, reason) -> None:
        """Marks the setup as failed and tracks which part failed"""
        self.connection_status = self.STATUS_FAILED
        self.failure_reason = reason

    @staticmethod
    def _configure_servers_assets() -> dict[str, tuple[str, str]]:
        """Map each public URL path to the static file that servers it

        :return: A dictionary of path -> (file path on the device, MIME type)
        """
        return {
            '/': ('/src/web/index.html', 'text/html'),
            '/style.css': ('/src/web/style.css', 'text/css'),
            '/app.js': ('/src/web/app.js', 'application/javascript')
        }

    @staticmethod
    def _read_request(conn) -> tuple[str, str, str]:
        """Read one full HTTP request from the client socket

        :param conn: The client socket returned by accept()
        :return: A (method, path, body) tuple, with the body decoded to a string
        """
        data = b''

        # Keep reading until the blank line that ends the header arrived
        while b'\r\n\r\n' not in data:
            chunk = conn.recv(512)

            if not chunk:
                break
            data += chunk

        head, _, body = data.partition(b'\r\n\r\n')
        lines = head.decode().split('\r\n')

        # First line (GET /status HTTP/1.1)
        method, path, _ = lines[0].split(' ', 2)

        # Remaining lines (Content-Length: 42)
        headers = {}
        for line in lines[1:]:
            key, _, value = line.partition(':')
            headers[key.strip().lower()] = value.strip()

        # Read the rest of the body
        length = int(headers.get('content-length', 0))
        while len(body) < length:
            chunk = conn.recv(512)
            if not chunk:
                break
            body += chunk
        return method, path, body.decode()

    @staticmethod
    def _send_redirect(conn, location) -> None:
        """Send a 302 redirect, which makes the phone open the setup page

        :param conn: The client socket returned by accept()
        :param location: The full URL the client should go
        """
        response = (
            'HTTP/1.0 302 Found\r\n'
            f'Location: {location}\r\n'
            'Connection: close\r\n'
            '\r\n'
        )
        conn.sendall(response.encode())

    @staticmethod
    def send_response(conn, status, content_type):
        """Send the HTTP status line and headers to the client

        The body is not sent here, the caller sends it afterward

        :param conn: The client socket returned by accept()
        :param status: Status code and reason (`e.g. '200 OK')
        :param content_type: MIME type (`e.g. 'text/html')
        """
        response = (
            f'HTTP/1.0 {status}\r\n'
            f'Content-Type: {content_type}; charset=utf-8\r\n'
            'Connection: close\r\n'
            '\r\n'
        )

        conn.sendall(response.encode())

    def _send_not_found(self, conn) -> None:
        """Send a 404 not found response with a body response"""
        self.send_response(conn, '404 Not Found', 'text/plain')
        conn.sendall(b'404 Not Found\r\n')

    @staticmethod
    def _send_file(conn, file) -> None:
        """Stream an open file to the client in small chunks

        :param conn: The client socket returned by accept()
        :param file: A file object opened in binary mode ('rb')
        """
        while True:
            chunk = file.read(512)

            if not chunk:
                break

            conn.sendall(chunk)