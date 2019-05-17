from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Handy
import mangascan.config_manager


class SettingsDialog():
    window = NotImplemented
    builder = NotImplemented

    def __init__(self, window):
        self.window = window
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/com/gitlab/valos/MangaScan/settings_dialog.ui')

    def open(self, action, param):
        settings_dialog = self.builder.get_object('settings_dialog')

        settings_dialog.set_modal(True)
        settings_dialog.set_transient_for(self.window)
        settings_dialog.present()

        self.set_config_values()

    def set_config_values(self):
        #
        # General
        #

        # Dark theme
        settings_theme_switch = self.builder.get_object('settings_theme_switch')
        settings_theme_switch.connect('notify::active', self.on_theme_changed)
        settings_theme_switch.set_active(mangascan.config_manager.get_dark_theme())

        #
        # Reader
        #

        # Reading direction
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('Right to left')))
        liststore.insert(1, Handy.ValueObject.new(_('Left to right')))

        row = self.builder.get_object('settings_reading_direction_row')
        row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        row.set_selected_index(mangascan.config_manager.get_reading_direction(nick=False))
        row.connect('notify::selected-index', self.on_reading_direction_changed)

        # Image scaling
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('Adjust to screen')))
        liststore.insert(1, Handy.ValueObject.new(_('Adjust to width')))
        liststore.insert(2, Handy.ValueObject.new(_('Adjust to height')))

        row = self.builder.get_object('settings_scaling_row')
        row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        row.set_selected_index(mangascan.config_manager.get_scaling(nick=False))
        row.connect('notify::selected-index', self.on_scaling_changed)

        # Full screen
        settings_fullscreen_switch = self.builder.get_object('settings_fullscreen_switch')
        settings_fullscreen_switch.connect('notify::active', self.on_fullscreen_changed)
        settings_fullscreen_switch.set_active(mangascan.config_manager.get_fullscreen())

    def on_fullscreen_changed(self, switch_button, gparam):
        if switch_button.get_active():
            mangascan.config_manager.set_fullscreen(True)
        else:
            mangascan.config_manager.set_fullscreen(False)

    def on_reading_direction_changed(self, row, param):
        index = row.get_selected_index()

        if index == 0:
            mangascan.config_manager.set_reading_direction('right-to-left')
        elif index == 1:
            mangascan.config_manager.set_reading_direction('left-to-right')

    def on_scaling_changed(self, row, param):
        index = row.get_selected_index()

        if index == 0:
            mangascan.config_manager.set_scaling('screen')
        elif index == 1:
            mangascan.config_manager.set_scaling('width')
        elif index == 2:
            mangascan.config_manager.set_scaling('height')

    def on_theme_changed(self, switch_button, gparam):
        gtk_settings = Gtk.Settings.get_default()

        if switch_button.get_active():
            mangascan.config_manager.set_dark_theme(True)
            gtk_settings.set_property('gtk-application-prefer-dark-theme', True)
        else:
            mangascan.config_manager.set_dark_theme(False)
            gtk_settings.set_property('gtk-application-prefer-dark-theme', False)
