from gettext import gettext as _

from gi.repository import Gtk
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
        settings_theme_switch = self.builder.get_object('settings_theme_switch')
        settings_theme_switch.connect('notify::active', self.on_settings_theme_switch_switched)
        settings_theme_switch_value = mangascan.config_manager.get_dark_theme()
        settings_theme_switch.set_active(settings_theme_switch_value)

        settings_reading_direction_switch = self.builder.get_object('settings_reading_direction_switch')
        settings_reading_direction_switch.connect('notify::active', self.on_settings_reading_direction_switch_switched)
        settings_reading_direction_switch_value = mangascan.config_manager.get_reading_direction()
        settings_reading_direction_switch.set_active(settings_reading_direction_switch_value)

    def on_settings_theme_switch_switched(self, switch_button, gparam):
        gtk_settings = Gtk.Settings.get_default()

        if switch_button.get_active():
            mangascan.config_manager.set_dark_theme(True)
            gtk_settings.set_property('gtk-application-prefer-dark-theme', True)
        else:
            mangascan.config_manager.set_dark_theme(False)
            gtk_settings.set_property('gtk-application-prefer-dark-theme', False)

    def on_settings_reading_direction_switch_switched(self, switch_button, gparam):
        if switch_button.get_active():
            mangascan.config_manager.set_reading_direction('left-to-right')
            self.builder.get_object('settings_reading_direction_description_label').set_text(_('From left to right'))
        else:
            mangascan.config_manager.set_reading_direction('right-to-left')
            self.builder.get_object('settings_reading_direction_description_label').set_text(_('From right to left'))
