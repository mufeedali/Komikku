# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import datetime
import threading

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf

import mangascan.config_manager
from mangascan.model import create_db_connection
from mangascan.model import Chapter


class Controls():
    is_visible = False
    reader = None
    chapter = None

    FULLSCREEN_ICON_NAME = 'view-fullscreen-symbolic'
    UNFULLSCREEN_ICON_NAME = 'view-restore-symbolic'

    def __init__(self, reader):
        self.reader = reader

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.get_style_context().add_class('reader-controls-box')
        self.box.set_valign(Gtk.Align.END)

        # Chapter's title
        self.label = Gtk.Label()
        self.label.get_style_context().add_class('reader-controls-title-label')
        self.label.set_halign(Gtk.Align.START)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.box.pack_start(self.label, True, True, 4)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # Chapter's pages slider: current / nb
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 2, 1)
        self.scale.get_style_context().add_class('reader-controls-pages-scale')
        self.scale.set_value_pos(Gtk.PositionType.RIGHT)

        def format(scale, value):
            return '{0}/{1}'.format(int(value), len(self.chapter.pages))

        self.scale.connect('format-value', format)
        self.scale.connect('value-changed', self.on_scale_value_changed)
        hbox.pack_start(self.scale, True, True, 0)

        # Fullscreen toggle button
        self.fullscreen_button = Gtk.ToggleButton()
        self.fullscreen_button.set_image(Gtk.Image.new_from_icon_name(self.FULLSCREEN_ICON_NAME, Gtk.IconSize.BUTTON))
        self.fullscreen_button.set_active(False)
        self.fullscreen_button.connect('clicked', self.toggle_fullscreen)
        hbox.pack_start(self.fullscreen_button, False, True, 0)

        self.box.pack_start(hbox, True, True, 0)

        self.reader.overlay.add_overlay(self.box)

    def goto_page(self, index):
        if self.scale.get_value() == index:
            self.scale.emit('value-changed')
        else:
            self.scale.set_value(index)

    def hide(self):
        self.is_visible = False
        self.box.hide()

    def init(self, chapter):
        self.chapter = chapter

        self.scale.set_range(1, len(self.chapter.pages))
        self.label.set_text(self.chapter.title)

    def init_fullscreen(self):
        if mangascan.config_manager.get_fullscreen():
            self.fullscreen_button.set_active(True)

    def on_scale_value_changed(self, scale):
        self.reader.render_page(int(scale.get_value()) - 1)

    def set_scale_direction(self, inverted):
        self.scale.set_inverted(inverted)

    def show(self):
        self.is_visible = True
        self.box.show()

    def toggle_fullscreen(self, *args):
        is_fullscreen = self.reader.window.get_window().get_state() & Gdk.WindowState.FULLSCREEN == Gdk.WindowState.FULLSCREEN

        if is_fullscreen:
            self.fullscreen_button.set_image(Gtk.Image.new_from_icon_name(self.FULLSCREEN_ICON_NAME, Gtk.IconSize.BUTTON))
            self.reader.window.unfullscreen()
        else:
            self.fullscreen_button.set_image(Gtk.Image.new_from_icon_name(self.UNFULLSCREEN_ICON_NAME, Gtk.IconSize.BUTTON))
            self.reader.window.fullscreen()


