from gettext import gettext as _
import gi
import logging
import sys

gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '0.0')
gi.require_version('Notify', '0.7')

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Handy
from gi.repository import Notify

from mangascan.main_window import MainWindow


class Application(Gtk.Application):
    connected = False
    development_mode = False
    application_id = 'info.febvre.MangaScan'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id=self.application_id, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.window = None

    def add_actions(self):
        self.window.add_actions()

    def add_accelerators(self):
        self.window.add_accelerators()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        GLib.set_application_name(_('MangaScan'))
        GLib.set_prgname(self.application_id)

        Handy.init()
        Notify.init('MangaScan')

        Gio.NetworkMonitor.get_default().connect('network-changed', self.on_network_status_changed)

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(application=self, title='MangaScan', icon_name=self.application_id)

            self.add_accelerators()
            self.add_actions()

        self.window.present()

    def get_logger(self):
        logger = logging.getLogger()

        if self.development_mode is True:
            logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%d-%m-%y %H:%M:%S', level=logging.DEBUG)
        else:
            logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%d-%m-%y %H:%M:%S', level=logging.INFO)

        return logger

    def on_network_status_changed(self, monitor, connected):
        self.connected = connected


if __name__ == '__main__':
    app = Application()
    app.run(sys.argv)
