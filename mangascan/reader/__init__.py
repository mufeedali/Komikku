# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

import mangascan.config_manager
from mangascan.activity_indicator import ActivityIndicator
from mangascan.reader.controls import Controls
from mangascan.reader.pager import Pager


class Reader:
    manga = None
    chapters_consulted = []
    size = None

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/info/febvre/MangaScan/ui/menu_reader.xml')

        self.overlay = self.builder.get_object('reader_overlay')

        # Headerbar
        self.title_label = self.builder.get_object('reader_page_title_label')
        self.subtitle_label = self.builder.get_object('reader_page_subtitle_label')

        # Pager
        self.pager = Pager(self)
        self.overlay.add_overlay(self.pager)

        # Activity indicator
        self.activity_indicator = ActivityIndicator()
        self.overlay.add_overlay(self.activity_indicator)

        # Controls
        self.controls = Controls(self)

    @property
    def background_color(self):
        return self.manga.background_color or mangascan.config_manager.get_background_color()

    @property
    def reading_direction(self):
        return self.manga.reading_direction or mangascan.config_manager.get_reading_direction()

    @property
    def scaling(self):
        return self.manga.scaling or mangascan.config_manager.get_scaling()

    def add_actions(self):
        # Reading direction
        self.reading_direction_action = Gio.SimpleAction.new_stateful(
            'reader.reading-direction', GLib.VariantType.new('s'), GLib.Variant('s', 'right-to-left'))
        self.reading_direction_action.connect('change-state', self.on_reading_direction_changed)

        # Scaling
        self.scaling_action = Gio.SimpleAction.new_stateful(
            'reader.scaling', GLib.VariantType.new('s'), GLib.Variant('s', 'screen'))
        self.scaling_action.connect('change-state', self.on_scaling_changed)

        # Background color
        self.background_color_action = Gio.SimpleAction.new_stateful(
            'reader.background-color', GLib.VariantType.new('s'), GLib.Variant('s', 'white'))
        self.background_color_action.connect('change-state', self.on_background_color_changed)

        self.window.application.add_action(self.reading_direction_action)
        self.window.application.add_action(self.scaling_action)
        self.window.application.add_action(self.background_color_action)

    def init(self, chapter):
        self.manga = chapter.manga

        self.size = self.window.get_size()

        # Reset list of chapters consulted
        self.chapters_consulted = set()

        # Init settings
        self.set_reading_direction()
        self.set_scaling()
        self.set_background_color()

        self.pager.clear()

        self.show()

        self.pager.switch_chapter(chapter)

    def on_background_color_changed(self, action, variant):
        value = variant.get_string()
        if value == self.manga.background_color:
            return

        self.manga.update(dict(background_color=value))
        self.set_background_color()

    def on_reading_direction_changed(self, action, variant):
        value = variant.get_string()
        if value == self.manga.reading_direction:
            return

        self.manga.update(dict(reading_direction=value))
        self.set_reading_direction()

        self.pager.reverse_pages()

    def on_resize(self):
        self.size = self.window.get_size()
        self.pager.resize_pages()

    def on_scaling_changed(self, action, variant):
        value = variant.get_string()
        if value == self.manga.scaling:
            return

        self.manga.update(dict(scaling=value))
        self.set_scaling()

        self.pager.rescale_pages()

    def set_background_color(self):
        self.background_color_action.set_state(GLib.Variant('s', self.background_color))
        if self.background_color == 'white':
            self.pager.viewport.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        else:
            self.pager.viewport.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))

    def set_reading_direction(self):
        self.reading_direction_action.set_state(GLib.Variant('s', self.reading_direction))
        self.controls.set_scale_direction(self.reading_direction == 'right-to-left')

    def set_scaling(self):
        self.scaling_action.set_state(GLib.Variant('s', self.scaling))

    def show(self):
        self.builder.get_object('fullscreen_button').show()

        self.builder.get_object('menu_button').set_menu_model(self.builder.get_object('menu-reader'))
        self.builder.get_object('menu_button_image').set_from_icon_name('view-more-symbolic', Gtk.IconSize.MENU)

        self.controls.hide()

        if mangascan.config_manager.get_fullscreen():
            self.window.set_fullscreen()

        self.window.show_page('reader')

    def update_title(self, chapter):
        # Add chapter to list of chapters consulted
        # This list is used by the Card page to update chapters rows
        self.chapters_consulted.add(chapter)

        # Set title & subtitle (headerbar)
        self.title_label.set_text(chapter.manga.name)
        subtitle = chapter.title
        if chapter.manga.name in subtitle:
            subtitle = subtitle.replace(chapter.manga.name, '').strip()
        self.subtitle_label.set_text(subtitle)
