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

from komikku.main_window import MainWindow


class Application(Gtk.Application):
    development_mode = False
    application_id = 'info.febvre.Komikku'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id=self.application_id, flags=Gio.ApplicationFlags.FLAGS_NONE, **kwargs)
        self.window = None

    def add_actions(self):
        self.window.add_actions()

    def add_accelerators(self):
        self.window.add_accelerators()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        GLib.set_application_name(_('Komikku'))
        GLib.set_prgname(self.application_id)

        Handy.init()
        Notify.init(_('Komikku'))

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(application=self, title='Komikku', icon_name=self.application_id)

            self.add_accelerators()
            self.add_actions()

        self.window.present()

    def get_logger(self):
        logging.basicConfig(
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%d-%m-%y %H:%M:%S',
            level=logging.DEBUG if self.development_mode else logging.INFO,
        )
        logger = logging.getLogger()

        return logger


if __name__ == '__main__':
    app = Application()
    app.run(sys.argv)
