from gettext import gettext as _
from pydoc import locate
import threading

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository import Pango

from mangascan.model import create_db_connection
from mangascan.model import Manga
from mangascan.servers import get_servers_list


class AddDialog():
    server = None
    page = None
    manga = None
    manga_data = None
    search_lock = False

    def __init__(self, window):
        self.window = window
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/info/febvre/MangaScan/ui/add_dialog.ui')

        self.dialog = self.builder.get_object('search_dialog')

        # Header bar
        self.builder.get_object('back_button').connect('clicked', self.on_back_button_clicked)
        self.custom_title_stack = self.builder.get_object('custom_title_stack')

        self.overlay = self.builder.get_object('overlay')
        self.stack = self.builder.get_object('stack')

        self.spinner_box = self.builder.get_object('spinner_box')
        self.overlay.add_overlay(self.spinner_box)
        self.hide_spinner()

        # Servers page
        listbox = self.builder.get_object('servers_page_listbox')
        listbox.connect('row-activated', self.on_server_clicked)

        for server in get_servers_list():
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class('add-dialog-server-listboxrow')
            row.server_data = server
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.add(box)

            # Server logo
            pixbuf = Pixbuf.new_from_resource_at_scale(
                '/info/febvre/MangaScan/icons/ui/favicons/{0}.ico'.format(server['id']), 16, 16, True)
            logo = Gtk.Image(xalign=0)
            logo.set_from_pixbuf(pixbuf)
            box.pack_start(logo, False, True, 0)

            # Server title
            label = Gtk.Label(xalign=0)
            label.set_text(server['name'])
            box.pack_start(label, True, True, 0)

            # Server flag (indicates the language)
            pixbuf = Pixbuf.new_from_resource_at_scale(
                '/info/febvre/MangaScan/icons/ui/flags/{0}.png'.format(server['lang']), 30, 16, True)
            flag = Gtk.Image(xalign=1)
            flag.set_from_pixbuf(pixbuf)
            box.pack_start(flag, False, True, 0)

            listbox.add(row)

        listbox.show_all()

        # Search page
        self.custom_title_search_page_searchentry = self.builder.get_object('custom_title_search_page_searchentry')
        self.custom_title_search_page_searchentry.connect('activate', self.on_search_entry_activated)

        self.search_page_listbox = self.builder.get_object('search_page_listbox')
        self.search_page_listbox.connect('row-activated', self.on_manga_clicked)

        # Manga page
        self.custom_title_manga_page_label = self.builder.get_object('custom_title_manga_page_label')
        self.add_button = self.builder.get_object('add_button')
        self.add_button.connect('clicked', self.on_add_button_clicked)
        self.read_button = self.builder.get_object('read_button')
        self.read_button.connect('clicked', self.on_read_button_clicked)

        self.show_page('servers')

    def clear_search(self):
        self.custom_title_search_page_searchentry.set_text('')
        self.clear_results()

    def clear_results(self):
        for child in self.search_page_listbox.get_children():
            self.search_page_listbox.remove(child)

    def hide_notification(self):
        self.builder.get_object('notification_revealer').set_reveal_child(False)

    def hide_spinner(self):
        self.spinner_box.hide()
        self.spinner_box.get_children()[0].stop()

    def on_add_button_clicked(self, button):
        def run():
            manga = Manga.new(self.manga_data, self.server)
            GLib.idle_add(complete, manga)

        def complete(manga):
            self.manga = manga

            notification = Notify.Notification.new(_('{0} manga added').format(self.manga.name))
            notification.set_timeout(Notify.EXPIRES_NEVER)
            notification.show()

            self.window.library.on_manga_added(self.manga)

            self.add_button.set_sensitive(True)
            self.add_button.hide()
            self.read_button.show()
            self.hide_spinner()

            return False

        self.show_spinner()
        self.add_button.set_sensitive(False)

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_back_button_clicked(self, button):
        if self.page == 'servers':
            self.dialog.close()
        elif self.page == 'search':
            self.show_page('servers')
        elif self.page == 'manga':
            self.show_page('search')

    def on_manga_clicked(self, listbox, row):
        def run():
            manga_data = self.server.get_manga_data(row.manga_data)
            if manga_data is not None:
                GLib.idle_add(complete, manga_data)
            else:
                GLib.idle_add(error)

        def complete(manga_data):
            self.manga_data = manga_data

            # Populate manga card
            cover_data = self.server.get_manga_cover_image(self.manga_data.get('cover'))
            if cover_data is not None:
                cover_stream = Gio.MemoryInputStream.new_from_data(cover_data, None)
                pixbuf = Pixbuf.new_from_stream_at_scale(cover_stream, 174, -1, True, None)
            else:
                pixbuf = Pixbuf.new_from_resource_at_scale('/info/febvre/MangaScan/images/missing_file.png', 174, -1, True)

            self.builder.get_object('cover_image').set_from_pixbuf(pixbuf)

            self.builder.get_object('author_value_label').set_markup(
                '<span size="small">{0}</span>'.format(', '.join(self.manga_data['authors']) if self.manga_data['authors'] else '-'))
            self.builder.get_object('genres_value_label').set_markup(
                '<span size="small">{0}</span>'.format(', '.join(self.manga_data['genres']) if self.manga_data['genres'] else '-'))
            self.builder.get_object('status_value_label').set_markup(
                '<span size="small">{0}</span>'.format(_(Manga.STATUSES[self.manga_data['status']])) if self.manga_data['status'] else '-')
            self.builder.get_object('server_value_label').set_markup(
                '<span size="small"><a href="{0}">{1}</a> ({2} chapters)</span>'.format(
                    self.server.get_manga_url(self.manga_data['slug'], self.manga_data.get('url')),
                    self.server.name,
                    len(self.manga_data['chapters'])
                )
            )

            self.builder.get_object('synopsis_value_label').set_text(self.manga_data['synopsis'] or '-')

            self.hide_spinner()
            self.show_page('manga')

            return False

        def error():
            self.hide_spinner()
            self.show_notification("Oops, failed to retrieve manga's information.")

            return False

        self.show_spinner()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_read_button_clicked(self, button):
        self.window.card.init(self.manga, transition=False)
        self.dialog.close()

    def on_search_entry_activated(self, entry):
        term = entry.get_text().strip()
        if not term or self.search_lock:
            return

        def run():
            result = self.server.search(term)
            if result:
                GLib.idle_add(complete, result)
            else:
                GLib.idle_add(error, result)

        def complete(result):
            self.hide_spinner()

            for item in result:
                row = Gtk.ListBoxRow()
                row.manga_data = item
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                row.add(box)
                label = Gtk.Label(xalign=0, margin=6)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                label.set_text(item['name'])
                box.pack_start(label, True, True, 0)

                self.search_page_listbox.add(row)

            self.search_page_listbox.show_all()

            self.search_lock = False

            return False

        def error(result):
            self.hide_spinner()
            self.search_lock = False

            if result is None:
                self.show_notification(_('Oops, search failed. Please try again.'))
            elif len(result) == 0:
                self.show_notification(_('No results'))

        self.search_lock = True
        self.clear_results()
        self.show_spinner()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_server_clicked(self, listbox, row):
        self.server = locate('mangascan.servers.{0}.{1}'.format(row.server_data['id'], row.server_data['class']))()
        self.show_page('search')

    def open(self, action, param):
        self.dialog.set_modal(True)
        self.dialog.set_transient_for(self.window)
        self.dialog.present()

    def show_notification(self, message):
        self.builder.get_object('notification_label').set_text(message)
        self.builder.get_object('notification_revealer').set_reveal_child(True)

        revealer_timer = threading.Timer(3.0, GLib.idle_add, args=[self.hide_notification])
        revealer_timer.start()

    def show_page(self, name):
        if name == 'search':
            if self.page == 'servers':
                self.custom_title_search_page_searchentry.set_placeholder_text(_('Search in {0}...').format(self.server.name))
                self.clear_search()
            else:
                self.custom_title_search_page_searchentry.grab_focus_without_selecting()
        elif name == 'manga':
            self.custom_title_manga_page_label.set_text(self.manga_data['name'])

            # Check if selected manga is already in library
            db_conn = create_db_connection()
            row = db_conn.execute(
                'SELECT * FROM mangas WHERE slug = ? AND server_id = ?',
                (self.manga_data['slug'], self.manga_data['server_id'])
            ).fetchone()
            db_conn.close()

            if row:
                self.manga = Manga(row['id'], self.server)

                self.read_button.show()
                self.add_button.hide()
            else:
                self.add_button.show()
                self.read_button.hide()

        self.custom_title_stack.set_visible_child_name(name)
        self.stack.set_visible_child_name(name)
        self.page = name

    def show_spinner(self):
        self.spinner_box.get_children()[0].start()
        self.spinner_box.show()
