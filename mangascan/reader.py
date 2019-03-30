import datetime
import threading

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf


class Reader():
    pixbuf = None
    size = None

    def __init__(self, window):
        self.window = window
        self.builder = window.builder

        self.viewport = self.builder.get_object('reader_page_viewport')
        self.scrolledwindow = self.viewport.get_parent()
        self.image = Gtk.Image()

        self.window.connect('check-resize', self.on_resize)
        self.scrolledwindow.connect('button-press-event', self.on_button_press)

    def clear(self):
        for child in self.viewport.get_children():
            self.viewport.remove(child)

    def init(self, chapter):
        self.chapter = chapter

        chapter.manga.update(dict(last_read=datetime.datetime.now()))

        self.render_page(self.chapter.last_page_read_index or 0)

    def on_button_press(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if event.x > self.size.width / 2:
                index = self.page_index - 1
            else:
                index = self.page_index + 1

            if index >= 0 and index < len(self.chapter.pages):
                self.render_page(index)
            else:
                # TODO: next or prev chapter
                print('BEGIN or END')

    def on_resize(self, window):
        size = self.viewport.get_allocated_size()[0]

        if self.size and (size.width != self.size.width or size.height != self.size.height):
            self.size = size
            self.set_page_image_from_pixbuf()

    def render_page(self, index):
        def get_page_image_path():
            self.chapter.update()
            page_path = self.chapter.get_page(self.page_index)

            GLib.idle_add(show_page_image, page_path)

        def show_page_image(page_path):
            if page_path is None:
                # TODO: Display not found page
                return False

            self.pixbuf = Pixbuf.new_from_file(page_path)
            self.size = self.viewport.get_allocated_size()[0]
            self.set_page_image_from_pixbuf()

            self.clear()
            self.viewport.add(self.image)
            self.image.show()

            return False

        self.page_index = index
        self.chapter.update(dict(last_page_read_index=index))

        self.show_spinner()

        thread = threading.Thread(target=get_page_image_path)
        thread.daemon = True
        thread.start()

    def set_page_image_from_pixbuf(self):
        width = self.pixbuf.get_width()
        height = self.pixbuf.get_height()

        # Adjust image on width
        pixbuf = self.pixbuf.scale_simple(
            self.size.width,
            height / (width / self.size.width),
            InterpType.BILINEAR
        )
        self.image.set_from_pixbuf(pixbuf)

        # if width > self.size.width:
        #     vadj.set_value((width - self.size.width) / 2)
        # if height > self.size.height:
        #     hadj.set_value((height - self.size.height) / 2)

    def show_spinner(self):
        self.clear()
        self.viewport.add(self.builder.get_object('spinner_box'))
