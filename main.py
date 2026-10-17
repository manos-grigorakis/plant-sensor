import sys

from src.connectivity.network import Network
from src.server.WebServer import WebServer
from src.store.ConfigStore import ConfigStore
from machine import Pin, I2C, ADC
from src.sensors.bh1750 import BH1750
from src.sensors.soil_moisture import SoilMoisture

sys.path.insert(0, '/src')

# Used for moisture sensor
AIR_VALUE = 52_000
WATER_VALUE = 29_400

def init_moisture_sensor():
    adc = ADC(Pin(1))
    moisture_sensor = SoilMoisture(AIR_VALUE, WATER_VALUE, adc)
    print(moisture_sensor.classify_moisture())

def init_lux_sensor():
    # Create I2C peripheral at frequency of 100kHz
    i2c = I2C(0, freq=100_000, sda=Pin(23), scl=Pin(24))

    lux_sensor = BH1750(i2c)
    print(f'Light: {lux_sensor.read_lux():.2f} lux')

if __name__ == "__main__":
    config_store = ConfigStore()
    network_manager = Network(config_store)

    if network_manager.connect_saved_network():
        print('Device is connected to the network, starting telemetry...')
        init_lux_sensor()
        init_moisture_sensor()
    else:
        print('Starting provisioning...')
        network_manager.create_access_point()
        WebServer(network_manager, config_store).start()




