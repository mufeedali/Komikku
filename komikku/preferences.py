# Copyright (C) 2019-2021 Valéry Febvre
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
from komikku.utils import KeyringHelper


@Gtk.Template.from_resource('/info/febvre/Komikku/ui/preferences_window.ui')
class PreferencesWindow(Handy.PreferencesWindow):
    __gtype_name__ = 'PreferencesWindow'

    parent = NotImplemented
    settings = NotImplemented

    theme_switch = Gtk.Template.Child('theme_switch')
    night_light_switch = Gtk.Template.Child('night_light_switch')
    desktop_notifications_switch = Gtk.Template.Child('desktop_notifications_switch')

    update_at_startup_switch = Gtk.Template.Child('update_at_startup_switch')
    new_chapters_auto_download_switch = Gtk.Template.Child('new_chapters_auto_download_switch')
    nsfw_content_switch = Gtk.Template.Child('nsfw_content_switch')
    servers_languages_actionrow = Gtk.Template.Child('servers_languages_actionrow')
    servers_languages_subpage = Gtk.Template.Child('servers_languages_subpage')
    servers_languages_subpage_close_button = Gtk.Template.Child('servers_languages_subpage_close_button')
    servers_languages_subpage_group = Gtk.Template.Child('servers_languages_subpage_group')
    servers_settings_actionrow = Gtk.Template.Child('servers_settings_actionrow')
    servers_settings_subpage = Gtk.Template.Child('servers_settings_subpage')
    servers_settings_subpage_close_button = Gtk.Template.Child('servers_settings_subpage_close_button')
    servers_settings_subpage_group = Gtk.Template.Child('servers_settings_subpage_group')
    long_strip_detection_switch = Gtk.Template.Child('long_strip_detection_switch')

    reading_mode_row = Gtk.Template.Child('reading_mode_row')
    scaling_row = Gtk.Template.Child('scaling_row')
    background_color_row = Gtk.Template.Child('background_color_row')
    borders_crop_switch = Gtk.Template.Child('borders_crop_switch')
    fullscreen_switch = Gtk.Template.Child('fullscreen_switch')

    credentials_storage_plaintext_fallback_switch = Gtk.Template.Child('credentials_storage_plaintext_fallback_switch')

    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.settings = Settings.get_default()

    def open(self, action, param):
        self.set_transient_for(self.parent)
        self.set_config_values()
        self.present()

    def on_background_color_changed(self, row, param):
        index = row.get_selected_index()

        if index == 0:
            self.settings.background_color = 'white'
        elif index == 1:
            self.settings.background_color = 'black'

    def on_borders_crop_changed(self, switch_button, gparam):
        self.settings.borders_crop = switch_button.get_active()

    def on_credentials_storage_plaintext_fallback_changed(self, switch_button, gparam):
        self.settings.credentials_storage_plaintext_fallback = switch_button.get_active()

    def on_desktop_notifications_changed(self, switch_button, gparam):
        if switch_button.get_active():
            self.settings.desktop_notifications = True
        else:
            self.settings.desktop_notifications = False

    def on_fullscreen_changed(self, switch_button, gparam):
        self.settings.fullscreen = switch_button.get_active()

    def on_long_strip_detection_changed(self, switch_button, gparam):
        self.settings.long_strip_detection = switch_button.get_active()

    def on_new_chapters_auto_download_changed(self, switch_button, gparam):
        if switch_button.get_active():
            self.settings.new_chapters_auto_download = True
        else:
            self.settings.new_chapters_auto_download = False

    def on_night_light_changed(self, switch_button, gparam):
        self.settings.night_light = switch_button.get_active()

        self.parent.init_theme()

    def on_nsfw_content_changed(self, switch_button, gparam):
        if switch_button.get_active():
            self.settings.nsfw_content = True
        else:
            self.settings.nsfw_content = False

    def on_reading_mode_changed(self, row, param):
        index = row.get_selected_index()

        if index == 0:
            self.settings.reading_mode = 'right-to-left'
        elif index == 1:
            self.settings.reading_mode = 'left-to-right'
        elif index == 2:
            self.settings.reading_mode = 'vertical'
        elif index == 3:
            self.settings.reading_mode = 'webtoon'

    def on_scaling_changed(self, row, param):
        index = row.get_selected_index()

        if index == 0:
            self.settings.scaling = 'screen'
        elif index == 1:
            self.settings.scaling = 'width'
        elif index == 2:
            self.settings.scaling = 'height'
        elif index == 3:
            self.settings.scaling = 'original'

    def on_servers_language_activated(self, switch_button, gparam, code):
        if switch_button.get_active():
            self.settings.add_servers_language(code)
        else:
            self.settings.remove_servers_language(code)

    def on_theme_changed(self, switch_button, gparam):
        self.settings.dark_theme = switch_button.get_active()

        self.parent.init_theme()

    def on_update_at_startup_changed(self, switch_button, gparam):
        if switch_button.get_active():
            self.settings.update_at_startup = True
        else:
            self.settings.update_at_startup = False

    def set_config_values(self):
        #
        # General
        #

        # Dark theme
        self.theme_switch.set_active(self.settings.dark_theme)
        self.theme_switch.connect('notify::active', self.on_theme_changed)

        # Night light
        self.night_light_switch.set_active(self.settings.night_light)
        self.night_light_switch.connect('notify::active', self.on_night_light_changed)

        # Desktop notifications
        self.desktop_notifications_switch.set_active(self.settings.desktop_notifications)
        self.desktop_notifications_switch.connect('notify::active', self.on_desktop_notifications_changed)

        #
        # Library
        #

        # Update manga at startup
        self.update_at_startup_switch.set_active(self.settings.update_at_startup)
        self.update_at_startup_switch.connect('notify::active', self.on_update_at_startup_changed)

        # Auto download new chapters
        self.new_chapters_auto_download_switch.set_active(self.settings.new_chapters_auto_download)
        self.new_chapters_auto_download_switch.connect('notify::active', self.on_new_chapters_auto_download_changed)

        # Servers languages
        PreferencesServersLanguagesSubpage(self)

        # Servers settings
        PreferencesServersSettingsSubpage(self)

        # Long strip detection
        self.long_strip_detection_switch.set_active(self.settings.long_strip_detection)
        self.long_strip_detection_switch.connect('notify::active', self.on_long_strip_detection_changed)

        # NSFW content
        self.nsfw_content_switch.set_active(self.settings.nsfw_content)
        self.nsfw_content_switch.connect('notify::active', self.on_nsfw_content_changed)

        #
        # Reader
        #

        # Reading mode
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('⬅ Right to Left')))
        liststore.insert(1, Handy.ValueObject.new(_('➡ Left to Right')))
        liststore.insert(2, Handy.ValueObject.new(_('⬇ Vertical')))
        liststore.insert(3, Handy.ValueObject.new(_('⬇ Webtoon')))

        self.reading_mode_row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        self.reading_mode_row.set_selected_index(self.settings.reading_mode_value)
        self.reading_mode_row.connect('notify::selected-index', self.on_reading_mode_changed)

        # Image scaling
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('Adapt to Screen')))
        liststore.insert(1, Handy.ValueObject.new(_('Adapt to Width')))
        liststore.insert(2, Handy.ValueObject.new(_('Adapt to Height')))
        liststore.insert(3, Handy.ValueObject.new(_('Original Size')))

        self.scaling_row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        self.scaling_row.set_selected_index(self.settings.scaling_value)
        self.scaling_row.connect('notify::selected-index', self.on_scaling_changed)

        # Background color
        liststore = Gio.ListStore.new(Handy.ValueObject)
        liststore.insert(0, Handy.ValueObject.new(_('White')))
        liststore.insert(1, Handy.ValueObject.new(_('Black')))

        self.background_color_row.bind_name_model(liststore, Handy.ValueObject.dup_string)
        self.background_color_row.set_selected_index(self.settings.background_color_value)
        self.background_color_row.connect('notify::selected-index', self.on_background_color_changed)

        # Borders crop
        self.borders_crop_switch.set_active(self.settings.borders_crop)
        self.borders_crop_switch.connect('notify::active', self.on_borders_crop_changed)

        # Full screen
        self.fullscreen_switch.set_active(self.settings.fullscreen)
        self.fullscreen_switch.connect('notify::active', self.on_fullscreen_changed)

        #
        # Advanced
        #

        # Credentials storage: allow plaintext as fallback
        self.credentials_storage_plaintext_fallback_switch.set_active(self.settings.credentials_storage_plaintext_fallback)
        self.credentials_storage_plaintext_fallback_switch.connect('notify::active', self.on_credentials_storage_plaintext_fallback_changed)


