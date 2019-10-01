# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import datetime
import threading

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf

from mangascan.activity_indicator import ActivityIndicator


class Page(Gtk.Overlay):
    def __init__(self, reader, chapter_id, index):
        Gtk.Overlay.__init__(self)

        self.reader = reader
        self.window = reader.window

        self.chapter_id = chapter_id
        self.index = index
        self.zoom = dict(active=False)

        self.set_size_request(self.window.get_size().width, -1)

        self.scrolledwindow = Gtk.ScrolledWindow()
        self.scrolledwindow.get_hadjustment().connect('changed', self.adjust_scroll)

        viewport = Gtk.Viewport()
        self.image = Gtk.Image()
        self.pixbuf = None
        viewport.add(self.image)
        self.scrolledwindow.add(viewport)

        # Page number indicator
        self.page_number_label = Gtk.Label()
        self.page_number_label.get_style_context().add_class('reader-page-number-indicator-label')
        self.page_number_label.set_valign(Gtk.Align.END)

        # Activity indicator
        self.activity_indicator = ActivityIndicator()

        self.add_overlay(self.scrolledwindow)
        self.add_overlay(self.page_number_label)
        self.add_overlay(self.activity_indicator)

        self.show_all()

    @property
    def chapter(self):
        return self.sequence.chapter

    @property
    def sequence(self):
        return self.reader.pager.sequences[self.chapter_id]

    def adjust_scroll(self, hadj):
        """ Update page horizontal scrollbar value """
        if self.reader.pager.zoom['active']:
            return

        hadj.set_value(hadj.get_upper() if self.reader.reading_direction == 'right-to-left' else 0)

    def load(self):
        def run():
            page_path = self.chapter.get_page_path(self.index)
            if page_path is None:
                if self.window.application.connected:
                    page_path = self.chapter.get_page(self.index)
                else:
                    self.window.show_notification(_('No Internet connection'))

            GLib.idle_add(complete, page_path)

        def complete(page_path):
            self.chapter.manga.update(dict(last_read=datetime.datetime.now()))

            if page_path:
                self.chapter.update(dict(
                    last_page_read_index=self.index,
                    read=self.index == len(self.chapter.pages) - 1,
                    recent=0,
                ))

                self.pixbuf = Pixbuf.new_from_file(page_path)
            else:
                self.pixbuf = Pixbuf.new_from_resource('/info/febvre/MangaScan/images/missing_file.png')

            self.set_image()

            self.activity_indicator.hide()

            self.chapter.manga.update(dict(last_read=datetime.datetime.now()))

            return False

        self.page_number_label.set_text('{0}/{1}'.format(self.index + 1, len(self.chapter.pages)))
        if self.reader.controls.is_visible:
            self.page_number_label.hide()
        else:
            self.page_number_label.show()

        if self.pixbuf is not None:
            return

        self.activity_indicator.show()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def rescale(self):
        if self.pixbuf:
            self.set_image()

    def resize(self):
        self.set_size_request(self.reader.size.width, -1)

        if self.pixbuf:
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
