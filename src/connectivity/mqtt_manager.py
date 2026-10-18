import json

from binascii import hexlify
from machine import unique_id
from umqtt.simple import MQTTClient

class MqttManager:
    def __init__(self, server, port, username, password) -> None:
        self.client_id = b'plant-sensor-' + hexlify(unique_id())
        self.device_id = self.client_id.decode()

        self.telemetry_topic = (b'plant-sensor/' + self.client_id + b'/telemetry')
        self.client = MQTTClient(self.client_id, server, port, username, password)

    def connect(self) -> bool:
        """Connect to the MQTT broker"""
        try:
            print(f'Connecting to MQTT broker ...')
            self.client.connect()
            return True
        except Exception as error:
            print(f'MQTT connection failed: {error}')
            return False

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker"""
        self.client.disconnect()

    def publish_discovery(self, device_name) -> None:
        """Publish discovery message to MQTT broker"""
        sensors = {
            "light": {
                "name": "Light",
                "device_class": "illuminance",
                "unit_of_measurement": "lx",
                "value_template": "{{ value_json.light.lux }}"
            },
            "moisture": {
                "name": "Soil Moisture",
                "device_class": "moisture",
                "unit_of_measurement": "%",
                "value_template": "{{ value_json.moisture.moisture_percentage }}"
            }
        }

        for key, sensor in sensors.items():
            config = {
                "name": sensor["name"],
                "unique_id": "{}_{}".format(self.device_id, key),
                "state_topic": self.telemetry_topic.decode(),
                "value_template": sensor["value_template"],
                "device_class": sensor["device_class"],
                "state_class": "measurement",
                "unit_of_measurement": sensor["unit_of_measurement"],
                "device": {
                    "identifiers": [self.device_id],
                    "name": device_name,
                    "manufacturer": "Seeed Studio",
                    "model": "XIAO ESP32-C5",
                }
            }

            topic = "homeassistant/sensor/{}_{}{}".format(self.device_id, key, "/config")
            print(f'Publishing discovery message to {topic}')
            self.client.publish(topic.encode(), json.dumps(config).encode(), retain=True)

    def publish_telemetry(self, light, moisture) -> None:
        """Publish light and moisture telemetry to MQTT broker"""
        payload = {
            "light": light,
            "moisture": moisture
        }

        print(f'Publishing telemetry to {self.telemetry_topic}')
        self.client.publish(self.telemetry_topic, json.dumps(payload).encode())

    @classmethod
    def from_config(cls, mqtt_config):
        return cls(
            mqtt_config['server'],
            mqtt_config['port'],
            mqtt_config['username'] or None,
            mqtt_config['password'] or None
        )