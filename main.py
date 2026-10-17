import sys

from src.connectivity.network import Network
from src.server.WebServer import WebServer
from src.store.ConfigStore import ConfigStore

sys.path.insert(0, '/src')

if __name__ == "__main__":
    config_store = ConfigStore()
    network_manager = Network(config_store)

    if network_manager.connect_saved_network():
        print('Device is connected to the network, starting telemetry...')
    else:
        print('Starting provisioning...')
        network_manager.create_access_point()
        WebServer(network_manager, config_store).start()




