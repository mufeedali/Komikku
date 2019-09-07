# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import time

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository import Handy

from threading import Timer

from mangascan.add_dialog import AddDialog
import mangascan.config_manager
from mangascan.card import Card
from mangascan.downloader import Downloader
from mangascan.library import Library
from mangascan.model import backup_db
from mangascan.reader import Reader
from mangascan.settings_dialog import SettingsDialog
from mangascan.updater import Updater


class MainWindow(Gtk.ApplicationWindow):
    mobile_width = False
    page = None

    _is_maximized = False
    _is_fullscreen = False
    _prev_size = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.application = kwargs['application']

        self.logging_manager = self.application.get_logger()
        self.downloader = Downloader(self)
        self.updater = Updater(self)

        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/info/febvre/MangaScan/ui/main_window.ui')
        self.builder.add_from_resource('/info/febvre/MangaScan/ui/menu.xml')

        self.overlay = self.builder.get_object('overlay')
        self.stack = self.builder.get_object('stack')
        self.title_stack = self.builder.get_object('title_stack')

        self.assemble_window()

        if Gio.Application.get_default().development_mode is True:
            mangascan.config_manager.set_development_backup_mode(True)

    def add_accelerators(self):
        self.application.set_accels_for_action('app.settings', ['<Control>p'])
        self.application.set_accels_for_action('app.add', ['<Control>plus'])
        self.application.set_accels_for_action('app.fullscreen', ['F11'])

    def add_actions(self):
        add_action = Gio.SimpleAction.new('add', None)
        add_action.connect('activate', self.on_left_button_clicked)

        settings_action = Gio.SimpleAction.new('settings', None)
        settings_action.connect('activate', self.on_settings_menu_clicked)

        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about_menu_clicked)

        shortcuts_action = Gio.SimpleAction.new('shortcuts', None)
        shortcuts_action.connect('activate', self.on_shortcuts_menu_clicked)

        fullscreen_action = Gio.SimpleAction.new('fullscreen', None)
        fullscreen_action.connect('activate', self.toggle_fullscreen)

        self.application.add_action(add_action)
        self.application.add_action(settings_action)
        self.application.add_action(about_action)
        self.application.add_action(shortcuts_action)
        self.application.add_action(fullscreen_action)

        self.library.add_actions()
        self.card.add_actions()
        self.reader.add_actions()

    def assemble_window(self):
        # Default size
        window_size = mangascan.config_manager.get_window_size()
        self.set_default_size(window_size[0], window_size[1])

        # Min size
        geom = Gdk.Geometry()
        geom.min_width = 360
        geom.min_height = 288
        self.set_geometry_hints(None, geom, Gdk.WindowHints.MIN_SIZE)

        # Titlebar
        self.titlebar = self.builder.get_object('titlebar')
        self.headerbar = self.builder.get_object('headerbar')

        self.left_button = self.builder.get_object('left_button')
        self.left_button.connect('clicked', self.on_left_button_clicked, None)

        self.set_titlebar(self.titlebar)

        # Fisrt start grid
        self.first_start_grid = self.builder.get_object('first_start_grid')
        pix = Pixbuf.new_from_resource_at_scale('/info/febvre/MangaScan/images/logo.png', 256, 256, True)
        self.builder.get_object('app_logo').set_from_pixbuf(pix)

        # Init pages
        self.library = Library(self)
        self.card = Card(self)
        self.reader = Reader(self)

        # Window
        self.connect('check-resize', self.on_resize)
        self.connect('delete-event', self.on_application_quit)
        self.connect('window-state-event', self.on_window_state_event)

        # Custom CSS
        screen = Gdk.Screen.get_default()

        css_provider = Gtk.CssProvider()
        css_provider_resource = Gio.File.new_for_uri('resource:///info/febvre/MangaScan/css/style.css')
        css_provider.load_from_file(css_provider_resource)

        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        if Gio.Application.get_default().development_mode is True:
            self.get_style_context().add_class('devel')

        # Apply theme
        gtk_settings = Gtk.Settings.get_default()
        gtk_settings.set_property('gtk-application-prefer-dark-theme', mangascan.config_manager.get_dark_theme())

        self.library.show()

    def change_layout(self):
        pass

    def confirm(self, title, message, callback):
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.YES:
                callback()

            dialog.destroy()

        dialog = Handy.Dialog.new(self)
        dialog.get_style_context().add_class('solid-csd')
        dialog.connect('response', on_response)
        dialog.set_title(title)
        dialog.add_buttons('Yes', Gtk.ResponseType.YES, 'Cancel', Gtk.ResponseType.CANCEL)
        dialog.set_default_response(Gtk.ResponseType.YES)

        label = Gtk.Label()
        label.set_text(message)
        label.set_line_wrap(True)
        label.set_vexpand(True)
        label.set_property('margin', 16)
        label.set_valign(Gtk.Align.CENTER)
        label.set_halign(Gtk.Align.CENTER)
        label.set_justify(Gtk.Justification.CENTER)
        dialog.get_content_area().add(label)

        dialog.show_all()

    def hide_notification(self):
        self.builder.get_object('notification_revealer').set_reveal_child(False)

    def on_about_menu_clicked(self, action, param):
        builder = Gtk.Builder()
        builder.add_from_resource('/info/febvre/MangaScan/about_dialog.ui')

        about_dialog = builder.get_object('about_dialog')
        about_dialog.set_modal(True)
        about_dialog.set_transient_for(self)
        about_dialog.present()

    def on_application_quit(self, window, event):
        def before_quit():
            self.save_window_size()
            backup_db()

        if self.downloader.status == 'running' or self.updater.status == 'running':
            def confirm_callback():
                self.downloader.stop()
                self.updater.stop()

                while self.downloader.status == 'running' or self.updater.status == 'running':
                    time.sleep(0.1)
                    continue

                before_quit()
                self.application.quit()

            message = [
                _('Are you sure you want to quit?'),
            ]
            if self.downloader.status == 'running':
                message.append(_('Some chapters are currently being downloaded.'))
            if self.updater.status == 'running':
                message.append(_('Some mangas are currently being updated.'))

            self.confirm(
                _('Quit?'),
                '\n'.join(message),
                confirm_callback
            )

            return True
        else:
            before_quit()

            return False

    def on_left_button_clicked(self, action, param):
        if self.page == 'library':
            if self.library.selection_mode:
                self.library.leave_selection_mode()
            elif self.application.connected:
                AddDialog(self).open(action, param)
            else:
                self.show_notification(_('No Internet connection'))
        elif self.page == 'card':
            if self.card.selection_mode:
                self.card.leave_selection_mode()
            else:
                self.library.show(invalidate_sort=True)
        elif self.page == 'reader':
            self.set_unfullscreen()

            # In card page, update all previously chapters consulted (last page read may have changed)
            for chapter in self.reader.chapters_consulted:
                self.card.update_chapter_row(chapter)

            self.card.show()

    def on_resize(self, window):
        size = self.get_size()
        if self._prev_size and self._prev_size.width == size.width and self._prev_size.height == size.height:
            return

        self._prev_size = size

        self.library.on_resize()
        if self.page == 'reader':
            self.reader.on_resize()

        if size.width < 700:
            if self.mobile_width is True:
                return

            self.mobile_width = True
            self.change_layout()
        else:
            if self.mobile_width is True:
                self.mobile_width = False
                self.change_layout()

    def on_settings_menu_clicked(self, action, param):
        SettingsDialog(self).open(action, param)

    def on_shortcuts_menu_clicked(self, action, param):
        builder = Gtk.Builder()
        builder.add_from_resource('/info/febvre/MangaScan/ui/shortcuts_overview.ui')

        shortcuts_overview = builder.get_object('shortcuts_overview')
        shortcuts_overview.set_modal(True)
        shortcuts_overview.set_transient_for(self)
        shortcuts_overview.present()

    def on_window_state_event(self, widget, event):
        self._is_maximized = (event.new_window_state & Gdk.WindowState.MAXIMIZED) != 0
        self._is_fullscreen = (event.new_window_state & Gdk.WindowState.FULLSCREEN) != 0

    def save_window_size(self):
        if not self._is_maximized and not self._is_fullscreen:
            size = self.get_size()
            mangascan.config_manager.set_window_size([size.width, size.height])

    def set_fullscreen(self):
        if not self._is_fullscreen:
            self.reader.controls.on_fullscreen()
            self.fullscreen()

    def set_unfullscreen(self):
        if self._is_fullscreen:
            self.reader.controls.on_unfullscreen()
            self.unfullscreen()

    def show_notification(self, message):
        self.builder.get_object('notification_label').set_text(message)
        self.builder.get_object('notification_revealer').set_reveal_child(True)

        revealer_timer = Timer(5.0, GLib.idle_add, args=[self.hide_notification])
        revealer_timer.start()

    def show_page(self, name, transition=True):
        if not transition:
            # Save defined transition type
            transition_type = self.stack.get_transition_type()
            # Set transition type to NONE
            self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
            self.title_stack.set_transition_type(Gtk.StackTransitionType.NONE)

        self.stack.set_visible_child_name(name)
        self.title_stack.set_visible_child_name(name)

        if not transition:
            # Restore transition type
            self.stack.set_transition_type(transition_type)
            self.title_stack.set_transition_type(transition_type)

        self.page = name

    def toggle_fullscreen(self, *args):
        if self._is_fullscreen:
            self.set_unfullscreen()
        else:
            self.set_fullscreen()