class Reader():
    button_press_timeout_id = None
    chapter = None
    default_double_click_time = Gtk.Settings.get_default().get_property('gtk-double-click-time')
    pixbuf = None
    size = None
    zoom = dict(active=False)

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/com/gitlab/valos/MangaScan/menu_reader.xml')

        self.viewport = self.builder.get_object('reader_page_viewport')
        self.scrolledwindow = self.viewport.get_parent()
        self.overlay = self.scrolledwindow.get_parent()

        self.image = Gtk.Image()
        self.viewport.add(self.image)

        # Spinner
        self.spinner_box = self.builder.get_object('spinner_box')
        self.overlay.add_overlay(self.spinner_box)

        # Controls
        self.controls = Controls(self)

        self.scrolledwindow.connect('button-press-event', self.on_button_press)

    @property
    def reading_direction(self):
        return self.chapter.manga.reading_direction or mangascan.config_manager.get_reading_direction()

    @property
    def scaling(self):
        return self.chapter.manga.scaling or mangascan.config_manager.get_scaling()

    def add_accelerators(self):
        self.window.application.set_accels_for_action('app.reader.fullscreen', ['F11'])

    def add_actions(self):
        # Reading direction
        self.reading_direction_action = Gio.SimpleAction.new_stateful(
            'reader.reading-direction', GLib.VariantType.new('s'), GLib.Variant('s', 'right-to-left'))
        self.reading_direction_action.connect('change-state', self.on_reading_direction_changed)

        # Scaling
        self.scaling_action = Gio.SimpleAction.new_stateful(
            'reader.scaling', GLib.VariantType.new('s'), GLib.Variant('s', 'screen'))
        self.scaling_action.connect('change-state', self.on_scaling_changed)

        # Fullscreen
        self.fullscreen_action = Gio.SimpleAction.new('reader.fullscreen', None)
        self.fullscreen_action.connect('activate', self.controls.toggle_fullscreen)

        self.window.application.add_action(self.reading_direction_action)
        self.window.application.add_action(self.scaling_action)
        self.window.application.add_action(self.fullscreen_action)

    def hide_spinner(self):
        self.spinner_box.hide()
        self.spinner_box.get_children()[0].stop()

    def init(self, chapter, index=None):
        def run():
            self.chapter.update()

            GLib.idle_add(complete, index)

        def complete(index):
            self.chapter.manga.update(dict(last_read=datetime.datetime.now()))

            if index is None:
                index = self.chapter.last_page_read_index or 0
            elif index == 'first':
                index = 0
            elif index == 'last':
                index = len(self.chapter.pages) - 1

            self.hide_spinner()
            self.controls.init(self.chapter)
            self.controls.goto_page(index + 1)

        if index is None:
            # We come from library
            self.show()

        self.chapter = chapter

        self.show_spinner()

        # Init settings
        self.set_reading_direction()
        self.set_scaling()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_button_press(self, widget, event):
        if event.button == 1:
            if self.button_press_timeout_id is None and event.type == Gdk.EventType.BUTTON_PRESS:
                # Schedule single click event to be able to detect double click
                self.button_press_timeout_id = GLib.timeout_add(self.default_double_click_time + 100, self.on_single_click, event.copy())

            elif event.type == Gdk.EventType._2BUTTON_PRESS:
                # Remove scheduled single click event
                if self.button_press_timeout_id:
                    GLib.source_remove(self.button_press_timeout_id)
                    self.button_press_timeout_id = None

                GLib.idle_add(self.on_double_click, event.copy())

    def on_double_click(self, event):
        # Zoom/unzoom

        def adjust_scroll(hadj, h_value, v_value):
            hadj.disconnect(adjust_scroll_handler_id)

            def adjust():
                vadj = self.scrolledwindow.get_vadjustment()
                hadj.set_value(h_value)
                vadj.set_value(v_value)

            GLib.idle_add(adjust)

        hadj = self.scrolledwindow.get_hadjustment()
        vadj = self.scrolledwindow.get_vadjustment()

        if self.zoom['active'] is False:
            # Record hadjustment and vadjustment values
            self.zoom['orig_hadj_value'] = hadj.get_value()
            self.zoom['orig_vadj_value'] = vadj.get_value()

            # Adjust image to 100% of original size (arbitrary experimental choice)
            factor = 1
            orig_width = self.image.get_pixbuf().get_width()
            orig_height = self.image.get_pixbuf().get_height()
            zoom_width = self.pixbuf.get_width() * factor
            zoom_height = self.pixbuf.get_height() * factor
            ratio = zoom_width / orig_width

            if orig_width <= self.size.width:
                rel_event_x = event.x - (self.size.width - orig_width) / 2
            else:
                rel_event_x = event.x + hadj.get_value()
            if orig_height <= self.size.height:
                rel_event_y = event.y - (self.size.height - orig_height) / 2
            else:
                rel_event_y = event.y + vadj.get_value()

            h_value = rel_event_x * ratio - event.x
            v_value = rel_event_y * ratio - event.y

            adjust_scroll_handler_id = hadj.connect('changed', adjust_scroll, h_value, v_value)

            pixbuf = self.pixbuf.scale_simple(zoom_width, zoom_height, InterpType.BILINEAR)

            self.image.set_from_pixbuf(pixbuf)

            self.zoom['active'] = True
        else:
            adjust_scroll_handler_id = hadj.connect('changed', adjust_scroll, self.zoom['orig_hadj_value'], self.zoom['orig_vadj_value'])

            self.set_page_image_from_pixbuf()

            self.zoom['active'] = False

    def on_reading_direction_changed(self, action, variant):
        value = variant.get_string()
        if value == self.chapter.manga.reading_direction:
            return

        self.chapter.manga.update(dict(reading_direction=value))
        self.set_reading_direction()

    def on_resize(self):
        if self.pixbuf is None:
            return

        self.size = self.viewport.get_allocation()
        self.set_page_image_from_pixbuf()

    def on_scaling_changed(self, action, variant):
        value = variant.get_string()
        if value == self.chapter.manga.scaling:
            return

        self.chapter.manga.update(dict(scaling=value))
        self.set_scaling()

    def on_single_click(self, event):
        self.button_press_timeout_id = None

        if event.x < self.size.width / 3:
            # 1st third of the page
            if self.zoom['active']:
                return

            index = self.page_index + 1 if self.reading_direction == 'right-to-left' else self.page_index - 1
        elif event.x > 2 * self.size.width / 3:
            # Last third of the page
            if self.zoom['active']:
                return

            index = self.page_index - 1 if self.reading_direction == 'right-to-left' else self.page_index + 1
        else:
            # Center part of the page
            if self.controls.is_visible:
                self.controls.hide()
            else:
                self.controls.show()

            return

        if index >= 0 and index < len(self.chapter.pages):
            self.controls.goto_page(index + 1)
        elif index == -1:
            # Get previous chapter
            db_conn = create_db_connection()
            row = db_conn.execute(
                'SELECT * FROM chapters WHERE manga_id = ? AND rank = ?', (self.chapter.manga_id, self.chapter.rank - 1)).fetchone()
            db_conn.close()

            if row:
                self.init(Chapter(row=row), 'last')
        elif index == len(self.chapter.pages):
            # Get next chapter
            db_conn = create_db_connection()
            row = db_conn.execute(
                'SELECT * FROM chapters WHERE manga_id = ? AND rank = ?', (self.chapter.manga_id, self.chapter.rank + 1)).fetchone()
            db_conn.close()

            if row:
                self.init(Chapter(row=row), 'first')

        return False

    def render_page(self, index):
        def run():
            page_path = self.chapter.get_page_path(index)
            if page_path is None:
                if self.window.application.connected:
                    page_path = self.chapter.get_page(self.page_index)
                else:
                    self.window.show_notification(_('No Internet connection'))

            GLib.idle_add(complete, page_path)

        def complete(page_path):
            if page_path:
                self.pixbuf = Pixbuf.new_from_file(page_path)
            else:
                self.pixbuf = Pixbuf.new_from_resource('/com/gitlab/valos/MangaScan/images/missing_file.png')

            self.chapter.update(dict(
                last_page_read_index=index,
                read=index == len(self.chapter.pages) - 1,
            ))

            self.size = self.viewport.get_allocation()
            self.set_page_image_from_pixbuf()

            self.image.show()

            self.hide_spinner()

            return False

        self.zoom['active'] = False
        self.page_index = index

        self.show_spinner()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def set_page_image_from_pixbuf(self):
        width = self.pixbuf.get_width()
        height = self.pixbuf.get_height()

        if self.scaling == 'width' or (self.scaling == 'screen' and self.size.width <= self.size.height):
            # Adapt image to width
            pixbuf = self.pixbuf.scale_simple(
                self.size.width,
                height / (width / self.size.width),
                InterpType.BILINEAR
            )
        elif self.scaling == 'height' or (self.scaling == 'screen' and self.size.width > self.size.height):
            # Adjust image to height
            pixbuf = self.pixbuf.scale_simple(
                width / (height / self.size.height),
                self.size.height,
                InterpType.BILINEAR
            )

        self.image.set_from_pixbuf(pixbuf)

    def set_reading_direction(self):
        self.reading_direction_action.set_state(GLib.Variant('s', self.reading_direction))
        self.controls.set_scale_direction(self.reading_direction == 'right-to-left')

    def set_scaling(self):
        self.scaling_action.set_state(GLib.Variant('s', self.scaling))

    def show_spinner(self):
        self.spinner_box.get_children()[0].start()
        self.spinner_box.show()

    def show(self):
        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu-reader'))
        self.builder.get_object('menubutton_image').set_from_icon_name('view-more-symbolic', Gtk.IconSize.MENU)

        self.image.clear()
        self.pixbuf = None
        self.controls.hide()
        self.controls.init_fullscreen()

        self.window.show_page('reader')
