import binascii
import machine
import network
import time

class Network:
    AP_SSID = 'Plant-Sensor'
    AP_PASSWORD = 'plant-setup-1234'
    HOSTNAME = 'plant-sensor'

    def __init__(self, config_store) -> None:
        self.config_store = config_store

    def connect_saved_network(self) -> bool:
        """Attempts to connect using the saved credentials saved in flash

        :return: True if connected, False otherwise (no credentials or attempt failed)
        """
        credentials = self.config_store.load_config("wifi")

        if credentials is None:
            print('No saved credentials found')
            return False

        ssid = credentials['ssid']
        password = credentials['password']

        # Station mode (the device joins an existing network as client)
        wlan = network.WLAN(network.WLAN.IF_STA)
        wlan.active(True)

        if self.connect_to_network(wlan, ssid, password):
            return True

        # Release the radio so the AP can take over
        wlan.active(False)
        return False

    def create_access_point(self) -> None:
        """Creates and configures a new access point for the setup page"""
        # Initialize Wi-Fi in Access Point mode
        ap = network.WLAN(network.WLAN.IF_AP)

        ap.config(ssid=self.AP_SSID, password=self.AP_PASSWORD, security=network.WLAN.SEC_WPA2, max_clients=5)
        ap.active(True)

        print(f'AP IP: {ap.ifconfig()[0]}')

    def connect_to_network(self, wlan, ssid, password, timeout_s=15) -> bool:
        """Attempts to connect to network by returning True or False

        :param wlan: The WLAN object to be connected to
        :param ssid: The SSID to connect to
        :param password: The password to connect to
        :param timeout_s: Timeout for connecting to network
        :return: True if the connection was successful, False otherwise
        """
        if not wlan.isconnected():
            print('Connecting to network...')
            network.hostname(self._built_hostname())
            wlan.disconnect()
            wlan.connect(ssid, password)

            # Wait for connection
            for _ in range(timeout_s * 2):
                if wlan.isconnected():
                    break
                time.sleep(0.5)

        if wlan.isconnected():
            print(f'IP Address: {wlan.ifconfig()[0]}')
            return True
        else:
            print(f'Failed to connect, WLAN status: {wlan.status()}')
            return False

    def _built_hostname(self) -> str:
        """Builds a unique hostname from the chip's unique ID

        :return: A unique hostname like 'plant-sensor-cf9278'
        """
        # Last 3 bytes in hex (6 chars)
        suffix = binascii.hexlify(machine.unique_id()[-3:]).decode()
        return f'{self.HOSTNAME}-{suffix}'
    
    @staticmethod
    def _scan_available_wlans(wlan) -> None:
        """Scans for available WLAN networks and prints them out

        :param wlan: The WLAN object to be scanned
        """
        print('Scanning for available WLANs...')

        for idx, item in enumerate(wlan.scan()):
            ssid = item[0].decode("utf-8")
            mac = ":".join(f"{byte:02X}" for byte in item[1])

            print(f'{idx} SSID: {ssid} | MAC: {mac} | Channel: {item[2]} | Hidden: {item[5]}')
        