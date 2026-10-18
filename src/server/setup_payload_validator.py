class SetupPayloadValidator:
    DEFAULT_MQTT_PORT = 1883

    @classmethod
    def validate(cls, form) -> dict | None:
        """Validate the setup payload and return the clean config or None

        :param form: The decoded JSON body of POST
        :return: A dict with the wifi, mqtt and sensor section, or None if invalid
        """
        if not isinstance(form, dict):
            return None

        wifi = cls._validate_wifi(form.get('wifi'))
        mqtt = cls._validate_mqtt(form.get('mqtt'))
        sensor = cls._validate_sensor(form.get('sensor'))

        if wifi is None or mqtt is None or sensor is None:
            return None

        return {'wifi': wifi, 'mqtt': mqtt, 'sensor': sensor}

    @staticmethod
    def _validate_wifi(wifi) -> dict | None:
        if not isinstance(wifi, dict) or not wifi.get('ssid') or not wifi.get('password'):
            return None

        return {'ssid': wifi.get('ssid'), 'password': wifi.get('password')}

    @classmethod
    def _validate_mqtt(cls, mqtt) -> dict | None:
        if not isinstance(mqtt, dict) or not mqtt.get('server'):
            return None

        try:
            port = int(mqtt.get('port', cls.DEFAULT_MQTT_PORT))
        except (TypeError, ValueError):
            return None

        if not 1 <= port <= 65535:
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
            return None

        return {'plant_name': sensor.get('plant_name')}