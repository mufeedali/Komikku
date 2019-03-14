import threading

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf


class Reader():
    def __init__(self, builder):
        self.builder = builder

        self.viewport = self.builder.get_object('reader_page_viewport')
        self.scrolledwindow = self.viewport.get_parent()
        self.spinner_box = self.builder.get_object('spinner_box')
        self.image = Gtk.Image()

        self.scrolledwindow.connect('button-press-event', self.on_button_press)

    def show_spinner(self):
        self.clear()
        self.viewport.add(self.spinner_box)

    def clear(self):
        for child in self.viewport.get_children():
            self.viewport.remove(child)

    def init(self, manga, chapter_id):
        self.manga = manga
        self.chapter = self.manga.data['chapters'][chapter_id]
        self.page_index = None

        # TODO: open last view page
        self.render_page(0)

    def on_button_press(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            sw_width = self.scrolledwindow.get_allocated_width()

            if event.x > sw_width / 2:
                index = self.page_index + 1
            else:
                index = self.page_index - 1

            if index >= 0 and index < len(self.chapter['pages']):
                print(index)
                self.render_page(index)
            else:
                # TODO: next or prev chapter
                print('BEGIN or END')

    def render_page(self, index):
        def get_page_image_path():
            print(self.chapter['id'])
            self.manga.update_chapter_data(self.chapter['id'])
            page_path = self.manga.get_chapter_page(self.chapter['id'], self.page_index)
            GLib.idle_add(set_page_image, page_path)

        def set_page_image(page_path):
            if page_path is None:
                # TODO: Display not found page
                return False

            pixbuf = Pixbuf.new_from_file(page_path)

            sw_width = self.scrolledwindow.get_allocated_width()

            sw_height = self.scrolledwindow.get_allocated_height()
            height = pixbuf.get_height()

            pixbuf = pixbuf.scale_simple(
                sw_width,
                height / (height / sw_height),
                InterpType.BILINEAR
            )
            self.image.set_from_pixbuf(pixbuf)

            self.clear()
            self.viewport.add(self.image)
            self.image.show()

            # if width > sw_width:
            #     vadj.set_value((width - sw_width) / 2)
            # if height > sw_height:
            #     hadj.set_value((height - sw_height) / 2)

            return False

        self.page_index = index

        self.show_spinner()

        thread = threading.Thread(target=get_page_image_path)
        thread.daemon = True
        thread.start()
