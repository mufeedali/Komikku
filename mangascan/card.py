from gettext import gettext as _
import threading
import time

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository.GdkPixbuf import Pixbuf

from mangascan.model import create_db_connection


class Card():
    manga = None

    def __init__(self, window):
        self.window = window
        self.builder = window.builder

    def delete_chapter(self, delete_button, box, chapter):
        chapter.purge()

        self.populate_chapter(box, chapter)

    def download_chapter(self, download_button, box, chapter):
        def run():
            chapter.update()

            for index, page in enumerate(chapter.pages):
                time.sleep(1)
                chapter.get_page(index)
                GLib.idle_add(update_notification, index)

            GLib.idle_add(complete)

        def update_notification(index):
            notification.update(
                _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title),
                _('Download page {0} / {1}').format(index + 1, len(chapter.pages))
            )
            notification.show()

            return False

        def complete():
            notification.update(
                _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title),
                _('Download completed')
            )
            notification.show()

            chapter.update(dict(downloaded=1))

            self.populate_chapter(box, chapter)

            return False

        # Set download button not sensitive
        box.get_children()[-1].set_sensitive(False)

        # Create notification
        notification = Notify.Notification.new(_('Download chapter'))
        notification.set_timeout(Notify.EXPIRES_DEFAULT)
        notification.show()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_chapter_clicked(self, listbox, row):
        self.window.reader.init(row.chapter_id)

        # TODO: save scrolledwindow vadjustment
        self.window.show_page('reader')

    def on_delete_menu_clicked(self, action, param):
        db_conn = create_db_connection()
        nb_mangas = db_conn.execute('SELECT count(*) FROM mangas').fetchone()[0]
        db_conn.close()

        if nb_mangas == 1:
            self.manga.delete()

            # Library is now empty
            self.window.library.populate()
        else:
            self.window.library.on_manga_deleted(self.manga)
            self.manga.delete()

        self.window.show_page('library')

    def on_update_menu_clicked(self, action, param):
        def run():
            self.manga.update()
            GLib.idle_add(complete)

        def complete():
            self.populate()

            notification = Notify.Notification.new(_('[{0}] Successfully updated').format(self.manga.name))
            notification.show()

            return False

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def open_manga(self, manga):
        self.populate(manga)
        self.show()

    def populate(self, manga=None):
        if manga:
            if manga != self.manga:
                # Scroll scrolledwindow to top when manga is changed
                vadjustment = self.window.stack.get_child_by_name('card').get_vadjustment()
                vadjustment.set_value(0)

            self.manga = manga

        pixbuf = Pixbuf.new_from_file_at_scale(self.manga.cover_path, 180, -1, True)
        self.builder.get_object('cover_image').set_from_pixbuf(pixbuf)

        self.builder.get_object('author_value_label').set_text(self.manga.author or '-')
        self.builder.get_object('type_value_label').set_text(self.manga.types or '-')
        self.builder.get_object('status_value_label').set_text(
            _(self.manga.STATUSES[self.manga.status]) if self.manga.status else '-')
        self.builder.get_object('server_value_label').set_text(
            '{0} ({1} chapters)'.format(self.manga.server.name, len(self.manga.chapters)))
        self.builder.get_object('last_update_value_label').set_text(
            self.manga.last_update.strftime('%m/%d/%Y') if self.manga.last_update else '-')

        self.builder.get_object('synopsis_value_label').set_text(self.manga.synopsis or '-')

        listbox = self.builder.get_object('chapters_listbox')
        listbox.connect("row-activated", self.on_chapter_clicked)

        for child in listbox.get_children():
            child.destroy()

        for chapter in self.manga.chapters:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class('listboxrow-chapter')
            row.chapter_id = chapter.id
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.add(box)

            self.populate_chapter(box, chapter)

            listbox.add(row)

        listbox.show_all()

    def populate_chapter(self, box, chapter):
        if box.get_parent() is None:
            return

        for child in box.get_children():
            child.destroy()

        # Title
        label = Gtk.Label(xalign=0)
        label.set_line_wrap(True)
        label.set_text(chapter.title)
        box.pack_start(label, True, True, 0)

        # Counter: nb read / nb pages
        label = Gtk.Label(xalign=0, yalign=1)
        label.get_style_context().add_class('listboxrow-chapter-counter')
        if chapter.pages is not None and chapter.last_page_read_index is not None:
            label.set_text('{0}/{1}'.format(chapter.last_page_read_index + 1, len(chapter.pages)))
        box.pack_start(label, False, True, 0)

        if chapter.last_page_read_index is not None or chapter.downloaded:
            # Delete button
            button = Gtk.Button.new_from_icon_name('user-trash-symbolic', Gtk.IconSize.BUTTON)
            button.connect('clicked', self.delete_chapter, box, chapter)
            button.set_relief(Gtk.ReliefStyle.NONE)
            box.pack_start(button, False, True, 0)
        else:
            # Download button
            button = Gtk.Button.new_from_icon_name('document-save-symbolic', Gtk.IconSize.BUTTON)
            button.connect('clicked', self.download_chapter, box, chapter)
            button.set_relief(Gtk.ReliefStyle.NONE)
            box.pack_start(button, False, True, 0)

        box.show_all()

    def show(self):
        self.window.headerbar.set_title(self.manga.name)
        self.builder.get_object('menubutton').set_popover(self.builder.get_object('card_page_menubutton_popover'))

        self.window.show_page('card')
