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
from komikku.utils import crop_pixbuf
from komikku.utils import Imagebuf
from komikku.utils import log_error_traceback


class Page(Gtk.Overlay):
    __gsignals__ = {
        'rendered': (GObject.SIGNAL_RUN_FIRST, None, (bool, )),
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

        self.cropped = False
        self.last_hadj_value = None
        self.last_vadj_value = None

        self.set_size()

        self.scrolledwindow = Gtk.ScrolledWindow()
        self.viewport = Gtk.Viewport()
        self.image = Gtk.Image()
        self.imagebuf = None
        self.viewport.add(self.image)
        self.scrolledwindow.add(self.viewport)
        self.add(self.scrolledwindow)

        if self.reader.reading_direction == 'vertical':
            self.scrolledwindow.get_vadjustment().connect('changed', self.on_scroll_changed, 'vertical')
            self.scrolledwindow.get_vadjustment().connect('value-changed', self.on_scroll_value_changed, 'vertical')
        else:
            self.scrolledwindow.get_hadjustment().connect('changed', self.on_scroll_changed, 'horizontal')
            self.scrolledwindow.get_hadjustment().connect('value-changed', self.on_scroll_value_changed, 'horizontal')

        self.scrolledwindow.connect('edge-overshot', self.on_edge_overshotted)

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

    def clean(self):
        self.status = 'cleaned'
        self.loadable = False
        self.imagebuf = None
        self.image.clear()

    def on_button_retry_clicked(self, button):
        button.destroy()
        self.render(retry=True)

    def on_edge_overshotted(self, widget_, position):
        """During scrolling, a lower or upper limit has been surpassed.

        To allow 2-fingers swipe gesture, we crop image to disable scrolling (otherwise, Gtk.ScrolledWindow consumes scroll events)
        Full image must be restored at end of swipe
        """

        if self.pager.zoom['active']:
            return

        if self.reader.reading_direction == 'vertical':
            if position == Gtk.PositionType.BOTTOM:
                self.set_image(crop='top')
            elif position == Gtk.PositionType.TOP:
                self.set_image(crop='bottom')
        else:
            if position == Gtk.PositionType.LEFT:
                self.set_image(crop='right')
            elif position == Gtk.PositionType.RIGHT:
                self.set_image(crop='left')

    def on_scroll_changed(self, adj, type):
        """Set/restore page scrollbar position when image is set or updated"""

        if self.pager.zoom['active']:
            return

        if type == 'horizontal':
            adj.set_value(self.last_hadj_value if self.last_hadj_value is not None else adj.get_upper())
        else:
            adj.set_value(self.last_vadj_value if self.last_vadj_value is not None else 0)

    def on_scroll_value_changed(self, adj_, type):
        """Store last horizontal or vertical scroll value"""

        if self.pager.zoom['active']:
            return

        hadj = self.scrolledwindow.get_hadjustment()
        vadj = self.scrolledwindow.get_vadjustment()

        if type == 'horizontal' and hadj.get_upper() > self.reader.size.width:
            self.last_hadj_value = hadj.get_value()
        elif type == 'vertical' and vadj.get_upper() > self.reader.size.height:
            self.last_vadj_value = vadj.get_value()

    def render(self, retry=False):
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

            self.emit('rendered', retry)

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
        self.error = None

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

    def set_image(self, crop=None):
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

            if not self.animated:
                if self.reader.scaling == 'width' or (self.reader.scaling == 'screen' and adapt_to_width_height <= self.reader.size.height):
                    # Adapt image to width
                    pixbuf = imagebuf.get_scaled_pixbuf(self.reader.size.width, adapt_to_width_height, False)
                elif self.reader.scaling == 'height' or (self.reader.scaling == 'screen' and adapt_to_height_width <= self.reader.size.width):
                    # Adapt image to height
                    pixbuf = imagebuf.get_scaled_pixbuf(adapt_to_height_width, self.reader.size.height, False)
            else:
                # NOTE: Special case of animated images (GIF)
                # They cannot be cropped, which would prevent navigation by 2-finger swipe gesture
                # Moreover, it's more comfortable to view them in full (fit viewport)

                if adapt_to_width_height <= self.reader.size.height:
                    # Adapt image to width
                    pixbuf = imagebuf.get_scaled_pixbuf(self.reader.size.width, adapt_to_width_height, False)
                elif adapt_to_height_width <= self.reader.size.width:
                    # Adapt image to height
                    pixbuf = imagebuf.get_scaled_pixbuf(adapt_to_height_width, self.reader.size.height, False)
        else:
            pixbuf = imagebuf.get_pixbuf()

        if crop is not None:
            if crop in ('right', 'bottom'):
                pixbuf = crop_pixbuf(pixbuf, 0, 0, self.reader.size.width, self.reader.size.height)
            elif crop == 'left':
                pixbuf = crop_pixbuf(pixbuf, pixbuf.get_width() - self.reader.size.width, 0, self.reader.size.width, self.reader.size.height)
            elif crop == 'top':
                pixbuf = crop_pixbuf(pixbuf, 0, pixbuf.get_height() - self.reader.size.height, self.reader.size.width, self.reader.size.height)
            self.cropped = True
        else:
            self.cropped = False

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
