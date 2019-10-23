# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import datetime
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType

from komikku.reader.pager.page import Page


class Pager(Gtk.ScrolledWindow):
    pages = []
    current_page = None

    button_press_timeout_id = None
    default_double_click_time = Gtk.Settings.get_default().get_property('gtk-double-click-time')
    scroll_lock = False
    zoom = dict(active=False)

    def __init__(self, reader):
        Gtk.ScrolledWindow.__init__(self)
        self.get_hscrollbar().hide()
        self.get_vscrollbar().hide()

        self.reader = reader
        self.window = reader.window

        self.viewport = Gtk.Viewport()
        self.add(self.viewport)

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.viewport.add(self.box)

        self.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.btn_press_handler_id = self.connect('button-press-event', self.on_btn_press)
        self.key_press_handler_id = self.connect('key-press-event', self.on_key_press)

        self.show_all()

    @property
    def pages(self):
        return self.box.get_children()

    def adjust_scroll(self, position=1, animate=True, duration=350):
        """ Scroll to a page """

        def ease_out_cubic(t):
            t = t - 1
            return t * t * t + 1

        def move(scrolledwindow, clock):
            now = clock.get_frame_time()
            if now < end_time and adj.get_value() != end:
                t = (now - start_time) / (end_time - start_time)
                t = ease_out_cubic(t)

                adj.set_value(start + t * (end - start))

                return True
            else:
                adj.set_value(end)
                self.scroll_lock = False

                return False

        adj = self.get_hadjustment()
        start = adj.get_value()
        end = position * self.reader.size.width

        if start - end == 0:
            return

        if animate:
            clock = self.get_frame_clock()
            if clock:
                start_time = clock.get_frame_time()
                end_time = start_time + 1000 * duration

                self.scroll_lock = True
                self.add_tick_callback(move)
        else:
            adj.set_value(end)

    def clear(self):
        self.current_page = None

        for page in self.pages:
            page.clean()
            page.destroy()

    def goto_page(self, page_index):
        if self.pages[0].index == page_index and self.pages[0].chapter == self.current_page.chapter:
            self.switchto_page('left')
        elif self.pages[2].index == page_index and self.pages[2].chapter == self.current_page.chapter:
            self.switchto_page('right')
        else:
            self.init(self.current_page.chapter, page_index)

    def init(self, chapter, page_index=None):
        self.reader.update_title(chapter)

        if page_index is None:
            page_index = chapter.last_page_read_index or 0

        direction = 1 if self.reader.reading_direction == 'right-to-left' else -1

        self.clear()

        # Left page
        left_page = Page(self, chapter, page_index + direction)
        self.box.pack_start(left_page, True, True, 0)

        # Center page
        center_page = Page(self, chapter, page_index)
        self.box.pack_start(center_page, True, True, 0)

        # Right page
        right_page = Page(self, chapter, page_index - direction)
        self.box.pack_start(right_page, True, True, 0)

        # Force immediate rendering
        self.queue_draw()
        while Gtk.events_pending():
            Gtk.main_iteration()

        self.adjust_scroll(animate=False)

        self.current_page = center_page
        center_page.connect('load-completed', self.on_first_page_loaded)
        center_page.load()

    def on_btn_press(self, widget, event):
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

        def adjust_scroll(hadj, vadj, h_value, v_value):
            hadj.disconnect(adjust_scroll_handler_id)

            def adjust():
                hadj.set_value(h_value)
                vadj.set_value(v_value)

            GLib.idle_add(adjust)

        page = self.current_page
        hadj = page.scrolledwindow.get_hadjustment()
        vadj = page.scrolledwindow.get_vadjustment()

        if self.zoom['active'] is False:
            image = page.image
            pixbuf = page.pixbuf

            # Record hadjustment and vadjustment values
            self.zoom['orig_hadj_value'] = hadj.get_value()
            self.zoom['orig_vadj_value'] = vadj.get_value()

            # Adjust image's width to 2x window's width
            factor = 2
            orig_width = image.get_pixbuf().get_width()
            orig_height = image.get_pixbuf().get_height()
            zoom_width = self.reader.size.width * factor
            zoom_height = orig_height * (zoom_width / orig_width)
            ratio = zoom_width / orig_width

            if orig_width <= self.reader.size.width:
                rel_event_x = event.x - (self.reader.size.width - orig_width) / 2
            else:
                rel_event_x = event.x + hadj.get_value()
            if orig_height <= self.reader.size.height:
                rel_event_y = event.y - (self.reader.size.height - orig_height) / 2
            else:
                rel_event_y = event.y + vadj.get_value()

            h_value = rel_event_x * ratio - event.x
            v_value = rel_event_y * ratio - event.y

            adjust_scroll_handler_id = hadj.connect('changed', adjust_scroll, vadj, h_value, v_value)

            scaled_pixbuf = pixbuf.scale_simple(zoom_width, zoom_height, InterpType.BILINEAR)

            image.set_from_pixbuf(scaled_pixbuf)

            self.zoom['active'] = True
        else:
            adjust_scroll_handler_id = hadj.connect(
                'changed', adjust_scroll, vadj, self.zoom['orig_hadj_value'], self.zoom['orig_vadj_value'])

            page.set_image()

            self.zoom['active'] = False

    def on_first_page_loaded(self, page):
        self.on_page_loaded(page, True)

        self.pages[0].load()
        self.pages[2].load()

    def on_key_press(self, widget, event):
        if self.reader.controls.is_visible:
            # No need to handle keyboard navigation when controls are visible
            # Slider (Gtk.Scale) already provides it
            return

        if event.state != 0 or event.keyval not in (Gdk.KEY_Left, Gdk.KEY_Right):
            return

        self.switchto_page('left' if event.keyval == Gdk.KEY_Left else 'right')

    def on_page_loaded(self, page, chapter_changed):
        if page.status == 'loaded':
            page.chapter.manga.update(dict(last_read=datetime.datetime.now()))

            page.chapter.update(dict(
                last_page_read_index=page.index,
                read=page.index == len(page.chapter.pages) - 1,
                recent=0,
            ))

        if page.chapter.pages is not None:
            if chapter_changed:
                self.reader.controls.init()

            self.reader.controls.set_scale_value(page.index + 1, block_event=True)

        return False

    def on_single_click(self, event):
        self.button_press_timeout_id = None

        if event.x < self.reader.size.width / 3:
            # 1st third of the page
            if self.zoom['active']:
                return False

            self.switchto_page('left')
        elif event.x > 2 * self.reader.size.width / 3:
            # Last third of the page
            if self.zoom['active']:
                return False

            self.switchto_page('right')
        else:
            # Center part of the page: toggle controls
            if self.reader.controls.is_visible:
                self.current_page.page_number_label.show()
                self.reader.controls.hide()
            else:
                self.current_page.page_number_label.hide()
                self.reader.controls.show()

        return False

    def rescale_pages(self):
        for page in self.pages:
            page.rescale()

    def resize_pages(self):
        for page in self.pages:
            page.resize()

        self.adjust_scroll(animate=False)

    def reverse_pages(self):
        pages = self.box.get_children()

        self.box.reorder_child(pages[0], 2)
        self.box.reorder_child(pages[2], 0)

        self.adjust_scroll(animate=False)

    def switchto_page(self, position):
        if self.scroll_lock:
            return

        if position == 'left':
            page = self.pages[0]
        elif position == 'right':
            page = self.pages[2]

        if page.chapter is None:
            # We reached first or last chapter
            if page.index < 0:
                message = _('There is no previous chapter.')
            else:
                message = _('It was the last chapter.')
            self.window.show_notification(message, interval=2)
            return

        if page.chapter.pages is None:
            # Page belongs to a chapter whose pages are still unknown
            return

        chapter_changed = self.current_page.chapter != page.chapter
        if chapter_changed:
            self.reader.update_title(page.chapter)

        self.current_page = page

        if position == 'left':
            self.adjust_scroll(0)

            def add_page(current_page):
                if self.scroll_lock:
                    return True

                # Clean and destroy 3rd page
                self.pages[2].clean()
                self.pages[2].destroy()  # will remove it from box

                direction = 1 if self.reader.reading_direction == 'right-to-left' else -1

                new_page = Page(self, current_page.chapter, current_page.index + direction)
                new_page.load()
                self.box.pack_start(new_page, True, True, 0)
                self.box.reorder_child(new_page, 0)

                self.adjust_scroll(animate=False)

                return False

            GLib.idle_add(add_page, self.current_page)

        elif position == 'right':
            self.adjust_scroll(2)

            def add_page(current_page):
                if self.scroll_lock:
                    return True

                # Clean and destroy 1st page
                self.pages[0].clean()
                self.pages[0].destroy()  # will remove it from box

                self.adjust_scroll(animate=False)

                direction = -1 if self.reader.reading_direction == 'right-to-left' else 1

                new_page = Page(self, current_page.chapter, current_page.index + direction)
                new_page.load()
                self.box.pack_start(new_page, True, True, 0)

                return False

            GLib.idle_add(add_page, self.current_page)

        GLib.idle_add(self.on_page_loaded, self.current_page, chapter_changed)
