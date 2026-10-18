import sys
import machine

sys.path.insert(0, '/src')

from src.connectivity.network import Network
from src.server.WebServer import WebServer
from src.store.ConfigStore import ConfigStore
from machine import Pin, I2C, ADC
from src.sensors.bh1750 import BH1750
from src.sensors.soil_moisture import SoilMoisture
from src.connectivity.mqtt_manager import MqttManager

DEBUG = True
SLEEP_INTERVAL_MS = 60_000

# Used for moisture sensor
AIR_VALUE = 52_000
WATER_VALUE = 29_400

def read_moisture_sensor():
    adc = ADC(Pin(1))
    moisture_sensor = SoilMoisture(AIR_VALUE, WATER_VALUE, adc)
    return moisture_sensor.classify_moisture()

def read_lux_sensor():
    # Create I2C peripheral at frequency of 100kHz
    i2c = I2C(0, freq=100_000, sda=Pin(23), scl=Pin(24))

    lux_sensor = BH1750(i2c)
    return lux_sensor.classify_light()

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
            finally:
                mqtt.disconnect()

        if DEBUG:
            print('Entering deep sleep for 60 seconds...')
        else:
            machine.deepsleep(SLEEP_INTERVAL_MS)
    else:
        print('Starting provisioning...')
        network_manager.create_access_point()
        WebServer(network_manager, config_store).start()