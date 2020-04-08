# Copyright (C) 2019-2020 Valéry Febvre
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

        self.box = Gtk.Box(spacing=0)  # Orientation is not kown yet
        self.viewport.add(self.box)

        self.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.KEY_PRESS_MASK |
            Gdk.EventMask.SMOOTH_SCROLL_MASK
        )

        self.connect('button-press-event', self.on_btn_press)
        self.window.connect('key-press-event', self.on_key_press)
        self.connect('motion-notify-event', self.on_motion_notify)
        self.connect('scroll-event', self.on_scroll)

        self.show_all()

    @property
    def pages(self):
        return self.box.get_children()

    def adjust_scroll(self, position=1, animate=True, duration=250):
        """ Scroll to a page """

        def ease_out_cubic(t):
            t = t - 1
            return t * t * t + 1

        def move(scrolledwindow, clock):
            now = clock.get_frame_time()
            if now < end_time and adj.get_value() != end:
                t = (now - start_time) / (end_time - start_time)
                # t = ease_out_cubic(t)

                adj.set_value(start + t * (end - start))

                return True

            adj.set_value(end)
            self.scroll_lock = False

            return False

        if self.reader.reading_direction == 'vertical':
            adj = self.get_vadjustment()
            end = position * self.reader.size.height
        else:
            adj = self.get_hadjustment()
            end = position * self.reader.size.width
        start = adj.get_value()

        if start - end == 0:
            return

        if animate:
            self.scroll_lock = True

            clock = self.get_frame_clock()
            if clock:
                start_time = clock.get_frame_time()
                end_time = start_time + 1000 * duration

                self.add_tick_callback(move)
        else:
            adj.set_value(end)

    def clear(self):
        self.current_page = None

        for page in self.pages:
            page.clean()
            page.destroy()

    def crop_pages_borders(self):
        for page in self.pages:
            if page.status == 'rendered' and page.error is None:
                page.set_image()

    def goto_page(self, page_index):
        if self.pages[0].index == page_index and self.pages[0].chapter == self.current_page.chapter:
            self.switchto_page('left')
        elif self.pages[2].index == page_index and self.pages[2].chapter == self.current_page.chapter:
            self.switchto_page('right')
        else:
            self.init(self.current_page.chapter, page_index)

    def hide_cursor(self):
        self.get_window().set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), 'none'))

    def init(self, chapter, page_index=None):
        self.reader.update_title(chapter)

        if page_index is None:
            if chapter.read:
                page_index = 0
            elif chapter.last_page_read_index is not None:
                page_index = chapter.last_page_read_index
            else:
                page_index = 0

        self.clear()
        self.set_orientation()

        direction = 1 if self.reader.reading_direction == 'right-to-left' else -1
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
        center_page.connect('rendered', self.on_first_page_rendered)
        center_page.render()

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

        return Gdk.EVENT_STOP

    def on_double_click(self, event):
        # Zoom/unzoom

        def on_adjustment_change(hadj, vadj, h_value, v_value):
            hadj.disconnect(handler_id)

            def adjust_scroll():
                hadj.set_value(h_value)
                vadj.set_value(v_value)

            GLib.idle_add(adjust_scroll)

        page = self.current_page

        if page.status != 'rendered' or page.error is not None:
            return

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

            handler_id = hadj.connect('changed', on_adjustment_change, vadj, h_value, v_value)

            scaled_pixbuf = pixbuf.scale_simple(zoom_width, zoom_height, InterpType.BILINEAR)

            image.set_from_pixbuf(scaled_pixbuf)

            self.zoom['active'] = True
        else:
            handler_id = hadj.connect(
                'changed', on_adjustment_change, vadj, self.zoom['orig_hadj_value'], self.zoom['orig_vadj_value'])

            page.set_image()

            self.zoom['active'] = False

    def on_first_page_rendered(self, page):
        if not page.chapter.pages:
            return
        self.reader.update_page_number(page.index + 1, len(page.chapter.pages))
        self.reader.controls.init()
        self.reader.controls.set_scale_value(page.index + 1)

        GLib.idle_add(self.on_page_switch, page)

        self.pages[0].render()
        self.pages[2].render()

    def on_key_press(self, widget, event):
        if self.window.page != 'reader':
            return Gdk.EVENT_PROPAGATE

        modifiers = Gtk.accelerator_get_default_mod_mask()
        if (event.state & modifiers) != 0:
            return Gdk.EVENT_PROPAGATE

        if event.keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left, Gdk.KEY_Right, Gdk.KEY_KP_Right):
            # Hide mouse cursor when using keyboard navigation
            self.hide_cursor()

            page = self.current_page
            hadj = page.scrolledwindow.get_hadjustment()

            if event.keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
                if hadj.get_value() == 0 and self.zoom['active'] is False:
                    self.switchto_page('left')
                    return Gdk.EVENT_STOP

                page.scrolledwindow.emit('scroll-child', Gtk.ScrollType.STEP_LEFT, False)
                return Gdk.EVENT_STOP

            if hadj.get_value() + self.reader.size.width == hadj.get_upper() and self.zoom['active'] is False:
                self.switchto_page('right')
                return Gdk.EVENT_STOP

            page.scrolledwindow.emit('scroll-child', Gtk.ScrollType.STEP_RIGHT, False)
            return Gdk.EVENT_STOP

        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up, Gdk.KEY_Down, Gdk.KEY_KP_Down):
            # Hide mouse cursor when using keyboard navigation
            self.hide_cursor()

            page = self.current_page
            vadj = page.scrolledwindow.get_vadjustment()

            if event.keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
                if self.reader.reading_direction == 'vertical' and vadj.get_value() + self.reader.size.height == vadj.get_upper():
                    self.switchto_page('right')
                    return Gdk.EVENT_STOP

                # If image height is greater than viewport height, arrow keys should scroll page down
                # Emit scroll signal: one step down
                page.scrolledwindow.emit('scroll-child', Gtk.ScrollType.STEP_DOWN, False)
                return Gdk.EVENT_STOP

            if self.reader.reading_direction == 'vertical' and vadj.get_value() == 0:
                self.switchto_page('left')

                # After switching pages, go to the end of the page that is now the current page
                vadj = self.current_page.scrolledwindow.get_vadjustment()
                vadj.set_value(vadj.get_upper() - self.reader.size.height)
                return Gdk.EVENT_STOP

            # If image height is greater than viewport height, arrow keys should scroll page up
            # Emit scroll signal: one step up
            page.scrolledwindow.emit('scroll-child', Gtk.ScrollType.STEP_UP, False)
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def on_motion_notify(self, widget, event):
        if self.get_window().get_cursor():
            # Cursor is hidden during keyboard navigation
            # Make cursor visible again when mouse is moved
            self.show_cursor()

        return Gdk.EVENT_PROPAGATE

    def on_page_switch(self, page):
        # Loop as long as the page rendering is not ended
        if page.status == 'rendering':
            return True

        if page.status != 'rendered' or page.error is not None:
            return False

        chapter = page.chapter

        # Update manga last read time
        self.reader.manga.update(dict(last_read=datetime.datetime.now()))

        # Mark page as read
        chapter.pages[page.index]['read'] = True

        # Check if chapter has been fully read
        chapter_is_read = True
        for chapter_page in reversed(chapter.pages):
            if not chapter_page.get('read'):
                chapter_is_read = False
                break

        # Update chapter
        chapter.update(dict(
            pages=chapter.pages,
            last_page_read_index=page.index,
            read=chapter_is_read,
            recent=0,
        ))

        return False

    def on_scroll(self, widget, event):
        # Stop GDK_SCROLL_SMOOTH events propagation
        # mouse and touch pad (2 fingers) scrolling
        return Gdk.EVENT_STOP

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
            self.reader.toggle_controls()

        return False

    def rescale_pages(self):
        for page in self.pages:
            page.rescale()

    def resize_pages(self):
        for page in self.pages:
            page.resize()

        self.adjust_scroll(animate=False)

    def reverse_pages(self):
        self.box.reorder_child(self.pages[0], 2)
        self.box.reorder_child(self.pages[1], 0)

        self.adjust_scroll(animate=False)

    def set_orientation(self):
        """ Set box orientation """

        def on_adjustment_change(adj):
            self.adjust_scroll(animate=False)
            adj.disconnect(handler_id)

        if self.reader.reading_direction == 'vertical':
            handler_id = self.get_vadjustment().connect('changed', on_adjustment_change)
            self.box.props.orientation = Gtk.Orientation.VERTICAL
        else:
            handler_id = self.get_hadjustment().connect('changed', on_adjustment_change)
            self.box.props.orientation = Gtk.Orientation.HORIZONTAL

    def show_cursor(self):
        self.get_window().set_cursor(None)

    def switchto_page(self, position):
        if self.scroll_lock:
            return

        if position == 'left':
            page = self.pages[0]
        elif position == 'right':
            page = self.pages[2]

        if page.status == 'offlimit':
            # We reached first or last chapter
            if page.index < 0:
                message = _('There is no previous chapter.')
            else:
                message = _('It was the last chapter.')
            self.window.show_notification(message, interval=2)
            return

        if not page.loadable:
            # Page index and pages of the chapter to which page belongs must be known to be able to move to another page
            return

        chapter_changed = self.current_page.chapter != page.chapter

        self.current_page = page

        # Update title and notify if chapter changed
        if chapter_changed:
            self.reader.update_title(page.chapter)
            self.window.show_notification(page.chapter.title, 2)
            self.reader.controls.init()

        # Update page number and controls page slider
        self.reader.update_page_number(page.index + 1, len(page.chapter.pages))
        self.reader.controls.set_scale_value(page.index + 1)

        GLib.idle_add(self.on_page_switch, page)

        if position == 'left':
            GLib.idle_add(self.adjust_scroll, 0)

            def add_page(current_page):
                if self.scroll_lock:
                    return True

                # Clean and destroy 3rd page
                self.pages[2].clean()
                self.pages[2].destroy()  # will remove it from box

                direction = 1 if self.reader.reading_direction == 'right-to-left' else -1

                new_page = Page(self, current_page.chapter, current_page.index + direction)
                self.box.pack_start(new_page, True, True, 0)
                self.box.reorder_child(new_page, 0)
                new_page.render()

                self.adjust_scroll(animate=False)

                return False

            GLib.idle_add(add_page, page)

        elif position == 'right':
            GLib.idle_add(self.adjust_scroll, 2)

            def add_page(current_page):
                if self.scroll_lock:
                    return True

                # Clean and destroy 1st page
                self.pages[0].clean()
                self.pages[0].destroy()  # will remove it from box

                self.adjust_scroll(animate=False)

                direction = -1 if self.reader.reading_direction == 'right-to-left' else 1

                new_page = Page(self, current_page.chapter, current_page.index + direction)
                self.box.pack_start(new_page, True, True, 0)
                new_page.render()

                return False

            GLib.idle_add(add_page, page)
