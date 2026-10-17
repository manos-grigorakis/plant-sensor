import sys

from src.connectivity.network import Network
from src.server.WebServer import WebServer
from src.store.ConfigStore import ConfigStore
from machine import Pin, I2C
from src.sensors.bh1750 import BH1750

sys.path.insert(0, '/src')

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
    else:
        print('Starting provisioning...')
        network_manager.create_access_point()
        WebServer(network_manager, config_store).start()




