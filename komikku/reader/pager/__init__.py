# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import datetime
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Handy
from gi.repository.GdkPixbuf import InterpType

from komikku.reader.pager.page import Page


class Pager(Handy.Carousel):
    current_page = None

    btn_press_handler_id = None
    btn_press_timeout_id = None
    key_press_handler_id = None
    default_double_click_time = Gtk.Settings.get_default().get_property('gtk-double-click-time')
    zoom = dict(active=False)

    def __init__(self, reader):
        super().__init__()

        self.reader = reader
        self.window = reader.window

        self.set_animation_duration(500)

        self.connect('motion-notify-event', self.on_motion_notify)
        self.connect('page-changed', self.on_page_changed)
        self.window.connect('scroll-event', self.on_scroll)

    @property
    def pages(self):
        return self.get_children()

    def clear(self):
        self.current_page = None

        for page in self.pages:
            page.clean()
            page.destroy()

    def crop_pages_borders(self):
        for page in self.pages:
            if page.status == 'rendered' and page.error is None:
                page.set_image()

    def disable_keyboard_and_mouse_click_navigation(self):
        # Keyboard
        if self.key_press_handler_id:
            self.window.disconnect(self.key_press_handler_id)
            self.key_press_handler_id = None

        # Mouse click
        if self.btn_press_handler_id:
            self.disconnect(self.btn_press_handler_id)
            self.btn_press_handler_id = None

    def enable_keyboard_and_mouse_click_navigation(self):
        # Keyboard
        if self.key_press_handler_id is None:
            self.key_press_handler_id = self.window.connect('key-press-event', self.on_key_press)

        # Mouse click
        if self.btn_press_handler_id is None:
            self.btn_press_handler_id = self.connect('button-press-event', self.on_btn_press)

    def goto_page(self, page_index):
        if self.pages[0].index == page_index and self.pages[0].chapter == self.current_page.chapter:
            self.scroll_to_direction('left')
        elif self.pages[2].index == page_index and self.pages[2].chapter == self.current_page.chapter:
            self.scroll_to_direction('right')
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

        # Center page
        center_page = Page(self, chapter, page_index)
        self.prepend(center_page)
        self.current_page = center_page
        self.scroll_to(center_page)

        # Left page
        left_page = Page(self, chapter, page_index + direction)
        self.prepend(left_page)

        # Right page
        right_page = Page(self, chapter, page_index - direction)
        self.insert(right_page, -1)

        center_page.connect('rendered', self.on_first_page_rendered)
        center_page.render()

    def add_page(self, position):
        if position == 'start':
            self.pages[2].clean()
            self.pages[2].destroy()  # will remove it from carousel

            page = self.pages[0]
            direction = 1 if self.reader.reading_direction == 'right-to-left' else -1
            new_page = Page(self, page.chapter, page.index + direction)
            self.prepend(new_page)
        else:
            self.pages[0].clean()
            self.pages[0].destroy()  # will remove it from carousel

            page = self.pages[-1]
            direction = -1 if self.reader.reading_direction == 'right-to-left' else 1
            new_page = Page(self, page.chapter, page.index + direction)
            self.insert(new_page, 2)

        new_page.render()

    def on_btn_press(self, widget, event):
        if event.button == 1:
            if self.btn_press_timeout_id is None and event.type == Gdk.EventType.BUTTON_PRESS:
                # Schedule single click event to be able to detect double click
                self.btn_press_timeout_id = GLib.timeout_add(self.default_double_click_time + 100, self.on_single_click, event.copy())

            elif event.type == Gdk.EventType._2BUTTON_PRESS:
                # Remove scheduled single click event
                if self.btn_press_timeout_id:
                    GLib.source_remove(self.btn_press_timeout_id)
                    self.btn_press_timeout_id = None

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

        if page.status != 'rendered' or page.error is not None or page.animated:
            return

        hadj = page.scrolledwindow.get_hadjustment()
        vadj = page.scrolledwindow.get_vadjustment()

        if self.zoom['active'] is False:
            self.set_interactive(False)

            image = page.image
            pixbuf = page.imagebuf.get_pixbuf()

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
            self.set_interactive(True)

            handler_id = hadj.connect(
                'changed', on_adjustment_change, vadj, self.zoom['orig_hadj_value'], self.zoom['orig_vadj_value'])

            page.set_image()

            self.zoom['active'] = False

    def on_first_page_rendered(self, page):
        if not page.chapter.pages:
            self.window.show_notification(_('This chapter is inaccessible.'), 2)
            return

        self.reader.update_page_number(page.index + 1, len(page.chapter.pages))
        self.reader.controls.init(page.chapter)
        self.reader.controls.set_scale_value(page.index + 1)

        GLib.idle_add(self.save_state, page)

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

            page = self.pages[1]
            hadj = page.scrolledwindow.get_hadjustment()

            if event.keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
                if hadj.get_value() == 0 and self.zoom['active'] is False:
                    self.scroll_to_direction('left')
                    return Gdk.EVENT_STOP

                page.scrolledwindow.emit('scroll-child', Gtk.ScrollType.STEP_LEFT, False)
                return Gdk.EVENT_STOP

            if hadj.get_value() + self.reader.size.width == hadj.get_upper() and self.zoom['active'] is False:
                self.scroll_to_direction('right')
                return Gdk.EVENT_STOP

            page.scrolledwindow.emit('scroll-child', Gtk.ScrollType.STEP_RIGHT, False)
            return Gdk.EVENT_STOP

        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up, Gdk.KEY_Down, Gdk.KEY_KP_Down):
            # Hide mouse cursor when using keyboard navigation
            self.hide_cursor()

            page = self.pages[1]
            vadj = page.scrolledwindow.get_vadjustment()

            if event.keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
                if self.reader.reading_direction == 'vertical' and vadj.get_value() + self.reader.size.height == vadj.get_upper():
                    self.scroll_to_direction('right')
                    return Gdk.EVENT_STOP

                # If image height is greater than viewport height, arrow keys should scroll page down
                # Emit scroll signal: one step down
                page.scrolledwindow.emit('scroll-child', Gtk.ScrollType.STEP_DOWN, False)
                return Gdk.EVENT_STOP

            if self.reader.reading_direction == 'vertical' and vadj.get_value() == 0:
                self.scroll_to_direction('left')

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

    def on_page_changed(self, carousel, index):
        self.enable_keyboard_and_mouse_click_navigation()

        # Set Hdy.Carousel non-interactive by default to be able to detect scrolling in pages (with scroll-event event)
        self.set_interactive(False)

        if self.current_page.cropped:
            # Previous page's image has been cropped to allow 2-fingers swipe gesture, it must be restored
            self.current_page.set_image()

        if index == 1:
            # Partial swipe
            return

        page = self.pages[index]

        if page.status == 'offlimit':
            GLib.idle_add(self.scroll_to, self.pages[1])

            if page.index == -1:
                message = _('There is no previous chapter.')
            else:
                message = _('It was the last chapter.')
            self.window.show_notification(message, interval=2)

            return

        # Update title and notify if chapter changed
        if self.current_page.chapter != page.chapter:
            self.reader.update_title(page.chapter)
            self.window.show_notification(page.chapter.title, 2)
            self.reader.controls.init(page.chapter)

        # Update page number and controls page slider
        self.reader.update_page_number(page.index + 1, len(page.chapter.pages))
        self.reader.controls.set_scale_value(page.index + 1)

        GLib.idle_add(self.save_state, page)

        self.add_page('start' if index == 0 else 'end')

        self.current_page = page

    def on_scroll(self, widget_, event):
        # A scroll event emitted means that page's image is not scrollable (otherwise, Gtk.ScrolledWindow consumes scroll events)
        # Hdy.Carousel must be set interactive to allow 2-fingers swipe gesture
        self.set_interactive(True)
        return Gdk.EVENT_PROPAGATE

    def on_single_click(self, event):
        self.btn_press_timeout_id = None

        if event.x < self.reader.size.width / 3:
            # 1st third of the page
            if self.zoom['active']:
                return False

            self.scroll_to_direction('left')
        elif event.x > 2 * self.reader.size.width / 3:
            # Last third of the page
            if self.zoom['active']:
                return False

            self.scroll_to_direction('right')
        else:
            # Center part of the page: toggle controls
            self.reader.toggle_controls()

        return False

    def rescale_pages(self):
        self.zoom['active'] = False

        for page in self.pages:
            page.rescale()

    def resize_pages(self):
        self.zoom['active'] = False

        for page in self.pages:
            page.resize()

    def reverse_pages(self):
        self.reorder(self.pages[0], -1)
        self.reorder(self.pages[0], 1)

    def save_state(self, page):
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

    def scroll_to_direction(self, direction):
        if direction == 'left':
            page = self.pages[0]
        elif direction == 'right':
            page = self.pages[-1]

        if page.status == 'offlimit':
            # We reached first or last chapter
            if direction == 'left':
                message = _('It was the last chapter.')
            elif direction == 'right':
                message = _('There is no previous chapter.')
            self.window.show_notification(message, interval=2)

            return

        if page == self.current_page:
            # Can occur during a quick keyboard navigation (when holding down an arrow key)
            return

        if not page.loadable:
            # Page index and pages of the chapter to which page belongs must be known to be able to move to another page
            return

        self.disable_keyboard_and_mouse_click_navigation()
        self.set_interactive(True)

        self.scroll_to(page)

    def set_orientation(self):
        if self.reader.reading_direction == 'vertical':
            self.props.orientation = Gtk.Orientation.VERTICAL
        else:
            self.props.orientation = Gtk.Orientation.HORIZONTAL

    def show_cursor(self):
        self.get_window().set_cursor(None)
