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
    chapter = None
    pages = None

    def __init__(self, reader, chapter):
        self.reader = reader
        self.pager = reader.pager
        self.window = reader.window

        self.chapter = chapter

        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.show()

        # Add a fake page used during loading phase only
        page = Page(self.reader, self.chapter.id, 0)
        self.pack_pages([page, ])

    def load(self, page_index, on_complete_callback):
        def run(page_index):
            if self.chapter.update_full():
                GLib.idle_add(complete, page_index)
            else:
                GLib.idle_add(error)

        def complete(page_index):
            pages = []
            for index, page in enumerate(self.chapter.pages):
                page = Page(self.reader, self.chapter.id, index)
                pages.append(page)

            self.pack_pages(pages)

            self.reader.activity_indicator.hide()

            on_complete_callback(page_index)

            return False

        def error():
            self.reader.activity_indicator.hide()
            self.window.show_notification(_('Oops, failed to retrieve chapter info. Please try again.'))

            return False

        self.reader.activity_indicator.show()

        thread = threading.Thread(target=run, args=[page_index, ])
        thread.daemon = True
        thread.start()

    def pack_pages(self, pages=None):
        for child in self.get_children():
            self.remove(child)

        if pages is not None:
            self.pages = pages

        for page in self.pages:
            if self.reader.reading_direction == 'right-to-left':
                self.pack_end(page, True, True, 0)
            else:
                self.pack_start(page, True, True, 0)

        # Force immediate rendering
        self.queue_draw()
        while Gtk.events_pending():
            Gtk.main_iteration()

    def rescale_pages(self):
        for page in self.pages:
            page.rescale()

    def resize_pages(self):
        for page in self.pages:
            page.resize()
