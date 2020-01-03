# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Handy

from komikku.models import Settings
from komikku.servers import LANGUAGES


class SettingsDialog():
    window = NotImplemented
    builder = NotImplemented

    def __init__(self, window):
        self.window = window
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/info/febvre/Komikku/ui/settings_dialog.ui')

    def open(self, action, param):
        settings_dialog = self.builder.get_object('settings_dialog')

        settings_dialog.set_modal(True)
        settings_dialog.set_transient_for(self.window)
        settings_dialog.present()

        self.set_config_values()

    def set_config_values(self):
        settings = Settings.get_default()

        #
        # General
        #

        # Dark theme
        settings_theme_switch = self.builder.get_object('settings_theme_switch')
        settings_theme_switch.set_active(settings.dark_theme)
        settings_theme_switch.connect('notify::active', self.on_theme_changed)

        # Night light
        settings_night_light_switch = self.builder.get_object('settings_night_light_switch')
        settings_night_light_switch.set_active(settings.night_light)
        settings_night_light_switch.connect('notify::active', self.on_night_light_changed)

        #
        # Library
        #

        # Update manga at startup
        settings_update_at_startup_switch = self.builder.get_object('settings_update_at_startup_switch')
        settings_update_at_startup_switch.set_active(settings.update_at_startup)
        settings_update_at_startup_switch.connect('notify::active', self.on_update_at_startup_changed)

        # Servers languages
        servers_languages = settings.servers_languages

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_border_width(12)

        for code, language in LANGUAGES.items():
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

            label = Gtk.Label(language, xalign=0)
            hbox.pack_start(label, True, True, 0)

            switch = Gtk.Switch.new()
            switch.set_active(code in servers_languages)
            switch.connect('notify::active', self.on_servers_language_activated, code)
            hbox.pack_start(switch, False, False, 0)

            vbox.pack_start(hbox, True, True, 0)

        vbox.show_all()
        self.builder.get_object('settings_servers_languages_row').add(vbox)

        #
        # Reader
        #

        # Reading direction
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('Right to left ←')))
        liststore.insert(1, Handy.ValueObject.new(_('Left to right →')))
        liststore.insert(2, Handy.ValueObject.new(_('Vertical ↓')))

        row = self.builder.get_object('settings_reading_direction_row')
        row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        row.set_selected_index(settings.reading_direction_value)
        row.connect('notify::selected-index', self.on_reading_direction_changed)

        # Image scaling
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('Adapt to screen')))
        liststore.insert(1, Handy.ValueObject.new(_('Adapt to width')))
        liststore.insert(2, Handy.ValueObject.new(_('Adapt to height')))

        row = self.builder.get_object('settings_scaling_row')
        row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        row.set_selected_index(settings.scaling_value)
        row.connect('notify::selected-index', self.on_scaling_changed)

        # Background color
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('White')))
        liststore.insert(1, Handy.ValueObject.new(_('Black')))

        row = self.builder.get_object('settings_background_color_row')
        row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        row.set_selected_index(settings.background_color_value)
        row.connect('notify::selected-index', self.on_background_color_changed)

        # Full screen
        settings_fullscreen_switch = self.builder.get_object('settings_fullscreen_switch')
        settings_fullscreen_switch.set_active(settings.fullscreen)
        settings_fullscreen_switch.connect('notify::active', self.on_fullscreen_changed)

    def on_background_color_changed(self, row, param):
        index = row.get_selected_index()

        if index == 0:
            Settings.get_default().background_color = 'white'
        elif index == 1:
            Settings.get_default().background_color = 'black'

    def on_fullscreen_changed(self, switch_button, gparam):
        Settings.get_default().fullscreen = switch_button.get_active()

    def on_night_light_changed(self, switch_button, gparam):
        Settings.get_default().night_light = switch_button.get_active()

        self.window.init_theme()

    def on_reading_direction_changed(self, row, param):
        index = row.get_selected_index()

        if index == 0:
            Settings.get_default().reading_direction = 'right-to-left'
        elif index == 1:
            Settings.get_default().reading_direction = 'left-to-right'
        elif index == 2:
            Settings.get_default().reading_direction = 'vertical'

    def on_scaling_changed(self, row, param):
        index = row.get_selected_index()

        if index == 0:
            Settings.get_default().scaling = 'screen'
        elif index == 1:
            Settings.get_default().scaling = 'width'
        elif index == 2:
            Settings.get_default().scaling = 'height'

    def on_servers_language_activated(self, switch_button, gparam, code):
        if switch_button.get_active():
            Settings.get_default().add_servers_language(code)
        else:
            Settings.get_default().remove_servers_language(code)

    def on_theme_changed(self, switch_button, gparam):
        Settings.get_default().dark_theme = switch_button.get_active()

        self.window.init_theme()

    def on_update_at_startup_changed(self, switch_button, gparam):
        if switch_button.get_active():
            Settings.get_default().update_at_startup = True
        else:
            Settings.get_default().update_at_startup = False
