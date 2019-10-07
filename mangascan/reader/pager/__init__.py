# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType

from mangascan.reader.pager.sequence import Sequence


class Pager(Gtk.ScrolledWindow):
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

        self.sequences = dict()
        self.current_chapter_id = None
        self.current_page_index = None

        self.viewport = Gtk.Viewport()
        self.add(self.viewport)

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.viewport.add(self.box)

        self.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.btn_press_handler_id = self.connect('button-press-event', self.on_btn_press)
        self.key_press_handler_id = self.connect('key-press-event', self.on_key_press)

        self.show_all()

    @property
    def current_chapter(self):
        return self.sequences[self.current_chapter_id].chapter

    @property
    def current_page(self):
        return self.sequences[self.current_chapter_id].pages[self.current_page_index]

    def adjust_scroll(self, animate=True, duration=350):
        """ Scroll to current page """

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
        end = self.compute_page_position() * self.reader.size.width

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

    def block_nav(self):
        """ Blocks keyboard and mouse/touch page navigation """

        self.handler_block(self.key_press_handler_id)
        self.handler_block(self.btn_press_handler_id)

    def clean(self):
        """ Clean all pages that are not neightbors of current page """

        pages = []
        current_page_position = None

        for sequence in self.box.get_children():
            for page in sequence.get_children():
                if page.pixbuf is not None or (sequence.chapter.id == self.current_chapter_id and page.index == self.current_page_index):
                    pages.append(page)
                    if sequence.chapter.id == self.current_chapter_id and page.index == self.current_page_index:
                        current_page_position = len(pages) - 1

        if current_page_position is None:
            return

        for page in pages[:(current_page_position - 1)] + pages[(current_page_position + 2):]:
            page.clean()

    def clear(self):
        self.sequences = dict()
        self.current_chapter_id = None
        self.current_page_index = None

        for sequence in self.box.get_children():
            self.box.remove(sequence)

    def compute_page_position(self):
        """ Computes current page's position in scrolledwindow """

        position = 0
        for sequence in self.box.get_children():
            if sequence.chapter.id == self.current_chapter_id:
                if self.current_page_index is not None:
                    if self.reader.reading_direction == 'right-to-left':
                        position += len(sequence.pages) - 1 - self.current_page_index
                    else:
                        position += self.current_page_index
                break
            else:
                position += len(sequence.pages)

        return position

    def load_chapter(self, chapter, page_index):
        sequence = Sequence(self.reader, chapter)
        self.current_page_index = 0
        self.current_chapter_id = chapter.id
        self.sequences[chapter.id] = sequence

        self.box.pack_start(sequence, True, True, 0)
        if page_index:
            if self.reader.reading_direction == 'right-to-left':
                if page_index == 'first':
                    self.box.reorder_child(sequence, 0)
                    self.get_hadjustment().set_value(self.reader.size.width)
            else:
                if page_index == 'last':
                    self.box.reorder_child(sequence, 0)
                    self.get_hadjustment().set_value(self.reader.size.width)

        self.adjust_scroll()

        def load_sequence():
            if self.scroll_lock:
                return True

            sequence.load(page_index, self.on_load_chapter_completed, self.unblock_nav)

            return False

        GLib.idle_add(load_sequence)

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

    def on_load_chapter_completed(self, page_index):
        self.unblock_nav()

        if page_index is None:
            page_index = self.current_chapter.last_page_read_index or 0
        elif page_index == 'first':
            page_index = 0
        elif page_index == 'last':
            page_index = len(self.current_chapter.pages) - 1

        self.reader.controls.init()

        self.switch_page(page_index, animate=False)

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

            # Adjust image to 100% of original size (arbitrary experimental choice)
            factor = 1
            orig_width = image.get_pixbuf().get_width()
            orig_height = image.get_pixbuf().get_height()
            zoom_width = pixbuf.get_width() * factor
            zoom_height = pixbuf.get_height() * factor
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

    def on_key_press(self, widget, event):
        if self.current_page_index is None:
            # Init is certainly not over yet.
            return

        if self.reader.controls.is_visible:
            # No need to handle keyboard navigation when controls are visible
            # Slider (Gtk.Scale) already provides it
            return

        if event.state != 0 or event.keyval not in (Gdk.KEY_Left, Gdk.KEY_Right):
            return

        if event.keyval == Gdk.KEY_Left:
            index = self.current_page_index + 1 if self.reader.reading_direction == 'right-to-left' else self.current_page_index - 1
        else:
            index = self.current_page_index - 1 if self.reader.reading_direction == 'right-to-left' else self.current_page_index + 1

        self.switch_page(index)

    def on_single_click(self, event):
        self.button_press_timeout_id = None

        if event.x < self.reader.size.width / 3:
            # 1st third of the page
            if self.zoom['active']:
                return False

            index = self.current_page_index + 1 if self.reader.reading_direction == 'right-to-left' else self.current_page_index - 1
        elif event.x > 2 * self.reader.size.width / 3:
            # Last third of the page
            if self.zoom['active']:
                return False

            index = self.current_page_index - 1 if self.reader.reading_direction == 'right-to-left' else self.current_page_index + 1
        else:
            # Center part of the page: toggle controls
            if self.reader.controls.is_visible:
                self.current_page.page_number_label.show()
                self.reader.controls.hide()
            else:
                self.current_page.page_number_label.hide()
                self.reader.controls.show()

            return False

        self.switch_page(index)

        return False

    def rescale_pages(self):
        for chapter_id, sequence in self.sequences.items():
            sequence.rescale_pages()

    def resize_pages(self):
        for chapter_id, sequence in self.sequences.items():
            sequence.resize_pages()

        self.adjust_scroll(animate=False)

    def reverse_pages(self):
        sequences = self.box.get_children()
        length = len(sequences)

        right_index = length
        for left_index in range(length // 2):
            right_index = right_index - 1

            self.box.reorder_child(sequences[left_index], right_index)
            self.box.reorder_child(sequences[right_index], left_index)

            sequences[left_index].reverse_pages()
            sequences[right_index].reverse_pages()

        if length // 2 != length / 2:
            sequences[length // 2].reverse_pages()

        self.adjust_scroll(animate=False)

    def switch_chapter(self, chapter, page_index=None):
        # Update headerbar with chapter title
        self.reader.update_title(chapter)

        if chapter.id not in self.sequences:
            # Chapter has not been loaded yet
            self.block_nav()

            self.load_chapter(chapter, page_index)
        else:
            self.current_chapter_id = chapter.id
            self.reader.controls.init()

            if page_index is None:
                page_index = chapter.last_page_read_index or 0
            elif page_index == 'first':
                page_index = 0
            elif page_index == 'last':
                page_index = len(chapter.pages) - 1

            self.switch_page(page_index)

    def switch_page(self, index, animate=True):
        if index >= 0 and index < len(self.sequences[self.current_chapter_id].pages):
            self.current_page_index = index

            self.adjust_scroll(animate)

            self.reader.controls.set_scale_value(index + 1, block_event=True)

            def load_page():
                if self.scroll_lock:
                    return True

                self.sequences[self.current_chapter_id].pages[index].load()

                return False

            GLib.idle_add(load_page)
            self.clean()
        else:
            # Chapter change: next or prev
            if index < 0:
                index = 'last'
                direction = -1
            else:
                index = 'first'
                direction = 1

            next_chapter = self.reader.manga.get_next_chapter(self.current_chapter, direction)

            if next_chapter is not None:
                self.switch_chapter(next_chapter, index)
            else:
                if index == 'first':
                    message = _('It was the last chapter')
                else:
                    message = _('There is no previous chapter.')
                self.window.show_notification(message, interval=2)

    def unblock_nav(self):
        """ Unblocks keyboard and mouse/touch page navigation """

        self.handler_unblock(self.key_press_handler_id)
        self.handler_unblock(self.btn_press_handler_id)
