import datetime
import threading

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf

import mangascan.config_manager
from mangascan.model import create_db_connection
from mangascan.model import Chapter


class Controls():
    visible = False
    reader = None

    def __init__(self, reader):
        self.reader = reader

        self.box = Gtk.VBox()
        self.box.get_style_context().add_class('reader-controls-box')
        self.box.set_valign(Gtk.Align.END)

        # Chapter's title
        self.label = Gtk.Label()
        self.label.get_style_context().add_class('reader-controls-title-label')
        self.label.set_halign(Gtk.Align.START)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.box.pack_start(self.label, True, True, 4)

        # Chapter's pages slider: current / nb
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 2, 1)
        self.scale.get_style_context().add_class('reader-controls-pages-scale')
        self.scale.set_value_pos(Gtk.PositionType.RIGHT)

        def format(scale, value):
            return '{0}/{1}'.format(int(value), len(self.reader.chapter.pages))

        self.scale.connect('format-value', format)
        self.scale.connect('value-changed', self.on_scale_value_changed)
        self.box.pack_start(self.scale, True, True, 0)

        self.reader.overlay.add_overlay(self.box)

    def goto_page(self, index):
        if self.scale.get_value() == index:
            self.scale.emit('value-changed')
        else:
            self.scale.set_value(index)

    def hide(self):
        self.visible = False
        self.box.hide()

    def init(self):
        self.scale.set_range(1, len(self.reader.chapter.pages))
        self.label.set_text(self.reader.chapter.title)

    def on_scale_value_changed(self, scale):
        self.reader.render_page(int(scale.get_value()) - 1)

    def set_scale_direction(self, inverted):
        self.scale.set_inverted(inverted)

    def show(self):
        self.visible = True
        self.box.show()


class Reader():
    chapter = None
    pixbuf = None
    size = None

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/com/gitlab/valos/MangaScan/menu_reader.xml')

        self.viewport = self.builder.get_object('reader_page_viewport')
        self.scrolledwindow = self.viewport.get_parent()
        self.overlay = self.scrolledwindow.get_parent()

        self.image = Gtk.Image()
        self.viewport.add(self.image)

        # Spinner
        self.spinner_box = self.builder.get_object('spinner_box')
        self.overlay.add_overlay(self.spinner_box)

        # Controls
        self.controls = Controls(self)

        self.window.connect('check-resize', self.on_resize)
        self.scrolledwindow.connect('button-press-event', self.on_button_press)

    @property
    def reading_direction(self):
        return self.chapter.manga.reading_direction or mangascan.config_manager.get_reading_direction()

    def add_actions(self):
        self.reading_direction_action = Gio.SimpleAction.new_stateful(
            'reader.reading-direction', GLib.VariantType.new('s'), GLib.Variant('s', 'right-to-left'))
        self.reading_direction_action.connect('change-state', self.on_reading_direction_changed)

        self.window.application.add_action(self.reading_direction_action)

    def hide_spinner(self):
        self.spinner_box.hide()
        self.spinner_box.get_children()[0].stop()

    def init(self, chapter, index=None):
        def run():
            self.chapter.update()

            GLib.idle_add(complete, index)

        def complete(index):
            self.chapter.manga.update(dict(last_read=datetime.datetime.now()))

            if index is None:
                index = self.chapter.last_page_read_index or 0
            elif index == 'first':
                index = 0
            elif index == 'last':
                index = len(self.chapter.pages) - 1

            self.hide_spinner()
            self.controls.init()
            self.controls.goto_page(index + 1)

        if index is None:
            # We come from library
            self.image.clear()
            self.controls.hide()
            self.show()

        self.chapter = chapter

        self.show_spinner()
        self.set_reading_direction()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_button_press(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if event.x < self.size.width / 3:
                # 1st third of the page
                index = self.page_index + 1 if self.reading_direction == 'right-to-left' else self.page_index - 1
            elif event.x > 2 * self.size.width / 3:
                # Last third of the page
                index = self.page_index - 1 if self.reading_direction == 'right-to-left' else self.page_index + 1
            else:
                # Center part of the page
                if self.controls.visible:
                    self.controls.hide()
                else:
                    self.controls.show()
                return

            if index >= 0 and index < len(self.chapter.pages):
                self.controls.goto_page(index + 1)
            elif index == -1:
                # Get previous chapter
                db_conn = create_db_connection()
                row = db_conn.execute(
                    'SELECT id FROM chapters WHERE manga_id = ? AND rank = ?', (self.chapter.manga_id, self.chapter.rank - 1)).fetchone()
                db_conn.close()

                if row:
                    self.init(Chapter(row['id']), 'last')
            elif index == len(self.chapter.pages):
                # Get next chapter
                db_conn = create_db_connection()
                row = db_conn.execute(
                    'SELECT id FROM chapters WHERE manga_id = ? AND rank = ?', (self.chapter.manga_id, self.chapter.rank + 1)).fetchone()
                db_conn.close()

                if row:
                    self.init(Chapter(row['id']), 'first')

    def on_reading_direction_changed(self, action, variant):
        value = variant.get_string()
        if value == self.chapter.manga.reading_direction:
            return

        self.chapter.manga.update(dict(reading_direction=value))
        self.set_reading_direction()

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
            if page_path:
                self.pixbuf = Pixbuf.new_from_file(page_path)
            else:
                self.pixbuf = Pixbuf.new_from_resource_at_scale('/com/gitlab/valos/MangaScan/images/missing_file.png', 180, -1, True)

            self.size = self.viewport.get_allocated_size()[0]
            self.set_page_image_from_pixbuf()

            self.image.show()

            self.hide_spinner()

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

    def set_reading_direction(self):
        self.reading_direction_action.set_state(GLib.Variant('s', self.reading_direction))
        self.controls.set_scale_direction(self.reading_direction == 'right-to-left')

    def show_spinner(self):
        self.spinner_box.get_children()[0].start()
        self.spinner_box.show()

    def show(self):
        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu-reader'))
        self.builder.get_object('menubutton_image').set_from_icon_name('view-more-symbolic', Gtk.IconSize.MENU)

        self.window.show_page('reader')
