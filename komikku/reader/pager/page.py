# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf

from komikku.activity_indicator import ActivityIndicator
from komikku.utils import log_error_traceback


class Page(Gtk.Overlay):
    __gsignals__ = {
        'render-completed': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, pager, chapter, index):
        Gtk.Overlay.__init__(self)

        self.pager = pager
        self.reader = pager.reader
        self.window = pager.window

        self.chapter = chapter
        self.index = index

        self.status = None     # rendering, rendered, offlimit, cleaned
        self.error = None      # connection error or server error
        self.loadable = False  # loadable from disk or downloadable from server (chapter pages are known)

        self.set_size()

        self.scrolledwindow = Gtk.ScrolledWindow()
        if self.reader.reading_direction == 'vertical':
            self.scrolledwindow.get_vadjustment().connect('changed', self.adjust_scroll)
        else:
            self.scrolledwindow.get_hadjustment().connect('changed', self.adjust_scroll)

        self.add(self.scrolledwindow)

        viewport = Gtk.Viewport()
        self.image = Gtk.Image()
        self.pixbuf = None
        viewport.add(self.image)
        self.scrolledwindow.add(viewport)

        # Activity indicator
        self.activity_indicator = ActivityIndicator()
        self.add_overlay(self.activity_indicator)
        self.set_overlay_pass_through(self.activity_indicator, True)  # Allows scrolling in zoom mode

        # Page number indicator
        self.page_number_label = Gtk.Label()
        self.page_number_label.get_style_context().add_class('reader-page-number-indicator-label')
        self.page_number_label.set_valign(Gtk.Align.END)
        self.add_overlay(self.page_number_label)
        self.set_overlay_pass_through(self.page_number_label, True)  # Allows scrolling in zoom mode

        self.show_all()

    @property
    def loaded(self):
        return self.pixbuf is not None

    def adjust_scroll(self, hadj):
        """ Update page horizontal scrollbar value according to reading direction """
        if self.reader.pager.zoom['active']:
            return

        hadj.set_value(hadj.get_upper() if self.reader.reading_direction == 'right-to-left' else 0)

    def clean(self):
        self.status = 'cleaned'
        self.loadable = False
        self.error = None
        self.pixbuf = None
        self.image.clear()

    def on_button_retry_clicked(self, button):
        button.destroy()
        self.render()

    def render(self):
        def run():
            # First, we ensure that chapter's list of pages is known
            if self.chapter.pages is None:
                try:
                    if not self.chapter.update_full():
                        on_error('server')
                        GLib.idle_add(complete)
                        return
                except Exception as e:
                    user_error_message = log_error_traceback(e)
                    on_error('connection', user_error_message)
                    GLib.idle_add(complete)
                    return

            # If page's index is out of pages numbers, page belongs to previous or next chapter.
            if self.index < 0 or self.index > len(self.chapter.pages) - 1:
                if self.index < 0:
                    # Page is the last page of previous chapter
                    self.chapter = self.chapter.manga.get_next_chapter(self.chapter, -1)
                elif self.index > len(self.chapter.pages) - 1:
                    # Page is the first page of next chapter
                    self.chapter = self.chapter.manga.get_next_chapter(self.chapter, 1)

                if self.chapter is not None:
                    # Chapter has changed
                    # Again, we ensure that chapter's list of pages is known
                    if self.chapter.pages is None:
                        try:
                            if not self.chapter.update_full():
                                on_error('server')
                                GLib.idle_add(complete)
                                return
                        except Exception as e:
                            user_error_message = log_error_traceback(e)
                            on_error('connection', user_error_message)
                            GLib.idle_add(complete)
                            return

                    if self.index < 0:
                        # Page is the last page of chapter
                        self.index = len(self.chapter.pages) - 1
                    else:
                        # Page is the first page of chapter
                        self.index = 0

                    self.loadable = True
                else:
                    # Page does not exist, it's out of limit
                    # ie before first page of first chapter or after last page of last chapter
                    self.status = 'offlimit'
                    GLib.idle_add(complete)
                    return
            else:
                self.loadable = True

            page_path = self.chapter.get_page_path(self.index)
            if page_path is None:
                try:
                    page_path = self.chapter.get_page(self.index)
                    if page_path:
                        self.pixbuf = Pixbuf.new_from_file(page_path)
                    else:
                        on_error('server')
                except Exception as e:
                    user_error_message = log_error_traceback(e)
                    on_error('connection', user_error_message)
            else:
                self.pixbuf = Pixbuf.new_from_file(page_path)

            GLib.idle_add(complete)

        def complete():
            if self.status == 'cleaned' or self.get_parent() is None:
                # Page has been removed from pager
                # rare case that occurs during a quick navigation
                return False

            if self.loadable:
                self.page_number_label.set_text('{0}/{1}'.format(self.index + 1, len(self.chapter.pages)))

            if self.loaded:
                self.set_image()
                self.status = 'rendered'

            self.activity_indicator.stop()

            self.emit('render-completed')

            return False

        def on_error(kind, message=None):
            assert kind in ('connection', 'server'), 'Invalid error kind'

            if message is not None:
                self.window.show_notification(message, 2)

            self.error = kind
            self.pixbuf = Pixbuf.new_from_resource('/info/febvre/Komikku/images/missing_file.png')

            self.show_retry_button()

        if self.status is not None and self.error is None:
            return

        self.status = 'rendering'

        self.toggle_page_number()
        self.activity_indicator.start()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def refresh(self):
        self.toggle_page_number()

    def rescale(self):
        if self.status == 'rendered':
            self.set_image()

    def resize(self):
        self.set_size()

        if self.status == 'rendered':
            self.set_image()

    def set_image(self):
        width = self.pixbuf.get_width()
        height = self.pixbuf.get_height()

        adapt_to_width_height = height / (width / self.reader.size.width)
        adapt_to_height_width = width / (height / self.reader.size.height)

        if self.reader.scaling == 'width' or (self.reader.scaling == 'screen' and adapt_to_width_height <= self.reader.size.height):
            # Adapt image to width
            pixbuf = self.pixbuf.scale_simple(
                self.reader.size.width,
                adapt_to_width_height,
                InterpType.BILINEAR
            )
        elif self.reader.scaling == 'height' or (self.reader.scaling == 'screen' and adapt_to_height_width <= self.reader.size.width):
            # Adapt image to height
            pixbuf = self.pixbuf.scale_simple(
                adapt_to_height_width,
                self.reader.size.height,
                InterpType.BILINEAR
            )

        self.image.set_from_pixbuf(pixbuf)

    def set_size(self):
        self.set_size_request(self.reader.size.width, self.reader.size.height)

    def show_retry_button(self):
        button = Gtk.Button.new()
        button.set_image(Gtk.Image.new_from_icon_name('view-refresh-symbolic', Gtk.IconSize.LARGE_TOOLBAR))
        button.set_image_position(Gtk.PositionType.TOP)
        button.set_always_show_image(True)
        button.set_label(_('Retry'))
        button.set_valign(Gtk.Align.CENTER)
        button.set_halign(Gtk.Align.CENTER)
        button.connect('clicked', self.on_button_retry_clicked)

        self.add_overlay(button)
        button.show()

    def toggle_page_number(self):
        if self.reader.controls.is_visible:
            self.page_number_label.hide()
        else:
            self.page_number_label.show()
