import binascii
import logging
import machine
import network
import time

log = logging.getLogger('network')

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
            log.info('No credentials found')
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

        log.info('Access point IP address: %s', ap.ifconfig()[0])

    def connect_to_network(self, wlan, ssid, password, timeout_s=15) -> bool:
        """Attempts to connect to network by returning True or False

        :param wlan: The WLAN object to be connected to
        :param ssid: The SSID to connect to
        :param password: The password to connect to
        :param timeout_s: Timeout for connecting to network
        :return: True if the connection was successful, False otherwise
        """
        if not wlan.isconnected():
            log.info('Attempting to connect to network with SSID %s', ssid)
            network.hostname(self._built_hostname())
            wlan.disconnect()
            wlan.connect(ssid, password)

            # Wait for connection
            for _ in range(timeout_s * 2):
                if wlan.isconnected():
                    break
                time.sleep(0.5)

        if wlan.isconnected():
            log.info('Connected to network, IP address: %s', wlan.ifconfig()[0])
            return True
        else:
            log.warning('Failed to connect to network with SSID: %s, WLAN status: %s', ssid, wlan.status())
            return False

    def _built_hostname(self) -> str:
        """Builds a unique hostname from the chip's unique ID

        :return: A unique hostname like 'plant-sensor-cf9278'
        """
        # Last 3 bytes in hex (6 chars)
        suffix = binascii.hexlify(machine.unique_id()[-3:]).decode()
        return f'{self.HOSTNAME}-{suffix}'
        