import datetime
import threading

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf

from mangascan.model import create_db_connection
from mangascan.model import Chapter


class Reader():
    chapter = None
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

    def init(self, chapter_id, index=None):
        def run():
            self.chapter.update()

            GLib.idle_add(complete, index)

        def complete(index):
            db_conn = create_db_connection()

            # Get previous chapter Id
            row = db_conn.execute(
                'SELECT id FROM chapters WHERE manga_id = ? AND rank = ?', (self.chapter.manga_id, self.chapter.rank - 1)).fetchone()
            self.prev_chapter_id = row['id'] if row else None

            # Get next chapter Id
            row = db_conn.execute(
                'SELECT id FROM chapters WHERE manga_id = ? AND rank = ?', (self.chapter.manga_id, self.chapter.rank + 1)).fetchone()
            self.next_chapter_id = row['id'] if row else None

            db_conn.close()

            self.chapter.manga.update(dict(last_read=datetime.datetime.now()))

            if index is None:
                index = self.chapter.last_page_read_index or 0
            elif index == 'first':
                index = 0
            elif index == 'last':
                index = len(self.chapter.pages) - 1

            self.render_page(index)

        self.show_spinner()

        self.chapter = Chapter(chapter_id, backref=True)

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_button_press(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if event.x < self.size.width / 3:
                # 1st third of the page
                index = self.page_index + 1
            elif event.x > 2 * self.size.width / 3:
                # Last third of the page
                index = self.page_index - 1
            else:
                # Center: no action yet
                return

            if index >= 0 and index < len(self.chapter.pages):
                self.render_page(index)
            elif self.prev_chapter_id and index == -1:
                self.init(self.prev_chapter_id, 'last')
            elif self.next_chapter_id and index == len(self.chapter.pages):
                self.init(self.next_chapter_id, 'first')

    def on_resize(self, window):
        size = self.viewport.get_allocated_size()[0]

        if self.size and (size.width != self.size.width or size.height != self.size.height):
            self.size = size
            self.set_page_image_from_pixbuf()

    def render_page(self, index):
        def get_page_image_path():
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

        print('{0} {1}/{2}'.format(self.chapter.title, index + 1, len(self.chapter.pages) if self.chapter.pages else '?'))

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

    def show_spinner(self):
        self.clear()
        self.viewport.add(self.builder.get_object('spinner_box'))
