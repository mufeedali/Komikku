# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf

from mangascan.activity_indicator import ActivityIndicator


class Page(Gtk.Overlay):
    __gsignals__ = {
        'load-completed': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, pager, chapter, index):
        Gtk.Overlay.__init__(self)

        self.pager = pager
        self.reader = pager.reader
        self.window = pager.window

        self.chapter = chapter
        self.index = index

        self.status = None

        self.set_size_request(self.window.get_size().width, -1)

        self.scrolledwindow = Gtk.ScrolledWindow()
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

        # Page number indicator
        self.page_number_label = Gtk.Label()
        self.page_number_label.get_style_context().add_class('reader-page-number-indicator-label')
        self.page_number_label.set_valign(Gtk.Align.END)
        self.add_overlay(self.page_number_label)

        self.show_all()

    def adjust_scroll(self, hadj):
        """ Update page horizontal scrollbar value according to reading direction """
        if self.reader.pager.zoom['active']:
            return

        hadj.set_value(hadj.get_upper() if self.reader.reading_direction == 'right-to-left' else 0)

    def clean(self):
        self.status = None
        self.pixbuf = None
        self.image.clear()

    def load(self):
        def run():
            # First, we ensure that chapter's list of pages is known
            if self.chapter.pages is None:
                if self.window.application.connected:
                    if not self.chapter.update_full():
                        GLib.idle_add(complete, None)
                        return
                else:
                    self.window.show_notification(_('No Internet connection'))
                    GLib.idle_add(complete, None)
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
                        if self.window.application.connected:
                            if not self.chapter.update_full():
                                GLib.idle_add(complete, None)
                                return
                        else:
                            self.window.show_notification(_('No Internet connection'))
                            GLib.idle_add(complete, None)
                            return

                    if self.index < 0:
                        # Page is the last page of chapter
                        self.index = len(self.chapter.pages) - 1
                    else:
                        # Page is the first page of chapter
                        self.index = 0

                else:
                    GLib.idle_add(complete, None)
                    return

            page_path = self.chapter.get_page_path(self.index)
            if page_path is None:
                if self.window.application.connected:
                    page_path = self.chapter.get_page(self.index)
                else:
                    self.window.show_notification(_('No Internet connection'))

            GLib.idle_add(complete, page_path)

        def complete(page_path):
            if self.chapter.pages is not None:
                self.page_number_label.set_text('{0}/{1}'.format(self.index + 1, len(self.chapter.pages)))

            if page_path:
                self.pixbuf = Pixbuf.new_from_file(page_path)
                self.status = 'loaded'
            else:
                self.pixbuf = Pixbuf.new_from_resource('/info/febvre/MangaScan/images/missing_file.png')
                self.status = 'error'

            self.set_image()

            self.activity_indicator.stop()

            self.emit('load-completed')

            return False

        if self.status in ('loaded', 'loading'):
            return

        self.status = 'loading'

        if self.reader.controls.is_visible:
            self.page_number_label.hide()
        else:
            self.page_number_label.show()

        self.activity_indicator.start()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def rescale(self):
        if self.status in ('error', 'loaded'):
            self.set_image()

    def resize(self):
        self.set_size_request(self.reader.size.width, -1)

        if self.status in ('error', 'loaded'):
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
