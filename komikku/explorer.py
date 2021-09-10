# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading
import time

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GdkPixbuf import PixbufAnimation

from komikku.models import create_db_connection
from komikku.models import Manga
from komikku.models import Settings
from komikku.servers import get_allowed_servers_list
from komikku.servers import get_buffer_mime_type
from komikku.servers import LANGUAGES
from komikku.utils import create_cairo_surface_from_pixbuf
from komikku.utils import html_escape
from komikku.utils import log_error_traceback
from komikku.utils import scale_pixbuf_animation


@Gtk.Template.from_resource('/info/febvre/Komikku/ui/explorer.ui')
class Explorer(Gtk.Stack):
    __gtype_name__ = 'Explorer'

    page = None
    preselection = False
    search_filters = None
    search_lock = False
    servers_search_mode = False

    server = None
    manga = None
    manga_data = None
    manga_slug = None

    servers_page_searchbar = Gtk.Template.Child('servers_page_searchbar')
    servers_page_searchentry = Gtk.Template.Child('servers_page_searchentry')
    servers_page_listbox = Gtk.Template.Child('servers_page_listbox')
    servers_page_pinned_listbox = Gtk.Template.Child('servers_page_pinned_listbox')

    search_page_searchbar = Gtk.Template.Child('search_page_searchbar')
    search_page_searchentry = Gtk.Template.Child('search_page_searchentry')
    search_page_filter_menu_button = Gtk.Template.Child('search_page_filter_menu_button')
    search_page_listbox = Gtk.Template.Child('search_page_listbox')

    card_page_cover_box = Gtk.Template.Child('card_page_cover_box')
    card_page_cover_image = Gtk.Template.Child('card_page_cover_image')
    card_page_authors_value_label = Gtk.Template.Child('card_page_authors_value_label')
    card_page_name_value_label = Gtk.Template.Child('card_page_name_value_label')
    card_page_genres_value_label = Gtk.Template.Child('card_page_genres_value_label')
    card_page_status_value_label = Gtk.Template.Child('card_page_status_value_label')
    card_page_server_value_label = Gtk.Template.Child('card_page_server_value_label')
    card_page_chapters_value_label = Gtk.Template.Child('card_page_chapters_value_label')
    card_page_synopsis_value_label = Gtk.Template.Child('card_page_synopsis_value_label')
    card_page_scanlators_value_label = Gtk.Template.Child('card_page_scanlators_value_label')
    card_page_last_chapter_value_label = Gtk.Template.Child('card_page_last_chapter_value_label')

    def __init__(self, window):
        Gtk.Stack.__init__(self)

        self.window = window

        self.title_label = self.window.explorer_title_label

        # Servers page
        self.servers_page_search_button = self.window.explorer_servers_page_search_button
        self.servers_page_searchbar.connect_entry(self.servers_page_searchentry)
        self.servers_page_searchbar.bind_property(
            'search-mode-enabled', self.servers_page_search_button, 'active', GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE
        )
        self.servers_page_searchentry.connect('activate', self.on_servers_page_searchentry_activated)
        self.servers_page_searchentry.connect('changed', self.search_servers)

        self.servers_page_search_button.connect('clicked', self.toggle_servers_search)

        self.servers_page_pinned_listbox.connect('row-activated', self.on_server_clicked)

        def _servers_filter(row):
            """
            This function gets one row and has to return:
            - True if the row should be displayed
            - False if the row should not be displayed
            """
            term = self.servers_page_searchentry.get_text().strip().lower()

            if not hasattr(row, 'server_data'):
                # Languages headers are always visible
                return True

            server_name = row.server_data['name']
            server_lang = row.server_data['lang']

            # Search in name and language
            return (
                term in server_name.lower() or
                term in LANGUAGES[server_lang].lower() or
                term in server_lang.lower()
            )

        self.servers_page_listbox.connect('row-activated', self.on_server_clicked)
        self.servers_page_listbox.set_filter_func(_servers_filter)

        # Search page
        self.search_page_server_website_button = self.window.explorer_search_page_server_website_button
        self.search_page_server_website_button.connect('clicked', self.on_search_page_server_website_button_clicked)
        self.search_page_searchbar.connect_entry(self.search_page_searchentry)
        self.search_page_searchentry.connect('activate', self.search)

        self.search_page_listbox.connect('row-activated', self.on_manga_clicked)

        # Card page
        self.card_page_add_read_button = self.window.explorer_card_page_add_read_button
        self.card_page_add_read_button.connect('clicked', self.on_card_page_add_read_button_clicked)

        self.window.connect('key-press-event', self.on_key_press)

        self.window.stack.add_named(self, 'explorer')

    def build_server_row(self, data):
        row = Gtk.ListBoxRow()

        row.server_data = data
        if 'manga_initial_data' in data:
            row.manga_data = data.pop('manga_initial_data')

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add(box)

        # Server logo
        logo = Gtk.Image()
        if data['logo_path']:
            pixbuf = Pixbuf.new_from_file_at_scale(
                data['logo_path'], 24 * self.window.hidpi_scale, 24 * self.window.hidpi_scale, True)
            logo.set_from_surface(create_cairo_surface_from_pixbuf(pixbuf, self.window.hidpi_scale))
        else:
            logo.set_size_request(24, 24)
        box.pack_start(logo, False, True, 0)

        # Server title & language
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, homogeneous=True)

        label = Gtk.Label(xalign=0)
        title = data['name']
        if data['is_nsfw']:
            title += ' (NSFW)'
        label.set_text(title)
        vbox.pack_start(label, True, True, 0)

        label = Gtk.Label(xalign=0)
        label.set_text(LANGUAGES[data['lang']])
        label.get_style_context().add_class('subtitle')
        vbox.pack_start(label, False, True, 0)

        box.pack_start(vbox, True, True, 0)

        # Server requires a user account
        if data['has_login']:
            label = Gtk.Image.new_from_icon_name('dialog-password-symbolic', Gtk.IconSize.BUTTON)
            box.pack_start(label, False, True, 0)

        # Button to pin/unpin
        button = Gtk.ToggleButton()
        button.set_image(Gtk.Image.new_from_icon_name('view-pin-symbolic', Gtk.IconSize.BUTTON))
        button.set_valign(Gtk.Align.CENTER)
        button.set_active(data['id'] in Settings.get_default().pinned_servers)
        button.connect('toggled', self.toggle_server_pinned_state, row)
        box.pack_start(button, False, True, 0)

        return row

    def clear_search_page_results(self):
        for child in self.search_page_listbox.get_children():
            self.search_page_listbox.remove(child)

    def clear_search_page_search(self):
        self.search_page_searchentry.set_text('')
        self.clear_search_page_results()
        self.init_search_page_filters()

    def init_search_page_filters(self):
        self.search_filters = {}

        if getattr(self.server, 'filters', None) is None:
            return

        def build_checkbox(filter):
            self.search_filters[filter['key']] = filter['default']

            def toggle(button, _param):
                self.search_filters[filter['key']] = button.get_active()

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, visible=True)

            check_button = Gtk.CheckButton(label=filter['name'], active=filter['default'], tooltip_text=filter['description'], visible=True)
            check_button.connect('notify::active', toggle)
            vbox.add(check_button)

            return vbox

        def build_entry(filter):
            self.search_filters[filter['key']] = filter['default']

            def on_text_changed(buf, _param):
                self.search_filters[filter['key']] = buf.get_text()

            entry = Gtk.Entry(text=filter['default'], placeholder_text=filter['name'], tooltip_text=filter['description'], visible=True)
            entry.get_buffer().connect('notify::text', on_text_changed)

            return entry

        def build_select_single(filter):
            self.search_filters[filter['key']] = filter['default']

            def toggle_option(button, _param, key):
                if button.get_active():
                    self.search_filters[filter['key']] = key

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, visible=True)

            last = None
            for option in filter['options']:
                is_active = option['key'] == filter['default']
                radio_button = Gtk.RadioButton(label=option['name'], visible=True)
                radio_button.join_group(last)
                radio_button.set_active(is_active)
                radio_button.connect('notify::active', toggle_option, option['key'])
                vbox.add(radio_button)
                last = radio_button

            return vbox

        def build_select_multiple(filter):
            self.search_filters[filter['key']] = [option['key'] for option in filter['options'] if option['default']]

            def toggle_option(button, _param, key):
                if button.get_active():
                    self.search_filters[filter['key']].append(key)
                else:
                    self.search_filters[filter['key']].remove(key)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, visible=True)

            for option in filter['options']:
                check_button = Gtk.CheckButton(label=option['name'], active=option['default'], visible=True)
                check_button.connect('notify::active', toggle_option, option['key'])
                vbox.add(check_button)

            return vbox

        popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=6, spacing=12, visible=True)

        last = None
        for filter in self.server.filters:
            if filter['type'] == 'checkbox':
                filter_widget = build_checkbox(filter)
            elif filter['type'] == 'entry':
                filter_widget = build_entry(filter)
            elif filter['type'] == 'select':
                if filter['value_type'] == 'single':
                    filter_widget = build_select_single(filter)
                elif filter['value_type'] == 'multiple':
                    filter_widget = build_select_multiple(filter)
                else:
                    raise NotImplementedError('Invalid select value_type')

                label = Gtk.Label(label=filter['name'], tooltip_text=filter['description'], visible=True, sensitive=False)
                if last:
                    sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, visible=True)
                    vbox.add(sep)
                vbox.add(label)
            else:
                raise NotImplementedError('Invalid filter type')

            vbox.add(filter_widget)
            last = filter_widget

        popover.add(vbox)

        self.search_page_filter_menu_button.set_popover(popover)

    def navigate_back(self, source):
        if self.page == 'servers':
            # Back to Library if:
            # - user click on 'Back' button
            # - or use 'Esc' key and 'severs' page in not in search mode
            if source == 'click' or not self.servers_page_searchbar.get_search_mode():
                self.window.library.show()

            # Leave search mode
            if self.servers_page_searchbar.get_search_mode():
                self.servers_page_searchbar.set_search_mode(False)
        elif self.page == 'search':
            self.search_lock = False
            self.server = None

            # Stop activity indicator in case of search page is left before the end of a search
            self.window.activity_indicator.stop()

            # Restore focus to search entry if in search mode
            if self.servers_page_searchbar.get_search_mode():
                self.servers_page_searchentry.grab_focus_without_selecting()

            self.show_page('servers')
        elif self.page == 'card':
            self.manga_slug = None

            # Restore focus to search entry
            self.search_page_searchentry.grab_focus_without_selecting()

            if self.preselection:
                self.show_page('servers')
            else:
                self.show_page('search')

    def on_card_page_add_button_clicked(self):
        def run():
            manga = Manga.new(self.manga_data, self.server, Settings.get_default().long_strip_detection)
            GLib.idle_add(complete, manga)

        def complete(manga):
            self.manga = manga

            self.window.show_notification(_('{0} manga added').format(self.manga.name))

            self.window.library.on_manga_added(self.manga)

            self.card_page_add_read_button.set_sensitive(True)
            self.card_page_add_read_button.get_children()[0].set_from_icon_name('media-playback-start-symbolic', Gtk.IconSize.BUTTON)
            self.window.activity_indicator.stop()

            return False

        self.window.activity_indicator.start()
        self.card_page_add_read_button.set_sensitive(False)

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_card_page_add_read_button_clicked(self, _button):
        if self.manga:
            self.on_card_page_read_button_clicked()
        else:
            self.on_card_page_add_button_clicked()

    def on_card_page_read_button_clicked(self):
        self.window.card.init(self.manga, transition=False)

    def on_key_press(self, _widget, event):
        """Search entry of servers/search pages can be focused by simply typing a printable character"""

        if self.window.page != 'explorer':
            return Gdk.EVENT_PROPAGATE

        if self.page == 'servers':
            return self.servers_page_searchbar.handle_event(event)
        elif self.page == 'search':
            return self.search_page_searchbar.handle_event(event)

        return Gdk.EVENT_PROPAGATE

    def on_manga_clicked(self, listbox, row):
        self.populate_card(row.manga_data)

    def on_resize(self):
        self.card_page_cover_box.set_orientation(Gtk.Orientation.VERTICAL if self.window.mobile_width else Gtk.Orientation.HORIZONTAL)

    def on_search_page_server_website_button_clicked(self, _button):
        if self.server.base_url:
            Gtk.show_uri_on_window(None, self.server.base_url, time.time())
        else:
            self.window.show_notification(_('Oops, server website URL is unknown.'), 2)

    def on_server_clicked(self, listbox, row):
        self.server = getattr(row.server_data['module'], row.server_data['class_name'])()
        if hasattr(row, 'manga_data'):
            self.populate_card(row.manga_data)
        else:
            self.show_page('search')

    def on_servers_page_searchentry_activated(self, _entry):
        if not self.servers_page_searchbar.get_search_mode():
            return

        row = self.servers_page_listbox.get_row_at_y(0)
        if row:
            self.on_server_clicked(self.servers_page_listbox, row)

    def populate_card(self, manga_data):
        def run(server, manga_slug):
            try:
                current_manga_data = server.get_manga_data(manga_data)

                if current_manga_data is not None:
                    GLib.idle_add(complete, current_manga_data, server)
                else:
                    GLib.idle_add(error, server, manga_slug)
            except Exception as e:
                user_error_message = log_error_traceback(e)
                GLib.idle_add(error, server, manga_slug, user_error_message)

        def complete(manga_data, server):
            if server != self.server or manga_data['slug'] != self.manga_slug:
                return False

            self.manga_data = manga_data

            # Populate manga card
            try:
                cover_data = self.server.get_manga_cover_image(self.manga_data.get('cover'))
            except Exception as e:
                cover_data = None
                user_error_message = log_error_traceback(e)
                if user_error_message:
                    self.window.show_notification(user_error_message)

            if cover_data is None:
                pixbuf = Pixbuf.new_from_resource_at_scale(
                    '/info/febvre/Komikku/images/missing_file.png', 174 * self.window.hidpi_scale, -1, True)
            else:
                cover_stream = Gio.MemoryInputStream.new_from_data(cover_data, None)
                if get_buffer_mime_type(cover_data) != 'image/gif':
                    pixbuf = Pixbuf.new_from_stream_at_scale(cover_stream, 174 * self.window.hidpi_scale, -1, True, None)
                else:
                    pixbuf = scale_pixbuf_animation(PixbufAnimation.new_from_stream(cover_stream), 174, -1, True, True)

            self.card_page_cover_image.clear()
            if isinstance(pixbuf, PixbufAnimation):
                self.card_page_cover_image.set_from_animation(pixbuf)
            else:
                self.card_page_cover_image.set_from_surface(create_cairo_surface_from_pixbuf(pixbuf, self.window.hidpi_scale))

            self.card_page_name_value_label.set_label(manga_data['name'])

            authors = html_escape(', '.join(self.manga_data['authors'])) if self.manga_data['authors'] else '-'
            self.card_page_authors_value_label.set_markup(authors)

            genres = html_escape(', '.join(self.manga_data['genres'])) if self.manga_data['genres'] else '-'
            self.card_page_genres_value_label.set_markup(genres)

            status = _(Manga.STATUSES[self.manga_data['status']]) if self.manga_data['status'] else '-'
            self.card_page_status_value_label.set_markup(status)

            scanlators = html_escape(', '.join(self.manga_data['scanlators'])) if self.manga_data['scanlators'] else '-'
            self.card_page_scanlators_value_label.set_markup(scanlators)

            self.card_page_server_value_label.set_markup(
                '<a href="{0}">{1}</a> [{2}]'.format(
                    self.server.get_manga_url(self.manga_data['slug'], self.manga_data.get('url')),
                    html_escape(self.server.name),
                    self.server.lang.upper(),
                )
            )

            self.card_page_chapters_value_label.set_markup(str(len(self.manga_data['chapters'])))

            self.card_page_last_chapter_value_label.set_markup(
                self.manga_data['chapters'][-1]['title'] if self.manga_data['chapters'] else '-'
            )

            self.card_page_synopsis_value_label.set_markup(self.manga_data['synopsis'] or '-')

            self.window.activity_indicator.stop()
            self.show_page('card')

            return False

        def error(server, manga_slug, message=None):
            if server != self.server or manga_slug != self.manga_slug:
                return False

            self.window.activity_indicator.stop()

            self.window.show_notification(message or _("Oops, failed to retrieve manga's information."), 2)

            return False

        self.manga = None
        self.manga_slug = manga_data['slug']
        self.window.activity_indicator.start()

        thread = threading.Thread(target=run, args=(self.server, self.manga_slug, ))
        thread.daemon = True
        thread.start()

    def populate_pinned_servers(self):
        for row in self.servers_page_pinned_listbox.get_children():
            row.destroy()

        pinned_servers = Settings.get_default().pinned_servers
        rows = []
        for server_data in self.servers:
            if server_data['id'] not in pinned_servers:
                continue

            rows.append(self.build_server_row(server_data))

        if len(rows) == 0:
            self.servers_page_pinned_listbox.hide()
            return

        # Add header row
        row = Gtk.ListBoxRow(activatable=False)
        row.get_style_context().add_class('header')
        label = Gtk.Label(xalign=0)
        label.get_style_context().add_class('subtitle')
        label.set_text(_('Pinned').upper())
        row.add(label)
        self.servers_page_pinned_listbox.add(row)

        for row in rows:
            self.servers_page_pinned_listbox.add(row)

        self.servers_page_pinned_listbox.show_all()

    def populate_servers(self, servers=None):
        if not servers:
            self.servers = get_allowed_servers_list(Settings.get_default())
            self.populate_pinned_servers()
        else:
            self.servers = servers
            self.preselection = True

        for row in self.servers_page_listbox.get_children():
            row.destroy()

        last_lang = None
        for server_data in self.servers:
            if server_data['lang'] != last_lang:
                # Add language header row
                last_lang = server_data['lang']

                row = Gtk.ListBoxRow(activatable=False)
                row.get_style_context().add_class('header')
                label = Gtk.Label(xalign=0)
                label.get_style_context().add_class('subtitle')
                label.set_text(LANGUAGES[server_data['lang']].upper())
                row.add(label)
                self.servers_page_listbox.add(row)

            row = self.build_server_row(server_data)
            self.servers_page_listbox.add(row)

        self.servers_page_listbox.show_all()

        if self.preselection and len(self.servers) == 1:
            row = self.servers_page_listbox.get_children()[1]
            self.server = getattr(row.server_data['module'], row.server_data['class_name'])()
            self.populate_card(row.manga_data)
        else:
            self.show_page('servers')

    def search(self, entry=None):
        if self.search_lock:
            return

        term = self.search_page_searchentry.get_text().strip()

        # Find manga by Id
        if term.startswith('id:'):
            slug = term[3:]

            if not slug:
                return

            self.populate_card(dict(slug=slug))
            return

        if not term and getattr(self.server, 'get_most_populars', None) is None:
            # An empty term is allowed only if server has 'get_most_populars' method
            return

        def run(server):
            most_populars = not term

            try:
                if most_populars:
                    # We offer most popular mangas as starting search results
                    result = server.get_most_populars(**self.search_filters)
                else:
                    result = server.search(term, **self.search_filters)

                if result:
                    GLib.idle_add(complete, result, server, most_populars)
                else:
                    GLib.idle_add(error, result, server)
            except Exception as e:
                user_error_message = log_error_traceback(e)
                GLib.idle_add(error, None, server, user_error_message)

        def complete(result, server, most_populars):
            if server != self.server:
                return False

            self.window.activity_indicator.stop()

            if most_populars:
                row = Gtk.ListBoxRow(activatable=False)
                row.get_style_context().add_class('header')
                row.manga_data = None
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                row.add(box)
                label = Gtk.Label(xalign=0)
                label.get_style_context().add_class('subtitle')
                label.set_text(_('MOST POPULARS'))
                box.pack_start(label, True, True, 0)

                self.search_page_listbox.add(row)

            for item in result:
                row = Gtk.ListBoxRow()
                row.manga_data = item
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                label = Gtk.Label(xalign=0)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                label.set_text(item['name'])
                box.pack_start(label, True, True, 0)
                row.add(box)

                self.search_page_listbox.add(row)

            self.search_page_listbox.show_all()

            self.search_lock = False

            return False

        def error(result, server, message=None):
            if server != self.server:
                return

            self.window.activity_indicator.stop()
            self.search_lock = False

            if message:
                self.window.show_notification(message)
            elif result is None:
                self.window.show_notification(_('Oops, search failed. Please try again.'), 2)
            elif len(result) == 0:
                self.window.show_notification(_('No results'))

        self.search_lock = True
        self.clear_search_page_results()
        self.search_page_listbox.hide()
        self.window.activity_indicator.start()

        thread = threading.Thread(target=run, args=(self.server, ))
        thread.daemon = True
        thread.start()

    def search_servers(self, _entry):
        self.servers_page_listbox.invalidate_filter()

    def show(self, transition=True, servers=None):
        self.page = None

        self.window.left_button_image.set_from_icon_name('go-previous-symbolic', Gtk.IconSize.BUTTON)
        self.window.library_flap_reveal_button.hide()
        self.window.right_button_stack.show()
        self.window.right_button_stack.set_visible_child_name('explorer.servers')

        self.window.menu_button.hide()

        self.populate_servers(servers)
        self.window.show_page('explorer', transition=transition)

    def show_page(self, name):
        if name == 'servers':
            self.title_label.set_text(_('Servers'))

            if self.page is None and self.servers_page_searchbar.get_search_mode():
                self.servers_page_searchbar.set_search_mode(False)

        elif name == 'search':
            self.title_label.set_text(self.server.name)

            if self.page == 'servers':
                self.clear_search_page_search()
                self.search()

        elif name == 'card':
            self.title_label.set_text(self.manga_data['name'])

            # Check if selected manga is already in library
            db_conn = create_db_connection()
            row = db_conn.execute(
                'SELECT * FROM mangas WHERE slug = ? AND server_id = ?',
                (self.manga_data['slug'], self.manga_data['server_id'])
            ).fetchone()
            db_conn.close()

            if row:
                self.manga = Manga.get(row['id'], self.server)

                self.card_page_add_read_button.get_children()[0].set_from_icon_name('media-playback-start-symbolic', Gtk.IconSize.BUTTON)
            else:
                self.card_page_add_read_button.get_children()[0].set_from_icon_name('list-add-symbolic', Gtk.IconSize.BUTTON)

        self.window.right_button_stack.set_visible_child_name('explorer.' + name)
        self.set_visible_child_name(name)

        self.page = name

    def toggle_server_pinned_state(self, button, row):
        if button.get_active():
            Settings.get_default().add_pinned_server(row.server_data['id'])
        else:
            Settings.get_default().remove_pinned_server(row.server_data['id'])

        if row.get_parent().get_name() == 'pinned_servers':
            for child_row in self.servers_page_listbox.get_children():
                if not hasattr(child_row, 'server_data'):
                    continue

                if child_row.server_data['id'] == row.server_data['id']:
                    child_row.get_children()[-1].get_children()[-1].set_active(button.get_active())
                    break

        self.populate_pinned_servers()

    def toggle_servers_search(self, button):
        self.servers_page_searchbar.set_search_mode(button.get_active())

        if button.get_active():
            self.servers_page_pinned_listbox.hide()
        else:
            self.servers_page_pinned_listbox.show()
