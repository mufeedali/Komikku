from gettext import gettext as _
import threading

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

from mangascan.downloader import Downloader
from mangascan.model import create_db_connection
from mangascan.model import Download
from mangascan.model import Manga
from mangascan.utils import network_is_available


class Card():
    manga = None

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/com/gitlab/valos/MangaScan/menu_card.xml')

        # Chapters listbox
        self.listbox = self.builder.get_object('chapters_listbox')
        self.listbox.connect("row-activated", self.on_chapter_clicked)

        def sort(child1, child2):
            """
            This function gets two children and has to return:
            - a negative integer if the firstone should come before the second one
            - zero if they are equal
            - a positive integer if the second one should come before the firstone
            """
            if child1.chapter.rank > child2.chapter.rank:
                return -1 if self.order == 'desc' else 1
            elif child1.chapter.rank < child2.chapter.rank:
                return 1 if self.order == 'desc' else -1
            else:
                return 0

        self.listbox.set_sort_func(sort)

        # Downloader change callback
        def downloader_change_cb(chapter):
            if self.window.stack.props.visible_child_name != 'card':
                return

            if self.manga is None or self.manga.id != chapter.manga_id:
                return

            row = None
            for child in self.listbox.get_children():
                if child.chapter.id == chapter.id:
                    row = child
                    break

            if row is None:
                return

            box = row.get_children()[0]
            self.populate_chapter(box, chapter)

        self.downloader = Downloader(downloader_change_cb)
        self.downloader.start()

    @property
    def order(self):
        return self.manga.order_ or 'desc'

    def add_actions(self):
        delete_action = Gio.SimpleAction.new("card.delete", None)
        delete_action.connect("activate", self.on_delete_menu_clicked)

        update_action = Gio.SimpleAction.new("card.update", None)
        update_action.connect("activate", self.on_update_menu_clicked)

        self.order_action = Gio.SimpleAction.new_stateful('card.order', GLib.VariantType.new('s'), GLib.Variant('s', 'desc'))
        self.order_action.connect('change-state', self.on_order_changed)

        self.window.application.add_action(delete_action)
        self.window.application.add_action(update_action)
        self.window.application.add_action(self.order_action)

    def delete_chapter(self, delete_button, box, chapter):
        chapter.purge()

        self.populate_chapter(box, chapter)

    def download_chapter(self, button, box, chapter):
        if not network_is_available():
            self.window.show_notification(_('No Internet connection'))
            return

        # Add chapter in download queue
        Download.new(chapter.id)

        # Update chapter
        self.populate_chapter(box, chapter)

        self.downloader.start()

    def init(self, manga=None, transition=True):
        if manga and self.manga and manga.id != self.manga.id:
            # Scroll scrolledwindow to top when manga is changed
            vadjustment = self.window.stack.get_child_by_name('card').get_vadjustment()
            vadjustment.set_value(0)

        # Create a fresh instance of manga
        if manga:
            self.manga = Manga(manga.id)
        else:
            self.manga = Manga(self.manga.id)

        self.show(transition)
        self.populate()

    def on_chapter_clicked(self, listbox, row):
        self.window.reader.init(row.chapter)

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

    def on_order_changed(self, action, variant):
        value = variant.get_string()
        if value == self.manga.order_:
            return

        self.manga.update(dict(order_=value))
        self.set_order()

    def on_update_menu_clicked(self, action, param):
        def run(manga):
            self.window.show_notification(_('Start update'))

            if manga.update():
                GLib.idle_add(complete, manga)
            else:
                GLib.idle_add(error)

        def complete(manga):
            # Update card only if manga has not changed
            if self.manga.id == manga.id:
                self.init(manga)

            self.window.show_notification(_('Successfully updated'))

            return False

        def error():
            self.window.show_notification(_('Oops, update failed, Please try again.'))
            return False

        if not network_is_available():
            self.window.show_notification(_('No Internet connection'))
            return

        thread = threading.Thread(target=run, args=(self.manga,))
        thread.daemon = True
        thread.start()

    def populate(self):
        if self.manga.cover_fs_path is not None:
            pixbuf = Pixbuf.new_from_file_at_scale(self.manga.cover_fs_path, 180, -1, True)
        else:
            pixbuf = Pixbuf.new_from_resource_at_scale("/com/gitlab/valos/MangaScan/images/missing_file.png", 180, -1, True)
        self.builder.get_object('cover_image').set_from_pixbuf(pixbuf)

        self.builder.get_object('author_value_label').set_text(self.manga.author or '-')
        self.builder.get_object('genres_value_label').set_text(', '.join(self.manga.genres) if self.manga.genres else '-')
        self.builder.get_object('status_value_label').set_text(
            _(self.manga.STATUSES[self.manga.status]) if self.manga.status else '-')
        self.builder.get_object('server_value_label').set_text(
            '{0} ({1} chapters)'.format(self.manga.server.name, len(self.manga.chapters)))
        self.builder.get_object('last_update_value_label').set_text(
            self.manga.last_update.strftime('%m/%d/%Y') if self.manga.last_update else '-')

        self.builder.get_object('synopsis_value_label').set_text(self.manga.synopsis or '-')

        for child in self.listbox.get_children():
            child.destroy()

        for chapter in self.manga.chapters:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class('card-chapter-listboxrow')
            row.chapter = chapter
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            row.add(box)

            self.populate_chapter(box, chapter)

            self.listbox.add(row)

        self.set_order()
        self.listbox.show_all()

    def populate_chapter(self, box, chapter):
        for child in box.get_children():
            child.destroy()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        # Title
        label = Gtk.Label(xalign=0)
        ctx = label.get_style_context()
        ctx.add_class('card-chapter-label')
        if chapter.last_page_read_index is not None:
            if chapter.last_page_read_index == len(chapter.pages) - 1:
                # Chapter reading ended
                ctx.add_class('card-chapter-label-ended')
            else:
                # Chapter reading started
                ctx.add_class('card-chapter-label-started')
        label.set_line_wrap(True)
        label.set_text(chapter.title)
        hbox.pack_start(label, True, True, 0)

        active_download = Download.get_by_chapter_id(chapter.id)

        # Download or Delete button
        if (chapter.last_page_read_index is not None or chapter.downloaded) and active_download is None:
            # Delete button
            button = Gtk.Button.new_from_icon_name('user-trash-symbolic', Gtk.IconSize.BUTTON)
            button.connect('clicked', self.delete_chapter, box, chapter)
        else:
            # Download button
            button = Gtk.Button.new_from_icon_name('document-save-symbolic', Gtk.IconSize.BUTTON)
            if active_download:
                button.set_sensitive(False)
            button.connect('clicked', self.download_chapter, box, chapter)
        button.set_relief(Gtk.ReliefStyle.NONE)
        hbox.pack_start(button, False, True, 0)

        box.pack_start(hbox, True, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Date + Downloaded state
        label = Gtk.Label(xalign=0, yalign=1)
        label.get_style_context().add_class('card-chapter-sublabel')
        text = chapter.date
        if chapter.downloaded:
            text = '{0} - {1}'.format(text, _('DOWNLOADED'))
        elif active_download:
            text = '{0} - {1}'.format(text, _(Download.STATUSES[active_download.status]))
        label.set_text(text)
        hbox.pack_start(label, True, True, 0)

        # Counter: nb read / nb pages
        label = Gtk.Label(xalign=0, yalign=1)
        label.get_style_context().add_class('card-chapter-sublabel')
        if chapter.pages is not None and chapter.last_page_read_index is not None:
            label.set_text('{0}/{1}'.format(chapter.last_page_read_index + 1, len(chapter.pages)))
        hbox.pack_start(label, False, True, 0)

        box.pack_start(hbox, True, True, 0)

        box.show_all()

    def set_order(self):
        self.order_action.set_state(GLib.Variant('s', self.order))
        self.listbox.invalidate_sort()

    def show(self, transition=True):
        if self.window.stack.props.visible_child_name == 'card':
            return

        self.window.headerbar.set_title(self.manga.name)

        self.builder.get_object('left_button_image').set_from_icon_name('go-previous-symbolic', Gtk.IconSize.MENU)

        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu-card'))
        self.builder.get_object('menubutton_image').set_from_icon_name('view-more-symbolic', Gtk.IconSize.MENU)

        self.window.show_page('card', transition=transition)
