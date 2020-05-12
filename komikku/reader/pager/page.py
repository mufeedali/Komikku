# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository.GdkPixbuf import PixbufAnimation

from komikku.activity_indicator import ActivityIndicator
from komikku.utils import Imagebuf
from komikku.utils import log_error_traceback



class Page(Gtk.Overlay):
    __gsignals__ = {
        'rendered': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, pager, chapter, index):
        Gtk.Overlay.__init__(self)

        self.pager = pager
        self.reader = pager.reader
        self.window = pager.window

        self.chapter = chapter
        self.index = index
        self.path = None

        self.status = None     # rendering, rendered, offlimit, cleaned
        self.error = None      # connection error, server error or corrupt file error
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
        self.imagebuf = None
        viewport.add(self.image)
        self.scrolledwindow.add(viewport)

        # Activity indicator
        self.activity_indicator = ActivityIndicator()
        self.add_overlay(self.activity_indicator)
        self.set_overlay_pass_through(self.activity_indicator, True)  # Allows scrolling in zoom mode

        self.show_all()


    @property
    def animated(self):
        return self.imagebuf.animated

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
        self.imagebuf = None
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
                    self.chapter = self.reader.manga.get_next_chapter(self.chapter, -1)
                elif self.index > len(self.chapter.pages) - 1:
                    # Page is the first page of next chapter
                    self.chapter = self.reader.manga.get_next_chapter(self.chapter, 1)

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
                        self.path = page_path
                    else:
                        on_error('server')
                except Exception as e:
                    user_error_message = log_error_traceback(e)
                    on_error('connection', user_error_message)
            else:
                self.path = page_path

            GLib.idle_add(complete)

        def complete():
            if self.status == 'cleaned' or self.get_parent() is None:
                # Page has been removed from pager
                # rare case that occurs during a quick navigation
                return False

            if self.status != 'offlimit':
                self.set_image()
                self.status = 'rendered'

            self.activity_indicator.stop()

            self.emit('rendered')

            return False

        def on_error(kind, message=None):
            assert kind in ('connection', 'server', ), 'Invalid error kind'

            if message is not None:
                self.window.show_notification(message, 2)

            self.error = kind

            self.show_retry_button()

        if self.status is not None and self.error is None:
            return

        self.imagebuf = None
        self.status = 'rendering'

        self.activity_indicator.start()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def rescale(self):
        if self.status == 'rendered':
            self.set_image()

    def resize(self):
        self.set_size()

        if self.status == 'rendered':
            self.set_image()

    def set_image(self):
        if self.imagebuf is None:
            if self.path is None:
                self.imagebuf = Imagebuf.new_from_resource('/info/febvre/Komikku/images/missing_file.png')
            else:
                self.imagebuf = Imagebuf.new_from_file(self.path)
                if self.imagebuf is None:
                    GLib.unlink(self.path)

                    self.show_retry_button()
                    self.window.show_notification(_('Failed to load image'), 2)

                    self.error = 'corrupt_file'
                    self.imagebuf = Imagebuf.new_from_resource('/info/febvre/Komikku/images/missing_file.png')

        # Crop image borders
        imagebuf = self.imagebuf.crop_borders() if self.reader.manga.borders_crop == 1 else self.imagebuf

        # Adjust image
        if self.reader.scaling != 'original':
            adapt_to_width_height = imagebuf.height / (imagebuf.width / self.reader.size.width)
            adapt_to_height_width = imagebuf.width / (imagebuf.height / self.reader.size.height)

            if self.reader.scaling == 'width' or (self.reader.scaling == 'screen' and adapt_to_width_height <= self.reader.size.height):
                # Adapt image to width
                pixbuf = imagebuf.get_scaled_pixbuf(self.reader.size.width, adapt_to_width_height, False)
            elif self.reader.scaling == 'height' or (self.reader.scaling == 'screen' and adapt_to_height_width <= self.reader.size.width):
                # Adapt image to height
                pixbuf = imagebuf.get_scaled_pixbuf(adapt_to_height_width, self.reader.size.height, False)
        else:
            pixbuf = imagebuf.get_pixbuf()

        if isinstance(pixbuf, PixbufAnimation):
            self.image.set_from_animation(pixbuf)
        else:
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
