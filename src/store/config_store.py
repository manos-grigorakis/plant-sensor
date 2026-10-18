import json
import logging
import os

log = logging.getLogger('config-store')

class ConfigStore:
    CONFIG_PATH = '/config.json'
    CONFIG_TMP_PATH = '/config.tmp'

    def save_config(self, section, data) -> None:
        """Save or update a configuration section"""
        config = self.load_config() or {}
        config[section] = data

        with open(self.CONFIG_TMP_PATH, 'w') as file:
            json.dump(config, file)

        try:
            os.remove(self.CONFIG_PATH)
        except OSError:
            pass

        os.rename(self.CONFIG_TMP_PATH, self.CONFIG_PATH)
        log.info('Configuration section %s saved successfully', section)

    def load_config(self, section = None) -> dict | None:
        """Load all configuration or a specific section"""
        try:
            with open(self.CONFIG_PATH, 'r') as file:
                config = json.load(file)
        except OSError:
            log.debug('Configuration file not found')
            return None
        except ValueError as error:
            log.error('Invalid JSON configuration file, %s', error)
            return None

        if section is None:
            return config

        return config.get(section)