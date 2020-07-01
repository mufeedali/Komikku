# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gi.repository import Gdk
from gi.repository import Gtk


class Controls:
    active = False
    is_visible = False
    reader = None

    def __init__(self, reader):
        self.reader = reader
        self.window = reader.window

        self.bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.bottom_box.get_style_context().add_class('reader-controls-bottom-box')
        self.bottom_box.set_valign(Gtk.Align.END)

        # Number of pages
        self.pages_count_label = Gtk.Label()
        self.pages_count_label.set_halign(Gtk.Align.START)
        self.bottom_box.pack_start(self.pages_count_label, False, True, 4)

        # Chapter's pages slider: current / nb
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 2, 1)
        self.scale.set_increments(1, 0)  # Disable scrolling with mouse wheel
        self.scale_handler_id = self.scale.connect('change-value', self.on_scale_value_changed)

        self.bottom_box.pack_start(self.scale, True, True, 0)
        self.reader.overlay.add_overlay(self.bottom_box)

    def hide(self):
        self.is_visible = False
        if self.window.is_fullscreen:
            self.window.headerbar_revealer.set_reveal_child(False)
        self.bottom_box.hide()

    def init(self, chapter):
        self.active = chapter.pages is not None
        if not self.active:
            return

        # Set slider range
        with self.scale.handler_block(self.scale_handler_id):
            self.scale.set_range(1, len(chapter.pages))

        self.pages_count_label.set_text(str(len(chapter.pages)))

    def on_fullscreen(self):
        self.window.headerbar_revealer.set_reveal_child(self.is_visible)

    def on_scale_value_changed(self, scale, scroll_type, value):
        value = round(value)
        if scroll_type != Gtk.ScrollType.JUMP or self.scale.get_value() == value:
            return Gdk.EVENT_STOP

        self.reader.pager.goto_page(value - 1)

    def on_unfullscreen(self):
        self.window.headerbar_revealer.set_reveal_child(True)

    def set_scale_value(self, index):
        if not self.active:
            return

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
        if not self.active:
            return

        self.is_visible = True

        if self.window.is_fullscreen:
            self.window.headerbar_revealer.set_reveal_child(True)

        self.bottom_box.show_all()
