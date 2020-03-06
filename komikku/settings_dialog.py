# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Handy

from komikku.models import Settings
from komikku.servers import get_server_main_id_by_id
from komikku.servers import get_servers_list
from komikku.servers import LANGUAGES
from komikku.utils import SecretAccountHelper


class SettingsDialog():
    window = NotImplemented
    builder = NotImplemented

    def __init__(self, window):
        self.window = window
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/info/febvre/Komikku/ui/settings_dialog.ui')

    def open(self, action, param):
        self.settings_dialog = self.builder.get_object('settings_dialog')

        self.settings_dialog.set_modal(True)
        self.settings_dialog.set_transient_for(self.window)
        self.settings_dialog.present()

        self.servers_settings_dialog = SettingsServersDialog(self.settings_dialog)

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

        # Desktop notifications
        settings_desktop_notifications_switch = self.builder.get_object('settings_desktop_notifications_switch')
        settings_desktop_notifications_switch.set_active(settings.desktop_notifications)
        settings_desktop_notifications_switch.connect('notify::active', self.on_desktop_notifications_changed)

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
        self.builder.get_object('settings_servers_languages_expander_row').add(vbox)

        # Servers settings
        btn = Gtk.Button()
        btn.add(Gtk.Image.new_from_icon_name('emblem-system-symbolic', Gtk.IconSize.BUTTON))
        btn.set_valign(Gtk.Align.CENTER)
        btn.show_all()
        self.builder.get_object('settings_servers_settings_action_row').add_action(btn)
        btn.connect('clicked', self.show_servers_settings)

        #
        # Reader
        #

        # Reading direction
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('Right to Left ←')))
        liststore.insert(1, Handy.ValueObject.new(_('Left to Right →')))
        liststore.insert(2, Handy.ValueObject.new(_('Vertical ↓')))

        row = self.builder.get_object('settings_reading_direction_row')
        row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        row.set_selected_index(settings.reading_direction_value)
        row.connect('notify::selected-index', self.on_reading_direction_changed)

        # Image scaling
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('Adapt to Screen')))
        liststore.insert(1, Handy.ValueObject.new(_('Adapt to Width')))
        liststore.insert(2, Handy.ValueObject.new(_('Adapt to Height')))

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

        # Borders crop
        borders_crop_switch = self.builder.get_object('settings_borders_crop_switch')
        borders_crop_switch.set_active(settings.borders_crop)
        borders_crop_switch.connect('notify::active', self.on_borders_crop_changed)

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

    def on_borders_crop_changed(self, switch_button, gparam):
        Settings.get_default().borders_crop = switch_button.get_active()

    def on_desktop_notifications_changed(self, switch_button, gparam):
        if switch_button.get_active():
            Settings.get_default().desktop_notifications = True
        else:
            Settings.get_default().desktop_notifications = False

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

    def show_servers_settings(self, button):
        SettingsServersDialog(self.settings_dialog).open()


