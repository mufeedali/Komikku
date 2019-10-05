# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading

from gi.repository import GLib
from gi.repository import Gtk

from mangascan.reader.pager.page import Page


class Sequence(Gtk.Box):
    def __init__(self, reader, chapter):
        self.reader = reader
        self.pager = reader.pager
        self.window = reader.window

        self.chapter = chapter
        self.pages = []

        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.show()

        # Create first page
        page = Page(self, self.chapter.id, 0)
        page.activity_indicator.start()
        self.pack_page(page)

    def load(self, page_index, on_complete_callback, on_error_callback):
        def run(page_index):
            if self.chapter.update_full():
                GLib.idle_add(complete, page_index)
            else:
                GLib.idle_add(error)

        def complete(page_index):
            # Create pages (we skip first which already exists)
            for index in range(1, len(self.chapter.pages)):
                page = Page(self, self.chapter.id, index)
                self.pack_page(page)

            # Force immediate rendering
            self.queue_draw()
            while Gtk.events_pending():
                Gtk.main_iteration()

            on_complete_callback(page_index)

            return False

        def error():
            self.window.show_notification(_('Oops, failed to retrieve chapter info. Please try again.'))

            on_error_callback()

            return False

        thread = threading.Thread(target=run, args=[page_index, ])
        thread.daemon = True
        thread.start()

    def pack_page(self, page):
        self.pages.append(page)

        if self.reader.reading_direction == 'right-to-left':
            self.pack_end(page, True, True, 0)
        else:
            self.pack_start(page, True, True, 0)

    def reverse_pages(self):
        for child in self.get_children():
            self.remove(child)

        for page in self.pages:
            if self.reader.reading_direction == 'right-to-left':
                self.pack_end(page, True, True, 0)
            else:
                self.pack_start(page, True, True, 0)

    def rescale_pages(self):
        for page in self.pages:
            page.rescale()

    def resize_pages(self):
        for page in self.pages:
            page.resize()
