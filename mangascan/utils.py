from gi.repository import Gio


def network_is_available():
    # https://developer.puri.sm/Librem5/Apps/Examples/Networking/NetworkState/index.html
    return Gio.NetworkMonitor.get_default().get_connectivity() == Gio.NetworkConnectivity.FULL