@Gtk.Template.from_resource('/info/febvre/Komikku/ui/settings_servers_dialog.ui')
class SettingsServersDialog(Handy.Dialog):
    __gtype_name__ = 'SettingsServersDialog'

    listbox = Gtk.Template.Child('listbox')
    parent = NotImplemented

    def __init__(self, parent):
        super(SettingsServersDialog, self).__init__(use_header_bar=True)
        self.parent = parent

    def open(self):
        def on_get_password(attributes, password, name, login_entry, password_entry):
            if not attributes or not password:
                return

            login_entry.set_text(attributes['login'])
            password_entry.set_text(password)

        self.get_header_bar().set_title(_('Servers Settings'))
        self.set_transient_for(self.parent)

        settings = Settings.get_default().servers_settings
        languages = Settings.get_default().servers_languages

        servers_data = dict()
        for server_data in get_servers_list(order_by=('name', 'lang')):
            main_id = get_server_main_id_by_id(server_data['id'])

            if main_id not in servers_data:
                servers_data[main_id] = dict(
                    main_id=main_id,
                    name=server_data['name'],
                    module=server_data['module'],
                    langs=[],
                )

            if not languages or server_data['lang'] in languages:
                servers_data[main_id]['langs'].append(server_data['lang'])

        for server_main_id, server_data in servers_data.items():
            if not server_data['langs']:
                continue

            server_class = getattr(server_data['module'], server_data['main_id'].capitalize())
            has_login = hasattr(server_class, 'login')

            server_settings = settings.get(server_main_id)
            server_enabled = server_settings is None or server_settings['enabled'] is True

            if len(server_data['langs']) > 1 or has_login:
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
                vbox.set_border_width(12)

                expander_row = Handy.ExpanderRow()
                expander_row.set_title(server_data['name'])
                expander_row.set_enable_expansion(server_enabled)
                expander_row.connect('notify::enable-expansion', self.on_server_activated, server_main_id)
                expander_row.add(vbox)

                self.listbox.add(expander_row)

                if len(server_data['langs']) > 1:
                    for lang in server_data['langs']:
                        lang_enabled = server_settings is None or server_settings['langs'].get(lang, True)

                        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

                        label = Gtk.Label(LANGUAGES[lang], xalign=0)
                        label.get_style_context().add_class('dim-label')
                        hbox.pack_start(label, True, True, 0)

                        switch = Gtk.Switch.new()
                        switch.set_active(lang_enabled)
                        switch.connect('notify::active', self.on_server_language_activated, server_main_id, lang)
                        hbox.pack_start(switch, False, False, 0)

                        vbox.pack_start(hbox, True, True, 0)

                if has_login:
                    frame = Gtk.Frame()
                    vbox.pack_start(frame, True, True, 0)

                    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
                    box.set_margin_top(6)
                    box.set_margin_right(6)
                    box.set_margin_bottom(6)
                    box.set_margin_left(6)
                    frame.add(box)

                    label = Gtk.Label('User Account')
                    label.set_valign(Gtk.Align.CENTER)
                    box.pack_start(label, True, True, 0)

                    login_entry = Gtk.Entry()
                    login_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'avatar-default-symbolic')
                    box.pack_start(login_entry, True, True, 0)

                    password_entry = Gtk.Entry()
                    password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
                    password_entry.set_visibility(False)
                    password_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'dialog-password-symbolic')
                    box.pack_start(password_entry, True, True, 0)

                    btn = Gtk.Button('Test')
                    btn.connect('clicked', self.test_account_login, server_main_id, server_class, login_entry, password_entry)
                    btn.set_always_show_image(True)
                    box.pack_start(btn, False, False, 0)

                    helper = SecretAccountHelper()
                    helper.get(server_main_id, on_get_password, login_entry, password_entry)
            else:
                action_row = Handy.ActionRow()
                action_row.set_title(server_data['name'])

                switch = Gtk.Switch.new()
                switch.set_active(server_enabled)
                switch.set_valign(Gtk.Align.CENTER)
                switch.connect('notify::active', self.on_server_activated, server_main_id)
                action_row.add_action(switch)

                self.listbox.add(action_row)

        self.listbox.show_all()

        if self.run() in (Gtk.ResponseType.CANCEL, Gtk.ResponseType.DELETE_EVENT, ):
            self.destroy()

    def on_server_activated(self, widget, gparam, server_main_id):
        if isinstance(widget, Handy.ExpanderRow):
            Settings.get_default().toggle_server(server_main_id, widget.get_enable_expansion())
        else:
            Settings.get_default().toggle_server(server_main_id, widget.get_active())

    def on_server_language_activated(self, switch_button, gparam, server_main_id, lang):
        Settings.get_default().toggle_server_lang(server_main_id, lang, switch_button.get_active())

    def test_account_login(self, button, server_main_id, server_class, login_entry, password_entry):
        def on_account_stored(source, result):
            server = server_class(login=login, password=password)

            if server.logged_in:
                button.set_image(Gtk.Image.new_from_icon_name('object-select-symbolic', Gtk.IconSize.MENU))
            else:
                button.set_image(Gtk.Image.new_from_icon_name('computer-fail-symbolic', Gtk.IconSize.MENU))

        login = login_entry.get_text()
        password = password_entry.get_text()

        helper = SecretAccountHelper()
        helper.clear(server_main_id, helper.store, server_main_id, login, password, on_account_stored)
