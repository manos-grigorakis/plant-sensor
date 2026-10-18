import logging

log = logging.getLogger('validator')

class SetupPayloadValidator:
    DEFAULT_MQTT_PORT = 1883

    @classmethod
    def validate(cls, form) -> dict | None:
        """Validate the setup payload and return the clean config or None

        :param form: The decoded JSON body of POST
        :return: A dict with the wifi, mqtt and sensor section, or None if invalid
        """
        if not isinstance(form, dict):
            log.warning('Setup payload is not a JSON object')
            return None

        wifi = cls._validate_wifi(form.get('wifi'))
        mqtt = cls._validate_mqtt(form.get('mqtt'))
        sensor = cls._validate_sensor(form.get('sensor'))

        if wifi is None or mqtt is None or sensor is None:
            return None

        log.debug('Setup payload is valid')
        return {'wifi': wifi, 'mqtt': mqtt, 'sensor': sensor}

    @staticmethod
    def _validate_wifi(wifi) -> dict | None:
        if not isinstance(wifi, dict):
            log.warning('Missing wifi section')
            return None

        if not wifi.get('ssid') or not wifi.get('password'):
            log.warning('Wifi section missing ssid or password')
            return None

        return {'ssid': wifi.get('ssid'), 'password': wifi.get('password')}

    @classmethod
    def _validate_mqtt(cls, mqtt) -> dict | None:
        if not isinstance(mqtt, dict):
            log.warning('Missing MQTT section')
            return None

        if not mqtt.get('server'):
            log.warning('MQTT section is missing server')
            return None

        try:
            port = int(mqtt.get('port', cls.DEFAULT_MQTT_PORT))
        except (TypeError, ValueError):
            log.warning('MQTT section is not a number')
            return None

        if not 1 <= port <= 65535:
            log.warning('MQTT port number %s is out of range', port)
            return None

        return {
            'server': mqtt['server'],
            'port': port,
            'username': mqtt.get('username') or '',
            'password': mqtt.get('password') or '',
        }

    @staticmethod
    def _validate_sensor(sensor) -> dict | None:
        if not isinstance(sensor, dict) or not sensor.get('plant_name'):
            log.warning('Sensor section is missing plant_name')
            return None

        return {'plant_name': sensor.get('plant_name')}