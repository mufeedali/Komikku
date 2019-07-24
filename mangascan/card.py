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


class Card():
    manga = None
    selection_mode = False

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/com/gitlab/valos/MangaScan/menu_card.xml')
        self.builder.add_from_resource('/com/gitlab/valos/MangaScan/menu_card_selection_mode.xml')

        self.stack = self.builder.get_object('card_stack')

        # Chapters listbox
        self.listbox = self.builder.get_object('chapters_listbox')
        self.listbox.connect('row-activated', self.on_chapter_clicked)
        self.gesture = Gtk.GestureLongPress.new(self.listbox)
        self.gesture.set_touch_only(False)
        self.gesture.connect('pressed', self.enter_selection_mode)

        def sort(child1, child2):
            """
            This function gets two children and has to return:
            - a negative integer if the firstone should come before the second one
            - zero if they are equal
            - a positive integer if the second one should come before the firstone
            """
            if child1.chapter.rank > child2.chapter.rank:
                return -1 if self.sort_order == 'desc' else 1
            elif child1.chapter.rank < child2.chapter.rank:
                return 1 if self.sort_order == 'desc' else -1
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

            row.chapter = chapter
            self.populate_chapter(row)

        self.downloader = Downloader(downloader_change_cb)
        self.downloader.start()

    @property
    def sort_order(self):
        return self.manga.sort_order or 'desc'

    def add_actions(self):
        # Menu actions
        delete_action = Gio.SimpleAction.new('card.delete', None)
        delete_action.connect('activate', self.on_delete_menu_clicked)
        self.window.application.add_action(delete_action)

        update_action = Gio.SimpleAction.new('card.update', None)
        update_action.connect('activate', self.on_update_menu_clicked)
        self.window.application.add_action(update_action)

        self.sort_order_action = Gio.SimpleAction.new_stateful('card.sort-order', GLib.VariantType.new('s'), GLib.Variant('s', 'desc'))
        self.sort_order_action.connect('change-state', self.on_sort_order_changed)
        self.window.application.add_action(self.sort_order_action)

        # Menu actions in selection mode
        download_selected_chapters_action = Gio.SimpleAction.new('card.download-selected-chapters', None)
        download_selected_chapters_action.connect('activate', self.download_selected_chapters)
        self.window.application.add_action(download_selected_chapters_action)

        mark_selected_chapters_as_read_action = Gio.SimpleAction.new('card.mark-selected-chapters-as-read', None)
        mark_selected_chapters_as_read_action.connect('activate', self.toggle_selected_chapters_read_status, 1)
        self.window.application.add_action(mark_selected_chapters_as_read_action)

        mark_selected_chapters_as_unread_action = Gio.SimpleAction.new('card.mark-selected-chapters-as-unread', None)
        mark_selected_chapters_as_unread_action.connect('activate', self.toggle_selected_chapters_read_status, 0)
        self.window.application.add_action(mark_selected_chapters_as_unread_action)

        reset_selected_chapters_action = Gio.SimpleAction.new('card.reset-selected-chapters', None)
        reset_selected_chapters_action.connect('activate', self.reset_selected_chapters)
        self.window.application.add_action(reset_selected_chapters_action)

        # Chapters menu actions
        download_chapter_action = Gio.SimpleAction.new('card.download-chapter', None)
        download_chapter_action.connect('activate', self.download_chapter)
        self.window.application.add_action(download_chapter_action)

        mark_chapter_as_read_action = Gio.SimpleAction.new('card.mark-chapter-as-read', None)
        mark_chapter_as_read_action.connect('activate', self.toggle_chapter_read_status, 1)
        self.window.application.add_action(mark_chapter_as_read_action)

        mark_chapter_as_unread_action = Gio.SimpleAction.new('card.mark-chapter-as-unread', None)
        mark_chapter_as_unread_action.connect('activate', self.toggle_chapter_read_status, 0)
        self.window.application.add_action(mark_chapter_as_unread_action)

        reset_chapter_action = Gio.SimpleAction.new('card.reset-chapter', None)
        reset_chapter_action.connect('activate', self.reset_chapter)
        self.window.application.add_action(reset_chapter_action)

    def download_chapter(self, action, param):
        if not self.window.application.connected:
            self.window.show_notification(_('No Internet connection'))
            return

        # Add chapter in download queue
        self.downloader.add(self.action_row.chapter.id)
        self.downloader.add(self.action_row.chapter.id)

        # Update chapter
        self.populate_chapter(self.action_row)

        self.downloader.start()

    def download_selected_chapters(self, action, param):
        if not self.window.application.connected:
            self.window.show_notification(_('No Internet connection'))
            return

        for row in self.listbox.get_selected_rows():
            # Add chapter in download queue
            self.downloader.add(row.chapter.id)

            # Update chapter
            self.populate_chapter(row)

        self.downloader.start()

        self.leave_selection_mode()

    def enter_selection_mode(self, gesture, x, y):
        self.selection_mode = True

        self.listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        self.window.titlebar.set_selection_mode(True)

        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu-card-selection-mode'))

    def init(self, manga=None, transition=True):
        if manga and (self.manga is None or manga.id != self.manga.id):
            # Default page is Chapters page
            self.stack.set_visible_child_name('page_card_chapters')

            for child in self.builder.get_object('card_stack').get_children():
                # Scroll scrolledwindows (of info and chapters pages) to top when manga is changed
                child.get_vadjustment().set_value(0)

        # Create a fresh instance of manga
        if manga:
            self.manga = Manga(manga.id)
        else:
            self.manga = Manga(self.manga.id)

        self.populate()
        self.show(transition)

    def leave_selection_mode(self):
        self.selection_mode = False

        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for row in self.listbox.get_children():
            row._selected = False

        self.window.titlebar.set_selection_mode(False)

        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu-card'))

    def on_chapter_clicked(self, listbox, row):
        if self.selection_mode:
            if row._selected:
                self.listbox.unselect_row(row)
                row._selected = False
            else:
                row._selected = True
        else:
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

        self.window.library.show()

    def on_sort_order_changed(self, action, variant):
        value = variant.get_string()
        if value == self.manga.sort_order:
            return

        self.manga.update(dict(sort_order=value))
        self.set_sort_order()

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

        if not self.window.application.connected:
            self.window.show_notification(_('No Internet connection'))
            return

        thread = threading.Thread(target=run, args=(self.manga,))
        thread.daemon = True
        thread.start()

    def populate(self):
        # Chapters
        for child in self.listbox.get_children():
            child.destroy()

        for chapter in self.manga.chapters:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class('card-chapter-listboxrow')
            row.chapter = chapter
            row._selected = False

            self.populate_chapter(row)

            self.listbox.add(row)

        self.set_sort_order(invalidate=False)
        self.listbox.show_all()

        # Info
        if self.manga.cover_fs_path is not None:
            pixbuf = Pixbuf.new_from_file_at_scale(self.manga.cover_fs_path, 174, -1, True)
        else:
            pixbuf = Pixbuf.new_from_resource_at_scale('/com/gitlab/valos/MangaScan/images/missing_file.png', 174, -1, True)
        self.builder.get_object('cover_image').set_from_pixbuf(pixbuf)

        self.builder.get_object('author_value_label').set_text(self.manga.author or '-')
        self.builder.get_object('genres_value_label').set_text(', '.join(self.manga.genres) if self.manga.genres else '-')
        self.builder.get_object('status_value_label').set_text(
            _(self.manga.STATUSES[self.manga.status]) if self.manga.status else '-')
        self.builder.get_object('server_value_label').set_markup(
            '<a href="{0}">{1}</a> ({2} chapters)'.format(
                self.manga.server.manga_url.format(self.manga.slug),
                self.manga.server.name,
                len(self.manga.chapters)
            )
        )
        self.builder.get_object('last_update_value_label').set_text(
            self.manga.last_update.strftime('%m/%d/%Y') if self.manga.last_update else '-')

        self.builder.get_object('synopsis_value_label').set_text(self.manga.synopsis or '-')

    def populate_chapter(self, row):
        for child in row.get_children():
            child.destroy()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.add(box)

        chapter = row.chapter

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        # Title
        label = Gtk.Label(xalign=0)
        ctx = label.get_style_context()
        ctx.add_class('card-chapter-label')
        if chapter.read:
            # Chapter reading ended
            ctx.add_class('card-chapter-label-ended')
        elif chapter.last_page_read_index is not None:
            # Chapter reading started
            ctx.add_class('card-chapter-label-started')
        label.set_line_wrap(True)
        label.set_text(chapter.title)
        hbox.pack_start(label, True, True, 0)

        # Action button
        button = Gtk.Button.new_from_icon_name('view-more-symbolic', Gtk.IconSize.BUTTON)
        button.connect('clicked', self.show_chapter_menu, row)
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
        else:
            active_download = Download.get_by_chapter_id(chapter.id)
            if active_download:
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

    def reset_chapter(self, action, param):
        chapter = self.action_row.chapter

        chapter.reset()

        self.populate_chapter(self.action_row)

    def reset_selected_chapters(self, action, param):
        for row in self.listbox.get_selected_rows():
            chapter = row.chapter

            chapter.reset()

            self.populate_chapter(row)

        self.leave_selection_mode()

    def set_sort_order(self, invalidate=True):
        self.sort_order_action.set_state(GLib.Variant('s', self.sort_order))
        if invalidate:
            self.listbox.invalidate_sort()

    def show(self, transition=True):
        if self.window.stack.props.visible_child_name == 'card':
            return

        self.window.headerbar.set_title(self.manga.name)

        self.builder.get_object('left_button_image').set_from_icon_name('go-previous-symbolic', Gtk.IconSize.MENU)

        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu-card'))
        self.builder.get_object('menubutton_image').set_from_icon_name('view-more-symbolic', Gtk.IconSize.MENU)

        self.window.show_page('card', transition=transition)

    def show_chapter_menu(self, button, row):
        chapter = row.chapter
        self.action_row = row

        popover = Gtk.Popover(border_width=4)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_relative_to(button)

        menu = Gio.Menu()
        if chapter.downloaded or chapter.last_page_read_index is not None:
            menu.append(_('Reset'), 'app.card.reset-chapter')
        if not chapter.downloaded:
            menu.append(_('Download'), 'app.card.download-chapter')
        if not chapter.read:
            menu.append(_('Mark as read'), 'app.card.mark-chapter-as-read')
        if chapter.read or chapter.last_page_read_index is not None:
            menu.append(_('Mark as unread'), 'app.card.mark-chapter-as-unread')

        popover.bind_model(menu, None)
        popover.popup()

    def toggle_selected_chapters_read_status(self, action, param, read):
        for row in self.listbox.get_selected_rows():
            chapter = row.chapter

            chapter.update(dict(
                read=read,
                last_page_read_index=len(chapter.pages) - 1 if read else None,
            ))

            self.populate_chapter(row)

        self.leave_selection_mode()

    def toggle_chapter_read_status(self, action, param, read):
        chapter = self.action_row.chapter

        chapter.update(dict(
            read=read,
            last_page_read_index=len(chapter.pages) - 1 if read else None,
        ))

        self.populate_chapter(self.action_row)
