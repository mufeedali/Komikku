# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gi.repository import Gtk


class Controls:
    is_visible = False
    reader = None

    def __init__(self, reader):
        self.reader = reader

        #
        # Top box (visible in fullscreen mode only)
        #
        self.top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.top_box.set_valign(Gtk.Align.START)

        # Headerbar
        self.headerbar = Gtk.HeaderBar()

        # Back button
        self.back_button = Gtk.Button.new_from_icon_name('go-previous-symbolic', Gtk.IconSize.BUTTON)
        self.back_button.connect('clicked', self.reader.window.on_left_button_clicked, None)
        self.headerbar.pack_start(self.back_button)

        # Menu button
        self.menu_button = Gtk.MenuButton.new()
        self.menu_button.get_children()[0].set_from_icon_name('view-more-symbolic', Gtk.IconSize.MENU)
        self.menu_button.set_menu_model(self.reader.builder.get_object('menu-reader'))
        self.headerbar.pack_end(self.menu_button)

        # Unfullscreen button
        self.unfullscreen_button = Gtk.Button.new_from_icon_name('view-restore-symbolic', Gtk.IconSize.BUTTON)
        self.unfullscreen_button.connect('clicked', self.reader.window.toggle_fullscreen)
        self.headerbar.pack_end(self.unfullscreen_button)

        self.top_box.pack_start(self.headerbar, True, True, 0)
        self.reader.overlay.add_overlay(self.top_box)

        #
        # Bottom box
        #
        self.bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.bottom_box.get_style_context().add_class('reader-controls-bottom-box')
        self.bottom_box.set_valign(Gtk.Align.END)

        # Number of pages
        self.pages_count_label = Gtk.Label()
        self.pages_count_label.set_halign(Gtk.Align.START)
        self.bottom_box.pack_start(self.pages_count_label, False, True, 4)

        # Chapter's pages slider: current / nb
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 2, 1)
        self.scale_handler_id = self.scale.connect('value-changed', self.on_scale_value_changed)

        self.bottom_box.pack_start(self.scale, True, True, 0)
        self.reader.overlay.add_overlay(self.bottom_box)

    def hide(self):
        self.is_visible = False
        self.top_box.hide()
        self.bottom_box.hide()

    def init(self):
        chapter = self.reader.pager.current_page.chapter

        # Set title & subtitle
        self.headerbar.set_title(chapter.manga.name)
        subtitle = chapter.title
        if chapter.manga.name in subtitle:
            subtitle = subtitle.replace(chapter.manga.name, '').strip()
        self.headerbar.set_subtitle(subtitle)

        # Set slider range
        with self.scale.handler_block(self.scale_handler_id):
            self.scale.set_range(1, len(chapter.pages))

        self.pages_count_label.set_text(str(len(chapter.pages)))

    def on_fullscreen(self):
        if self.is_visible:
            self.top_box.show_all()

    def on_scale_value_changed(self, scale):
        self.reader.pager.goto_page(int(scale.get_value()) - 1)

    def on_unfullscreen(self):
        if self.is_visible:
            self.top_box.hide()

    def set_scale_value(self, index):
        with self.scale.handler_block(self.scale_handler_id):
            if self.scale.get_value() == index:
                self.scale.emit('value-changed')
            else:
                self.scale.set_value(index)

    def set_scale_direction(self, inverted):
        self.scale.set_inverted(inverted)
        self.scale.set_value_pos(Gtk.PositionType.RIGHT if inverted else Gtk.PositionType.LEFT)
        self.bottom_box.set_child_packing(self.pages_count_label, False, True, 4, Gtk.PackType.START if inverted else Gtk.PackType.END)

    def show(self):
        self.is_visible = True

        if self.reader.window.is_fullscreen:
            self.top_box.show_all()

        self.bottom_box.show_all()
