# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from komikku.reader.pager import BasePager
from komikku.reader.pager.page import Page


class WebtoonPager(Gtk.Box, BasePager):
    """Vertical smooth/continuous scrolling (a.k.a. infinite canvas) pager"""

    current_chapter_id = None
    current_page = None
    current_page_scroll_value = 0
    nb_preloaded_pages = 3  # Number of preloaded pages before and after the center/visible page
    scroll_direction = None

    render_pages_counter = 10
    render_pages_timeout_id = 0

    add_page_lock = False
    scroll_lock = False
    dont_ignore_scroll_adjustment = False

    def __init__(self, reader):
        Gtk.Box.__init__(self, visible=True)
        BasePager.__init__(self, reader)

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.vadj = self.scrolledwindow.get_vadjustment()

        self.scroll_handler_id = self.scrolledwindow.connect('scroll-event', self.on_scroll)
        self.scroll_changed_handler_id = self.vadj.connect('notify::upper', self.on_scroll_changed)
        self.scroll_value_changed_handler_id = self.vadj.connect('value-changed', self.on_scroll_value_changed)

        self.zoom['active'] = False

    @property
    def pages_offsets(self):
        pages = self.pages

        offsets = [0]
        for index, page in enumerate(pages[:-1]):
            prev = offsets[index]
            _minimal, natural = page.get_preferred_size()
            offsets.append(prev + natural.height)

        return offsets

    def add_page(self, position):
        pages = self.pages

        if position == Gtk.PositionType.TOP:
            with self.vadj.handler_block(self.scroll_changed_handler_id):
                pages[-1].clean()
                pages[-1].destroy()

            page = pages[0]
            new_page = Page(self, page.chapter, page.index - 1)
            self.add(new_page)
            self.reorder_child(new_page, 0)
        else:
            with self.vadj.handler_block(self.scroll_changed_handler_id):
                pages[0].clean()
                pages[0].destroy()

            page = pages[-1]
            new_page = Page(self, page.chapter, page.index + 1)
            self.add(new_page)

        new_page.status_changed_handler_id = new_page.connect('notify::status', self.on_page_status_changed)
        new_page.connect('rendered', self.on_page_rendered)

    def adjust_scroll(self, value=None, emit_signal=True):
        if value is None:
            value = self.get_page_offset(self.current_page) + self.current_page_scroll_value

        if emit_signal:
            self.vadj.set_value(value)
            if self.vadj.get_value() == value:
                self.vadj.emit('value-changed')
        else:
            with self.vadj.handler_block(self.scroll_value_changed_handler_id):
                self.vadj.set_value(value)

    def clear(self):
        self.scrolledwindow.disconnect(self.scroll_handler_id)

        self.vadj.set_value(0)
        self.vadj.disconnect(self.scroll_changed_handler_id)
        self.vadj.disconnect(self.scroll_value_changed_handler_id)

        GLib.source_remove(self.render_pages_timeout_id)

        BasePager.clear(self)

    def get_page_offset(self, page):
        pages = self.pages

        offset = 0
        for p in pages:
            if page == p:
                break
            _minimal, natural = p.get_preferred_size()
            offset += natural.height

        return offset

    def get_position(self, scroll_value):
        pages_offsets = self.pages_offsets
        position = None

        for i, page_offset in enumerate(reversed(pages_offsets)):
            if scroll_value >= page_offset:
                position = len(pages_offsets) - 1 - i
                break

        return position

    def goto_page(self, index):
        self.init(self.current_page.chapter, index)

    def init(self, chapter, page_index=None):
        if page_index is None:
            if chapter.read:
                page_index = 0
            elif chapter.last_page_read_index is not None:
                page_index = chapter.last_page_read_index
            else:
                page_index = 0

        for i in range(-self.nb_preloaded_pages, self.nb_preloaded_pages + 1):
            page = Page(self, chapter, page_index + i)
            page.status_changed_handler_id = page.connect('notify::status', self.on_page_status_changed)
            page.connect('rendered', self.on_page_rendered)
            self.add(page)
            if i == 0:
                self.current_page = page
                page.render()

        self.render_pages_timeout_id = GLib.timeout_add(500, self.render_pages)
        GLib.idle_add(self.update, self.current_page)

        self.set_interactive(True)

    def on_key_press(self, _widget, event):
        if self.window.page != 'reader' or self.scroll_lock:
            return Gdk.EVENT_PROPAGATE

        modifiers = Gtk.accelerator_get_default_mod_mask()
        if (event.state & modifiers) != 0:
            return Gdk.EVENT_PROPAGATE

        if event.keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
            self.hide_cursor()
            self.scroll_direction = Gtk.DirectionType.DOWN
            self.dont_ignore_scroll_adjustment = True
            self.vadj.set_value(self.vadj.get_value() + self.vadj.get_step_increment())
            return Gdk.EVENT_STOP

        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
            self.hide_cursor()
            self.scroll_direction = Gtk.DirectionType.UP
            self.dont_ignore_scroll_adjustment = True
            self.vadj.set_value(self.vadj.get_value() - self.vadj.get_step_increment())
            return Gdk.EVENT_STOP

        if event.keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
            self.hide_cursor()
            self.scroll_to_direction('left')
            return Gdk.EVENT_STOP

        if event.keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
            self.hide_cursor()
            self.scroll_to_direction('right')
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def on_page_status_changed(self, page, _param):
        if page.status == 'rendering':
            return

        if page.status == 'render':
            self.scroll_lock = True
            return

        self.render_pages_counter += 1

    def on_scroll(self, _scrolledwindow, event):
        if self.scroll_lock:
            # Disable scrolling
            return Gdk.EVENT_STOP

        ret, scroll_direction = event.get_scroll_direction()
        if ret:
            self.scroll_direction = scroll_direction
        else:
            ret, _delta_x, delta_y = event.get_scroll_deltas()
            if ret:
                self.scroll_direction = Gtk.DirectionType.UP if delta_y < 0 else Gtk.DirectionType.DOWN
            else:
                self.scroll_direction = None
                return Gdk.EVENT_PROPAGATE

        return Gdk.EVENT_PROPAGATE

    def on_scroll_changed(self, _vadj, _param):
        # Called when a page is added or rendered
        self.adjust_scroll()

    def on_scroll_value_changed(self, _vadj):
        ret, _state = Gtk.get_current_event_state()
        if not ret and not self.dont_ignore_scroll_adjustment:
            # Scrolling value changed but not by user interaction
            self.add_page_lock = False
            self.scroll_lock = False
            return

        if self.add_page_lock:
            # Cancel scroll
            self.dont_ignore_scroll_adjustment = False
            self.adjust_scroll(emit_signal=False)
            return

        self.add_page_lock = True
        self.dont_ignore_scroll_adjustment = False

        scroll_value = self.vadj.get_value()
        if self.scroll_direction == Gtk.DirectionType.UP:
            position = self.get_position(scroll_value)
        else:
            position = self.get_position(scroll_value + self.reader.size.height)
        page = self.pages[position]

        if page != self.current_page:
            if not page.loadable:
                self.add_page_lock = False

                # Cancel scroll
                value = self.get_page_offset(self.current_page)
                if self.scroll_direction == Gtk.DirectionType.DOWN:
                    _minimal, natural = self.current_page.get_preferred_size()
                    value -= self.reader.size.height - natural.height
                self.adjust_scroll(value=value, emit_signal=False)

                if page.status == 'offlimit':
                    if self.scroll_direction == Gtk.DirectionType.DOWN:
                        message = _('It was the last chapter.')
                    else:
                        message = _('There is no previous chapter.')
                    self.window.show_notification(message, interval=2)

                return

            self.current_page = page
            self.current_page_scroll_value = scroll_value - self.get_page_offset(page)

            # Disable navigation: will be re-enabled if page is loadable
            self.set_interactive(False)

            GLib.idle_add(self.update, page)
            GLib.idle_add(self.save_progress, page)

            self.add_page(Gtk.PositionType.TOP if self.scroll_direction == Gtk.DirectionType.UP else Gtk.PositionType.BOTTOM)
        else:
            self.add_page_lock = False
            self.current_page_scroll_value = scroll_value - self.get_page_offset(page)

    def render_pages(self):
        if self.render_pages_counter == 0:
            return GLib.SOURCE_CONTINUE

        pages = self.pages
        if self.scroll_direction == Gtk.DirectionType.DOWN:
            pages = reversed(pages)

        for page in pages:
            if page.status is None:
                page.render()
                self.render_pages_counter -= 1
            if self.render_pages_counter == 0:
                break

        return GLib.SOURCE_CONTINUE

    def scroll_to_direction(self, direction):
        value = self.vadj.get_value()

        if direction == 'right':
            self.scroll_direction = Gtk.DirectionType.DOWN
            value += self.reader.size.height * 2 / 3
        else:
            self.scroll_direction = Gtk.DirectionType.UP
            value -= self.reader.size.height * 2 / 3

        self.dont_ignore_scroll_adjustment = True
        self.vadj.set_value(value)

    def set_interactive(self, interactive):
        if interactive:
            self.enable_keyboard_and_mouse_click_navigation()
        else:
            self.disable_keyboard_and_mouse_click_navigation()

    def update(self, page, _index=None):
        if page not in self.pages:
            return GLib.SOURCE_REMOVE

        if not page.loadable and page.error is None:
            # Loop until page is loadable or page is on error
            return GLib.SOURCE_CONTINUE

        if page.loadable:
            self.set_interactive(True)

        # Update title, initialize controls and notify user if chapter changed
        if self.current_chapter_id != page.chapter.id:
            self.current_chapter_id = page.chapter.id
            self.reader.update_title(page.chapter)
            self.window.show_notification(page.chapter.title, 2)
            self.reader.controls.init(page.chapter)

        # Update page number and controls page slider
        self.reader.update_page_number(page.index + 1, len(page.chapter.pages) if page.loadable else None)
        self.reader.controls.set_scale_value(page.index + 1)

        return GLib.SOURCE_REMOVE