class PreferencesServersLanguagesSubpage:
    parent = NotImplemented
    settings = NotImplemented

    def __init__(self, parent):
        self.parent = parent
        self.settings = Settings.get_default()

        self.parent.servers_languages_subpage_close_button.connect('clicked', self.close)
        self.parent.servers_languages_actionrow.props.activatable = True
        self.parent.servers_languages_actionrow.connect('activated', self.present)

        servers_languages = self.settings.servers_languages

        for code, language in LANGUAGES.items():
            action_row = Handy.ActionRow()
            action_row.set_title(language)
            action_row.set_activatable(True)

            switch = Gtk.Switch.new()
            switch.set_valign(Gtk.Align.CENTER)
            switch.set_halign(Gtk.Align.CENTER)
            switch.set_active(code in servers_languages)
            switch.connect('notify::active', self.on_language_activated, code)
            action_row.add(switch)
            action_row.set_activatable_widget(switch)
            action_row.show_all()

            self.parent.servers_languages_subpage_group.add(action_row)

    def close(self, _widget):
        self.parent.close_subpage()

    def on_language_activated(self, switch_button, gparam, code):
        if switch_button.get_active():
            self.settings.add_servers_language(code)
        else:
            self.settings.remove_servers_language(code)

    def present(self, _widget):
        self.parent.present_subpage(self.parent.servers_languages_subpage)


