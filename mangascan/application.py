import gi
import logging
import sys

gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '0.0')
gi.require_version('Notify', '0.7')

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Handy
from gi.repository import Notify

from mangascan.main_window import MainWindow


class Application(Gtk.Application):
    development_mode = False
    application_id = 'com.gitlab.valos.MangaScan'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id=self.application_id, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        GLib.set_application_name('Manga Scan')
        GLib.set_prgname('Manga Scan')

        Notify.init('Manga Scan')

        # Register LibHandy Responsive Column
        GObject.type_register(Handy.Column)

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(application=self, title='Manga Scan', icon_name=self.application_id)
            self.window.application = self

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

    def add_actions(self):
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.on_quit_menu_clicked)
        self.add_action(quit_action)

        self.window.add_actions()

    def add_accelerators(self):
        self.window.add_accelerators()

    def on_quit_menu_clicked(self, action, param):
        self.quit()


if __name__ == '__main__':
    app = Application()
    app.run(sys.argv)
