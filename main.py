import machine
import logging

from machine import Pin, I2C, ADC
from src.connectivity.network import Network
from src.server.web_server import WebServer
from src.store.config_store import ConfigStore
from src.sensors.bh1750 import BH1750
from src.sensors.soil_moisture import SoilMoisture
from src.connectivity.mqtt_manager import MqttManager

DEBUG = True
SLEEP_INTERVAL_MS = 60_000

# Logger configuration
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(levelname)-8s [%(name)s] %(message)s',
)

# Used for moisture sensor
AIR_VALUE = 52_000
WATER_VALUE = 29_400

log = logging.getLogger('main')

def read_moisture_sensor():
    adc = ADC(Pin(1))
    moisture_sensor = SoilMoisture(AIR_VALUE, WATER_VALUE, adc)

    result = moisture_sensor.classify_moisture()
    log.debug('Moisture sensor reading: %s', result)
    return result

def read_lux_sensor():
    # Create I2C peripheral at frequency of 100kHz
    i2c = I2C(0, freq=100_000, sda=Pin(23), scl=Pin(24))
    lux_sensor = BH1750(i2c)
    result = lux_sensor.classify_light()
    log.debug('Lux sensor reading: %s', result)
    return result

if __name__ == "__main__":
    config_store = ConfigStore()
    network_manager = Network(config_store)

    if network_manager.connect_saved_network():
        mqtt_config = config_store.load_config('mqtt')
        sensor_config = config_store.load_config('sensor')

        mqtt = MqttManager.from_config(mqtt_config)

        if mqtt.connect():
            try:
                mqtt.publish_discovery(sensor_config['plant_name'])
                mqtt.publish_telemetry(read_lux_sensor(), read_moisture_sensor())
            except Exception as error:
                log.exception('Sensor reading or MQTT publish failed')
            finally:
                try:
                    mqtt.disconnect()
                except OSError as error:
                    log.warning('MQTT disconnect failed: %s', error)

        if DEBUG:
            log.debug('DEBUG mode, skipping deep sleep')
        else:
            log.info('Entering deep sleep for %s ms', SLEEP_INTERVAL_MS)
            machine.deepsleep(SLEEP_INTERVAL_MS)
    else:
        log.info('Wi-Fi network not found. Starting provisioning captive portal')
        network_manager.create_access_point()
        WebServer(network_manager, config_store).start()