class PreferencesServersSettingsSubpage:
    parent = NotImplemented
    settings = NotImplemented

    def __init__(self, parent):
        self.parent = parent
        self.settings = Settings.get_default()
        self.keyring_helper = KeyringHelper()

        self.parent.servers_settings_subpage_close_button.connect('clicked', self.close)
        self.parent.servers_settings_actionrow.props.activatable = True
        self.parent.servers_settings_actionrow.connect('activated', self.present)

    def close(self, _widget):
        self.parent.close_subpage()

    def present(self, _widget):
        settings = self.settings.servers_settings
        languages = self.settings.servers_languages
        credentials_storage_plaintext_fallback = self.settings.credentials_storage_plaintext_fallback

        servers_data = {}
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
            has_login = getattr(server_class, 'has_login')

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

                self.parent.servers_settings_subpage_group.add(expander_row)

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

                        vbox.add(hbox)

                if has_login:
                    frame = Gtk.Frame()
                    vbox.add(frame)

                    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=12, spacing=12)
                    frame.add(box)

                    label = Gtk.Label(_('User Account'))
                    label.set_valign(Gtk.Align.CENTER)
                    box.pack_start(label, True, True, 0)

                    if server_class.base_url is None:
                        # Server has a customizable address/base_url (ex. Komga)
                        address_entry = Gtk.Entry()
                        address_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'network-server-symbolic')
                        box.pack_start(address_entry, True, True, 0)
                    else:
                        address_entry = None

                    username_entry = Gtk.Entry()
                    username_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'avatar-default-symbolic')
                    box.pack_start(username_entry, True, True, 0)

                    password_entry = Gtk.Entry()
                    password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
                    password_entry.set_visibility(False)
                    password_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'dialog-password-symbolic')
                    box.pack_start(password_entry, True, True, 0)

                    plaintext_checkbutton = None
                    if self.keyring_helper.is_disabled or not self.keyring_helper.has_recommended_backend:
                        label = Gtk.Label()
                        label.set_line_wrap(True)
                        if self.keyring_helper.is_disabled:
                            label.get_style_context().add_class('dim-label')
                            label.set_text(_('System keyring service is disabled. Credential cannot be saved.'))
                            box.pack_start(label, False, False, 0)
                        elif not self.keyring_helper.has_recommended_backend:
                            if not credentials_storage_plaintext_fallback:
                                plaintext_checkbutton = Gtk.CheckButton.new()
                                label.set_text(_('No keyring backends were found to store credential. Use plaintext storage as fallback.'))
                                plaintext_checkbutton.add(label)
                                box.pack_start(plaintext_checkbutton, False, False, 0)
                            else:
                                label.get_style_context().add_class('dim-label')
                                label.set_text(_('No keyring backends were found to store credential. Plaintext storage will be used as fallback.'))
                                box.pack_start(label, False, False, 0)

                    btn = Gtk.Button(_('Test'))
                    btn.connect(
                        'clicked', self.save_credential,
                        server_main_id, server_class, username_entry, password_entry, address_entry, plaintext_checkbutton
                    )
                    btn.set_always_show_image(True)
                    box.pack_start(btn, False, False, 0)

                    credential = self.keyring_helper.get(server_main_id)
                    if credential:
                        if address_entry is not None:
                            address_entry.set_text(credential.address)
                        username_entry.set_text(credential.username)
                        password_entry.set_text(credential.password)
            else:
                action_row = Handy.ActionRow()
                action_row.set_title(server_data['name'])

                switch = Gtk.Switch.new()
                switch.set_active(server_enabled)
                switch.set_valign(Gtk.Align.CENTER)
                switch.set_halign(Gtk.Align.CENTER)
                switch.connect('notify::active', self.on_server_activated, server_main_id)
                action_row.set_activatable_widget(switch)
                action_row.add(switch)

                self.parent.servers_settings_subpage_group.add(action_row)

        self.parent.servers_settings_subpage_group.show_all()
        self.parent.present_subpage(self.parent.servers_settings_subpage)

    def on_server_activated(self, widget, gparam, server_main_id):
        if isinstance(widget, Handy.ExpanderRow):
            self.settings.toggle_server(server_main_id, widget.get_enable_expansion())
        else:
            self.settings.toggle_server(server_main_id, widget.get_active())

    def on_server_language_activated(self, switch_button, gparam, server_main_id, lang):
        self.settings.toggle_server_lang(server_main_id, lang, switch_button.get_active())

    def save_credential(self, button, server_main_id, server_class, username_entry, password_entry, address_entry, plaintext_checkbutton):
        username = username_entry.get_text()
        password = password_entry.get_text()
        if address_entry is not None:
            address = address_entry.get_text().strip()
            if not address.startswith(('http://', 'https://')):
                return

            server = server_class(username=username, password=password, address=address)
        else:
            address = None
            server = server_class(username=username, password=password)

        if server.logged_in:
            button.set_image(Gtk.Image.new_from_icon_name('object-select-symbolic', Gtk.IconSize.MENU))
            if self.keyring_helper.is_disabled or plaintext_checkbutton is not None and not plaintext_checkbutton.get_active():
                return

            if plaintext_checkbutton is not None and plaintext_checkbutton.get_active():
                # Save user agrees to save credentials in plaintext
                self.parent.credentials_storage_plaintext_fallback_switch.set_active(True)

            self.keyring_helper.store(server_main_id, username, password, address)
        else:
            button.set_image(Gtk.Image.new_from_icon_name('computer-fail-symbolic', Gtk.IconSize.MENU))
