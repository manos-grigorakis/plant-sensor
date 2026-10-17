import json
import os

class ConfigStore:
    CONFIG_PATH = '/config.json'
    CONFIG_TMP_PATH = '/config.tmp'

    def save_credentials(self, ssid, password) -> None:
        """Save the Wi-Fi credentials to flash so they survive reboot"""
        # Write credentials to a temp file, protecting against power outages and file corruption
        with open(self.CONFIG_TMP_PATH, 'w') as file:
            json.dump({'ssid': ssid, 'password': password}, file)

        # Remove the existing config file
        try:
            os.remove(self.CONFIG_PATH)
        except OSError:
            # No previous config nothing to replace
            pass

        os.rename(self.CONFIG_TMP_PATH, self.CONFIG_PATH)

    def load_credentials(self) -> tuple[str, str] | None:
        """Loads the Wi-Fi from a file

        :return: The Wi-Fi credentials if exists, None otherwise
        """
        try:
            with open(self.CONFIG_PATH, 'r') as file:
                config = json.load(file)
        except(OSError, ValueError):
            # Missing file (OSError), corrupt JSON (ValueError)
            return None

        ssid = config['ssid']
        password = config['password']

        if not ssid or not password:
            return None

        return ssid, password