# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GdkPixbuf import PixbufAnimation
from gi.repository import Pango

from komikku.activity_indicator import ActivityIndicator
from komikku.models import create_db_connection
from komikku.models import Manga
from komikku.models import Settings
from komikku.servers import get_buffer_mime_type
from komikku.servers import get_server_logo_resource_path_by_id
from komikku.servers import get_server_main_id_by_id
from komikku.servers import get_servers_list
from komikku.servers import LANGUAGES
from komikku.utils import html_escape
from komikku.utils import log_error_traceback
from komikku.utils import scale_pixbuf_animation


class AddDialog:
    page = None
    search_filters = None
    search_lock = False

    server = None
    manga_slug = None
    manga_data = None
    manga = None

    def __init__(self, window):
        self.window = window
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/info/febvre/Komikku/ui/add_dialog.ui')

        self.dialog = self.builder.get_object('dialog')
        self.dialog.get_children()[0].set_border_width(0)

        # Header bar
        self.builder.get_object('back_button').connect('clicked', self.on_back_button_clicked)
        self.custom_title_stack = self.builder.get_object('custom_title_stack')

        # Make title centered
        self.builder.get_object('custom_title_servers_page_label').set_margin_end(38)

        self.overlay = self.builder.get_object('overlay')
        self.stack = self.builder.get_object('stack')

        self.activity_indicator = ActivityIndicator()
        self.overlay.add_overlay(self.activity_indicator)
        self.overlay.set_overlay_pass_through(self.activity_indicator, True)
        self.activity_indicator.show_all()

        # Servers page
        listbox = self.builder.get_object('servers_page_listbox')
        listbox.get_style_context().add_class('list-bordered')
        listbox.connect('row-activated', self.on_server_clicked)

        settings = Settings.get_default()
        servers_settings = settings.servers_settings
        servers_languages = settings.servers_languages

        for server_data in get_servers_list():
            if servers_languages and server_data['lang'] not in servers_languages:
                continue

            server_settings = servers_settings.get(get_server_main_id_by_id(server_data['id']))
            if server_settings is not None and (not server_settings['enabled'] or server_settings['langs'].get(server_data['lang']) is False):
                continue

            if settings.nsfw_content is False and server_data['is_nsfw']:
                continue

            row = Gtk.ListBoxRow()
            row.get_style_context().add_class('add-dialog-server-listboxrow')
            row.server_data = server_data
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.add(box)

            # Server logo
            logo = Gtk.Image()
            pixbuf = Pixbuf.new_from_resource_at_scale(
                get_server_logo_resource_path_by_id(server_data['id']), 24 * self.window.hidpi_scale, 24 * self.window.hidpi_scale, True)
            logo.set_from_surface(Gdk.cairo_surface_create_from_pixbuf(pixbuf, self.window.hidpi_scale))
            box.pack_start(logo, False, True, 0)

            # Server title
            label = Gtk.Label(xalign=0)
            title = server_data['name']
            if server_data['is_nsfw']:
                title += ' (NSFW)'
            label.set_text(title)
            box.pack_start(label, True, True, 0)

            # Server language
            label = Gtk.Label()
            label.set_text(LANGUAGES[server_data['lang']])
            label.get_style_context().add_class('add-dialog-server-language-label')
            box.pack_start(label, False, True, 0)

            listbox.add(row)

        listbox.show_all()

        # Search page
        self.custom_title_search_page_searchentry = self.builder.get_object('custom_title_search_page_searchentry')
        self.custom_title_search_page_searchentry.connect('activate', self.search)
        self.custom_title_search_page_filter_menu_button = self.builder.get_object('custom_title_search_page_filter_menu_button')

        self.search_page_listbox = self.builder.get_object('search_page_listbox')
        self.search_page_listbox.get_style_context().add_class('list-bordered')
        self.search_page_listbox.connect('row-activated', self.on_manga_clicked)

        # Manga page
        grid = self.builder.get_object('manga_page_grid')
        grid.set_margin_top(6)
        grid.set_margin_end(6)
        grid.set_margin_bottom(6)
        grid.set_margin_start(6)
        self.custom_title_manga_page_label = self.builder.get_object('custom_title_manga_page_label')
        self.add_button = self.builder.get_object('add_button')
        self.add_button.connect('clicked', self.on_add_button_clicked)
        self.read_button = self.builder.get_object('read_button')
        self.read_button.connect('clicked', self.on_read_button_clicked)

        self.show_page('servers')

    def clear_search(self):
        self.custom_title_search_page_searchentry.set_text('')
        self.clear_results()
        self.init_filters()

    def clear_results(self):
        for child in self.search_page_listbox.get_children():
            self.search_page_listbox.remove(child)

    def hide_notification(self):
        self.builder.get_object('notification_revealer').set_reveal_child(False)

    def init_filters(self):
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
                radio_button = Gtk.RadioButton(label=option['name'], active=is_active, visible=True)
                radio_button.join_group(last)
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
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, visible=True)
        vbox.set_margin_top(6)
        vbox.set_margin_end(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(6)

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

        self.custom_title_search_page_filter_menu_button.set_popover(popover)

    def on_add_button_clicked(self, button):
        def run():
            manga = Manga.new(self.manga_data, self.server)
            GLib.idle_add(complete, manga)

        def complete(manga):
            self.manga = manga

            self.show_notification(_('{0} manga added').format(self.manga.name))

            self.window.library.on_manga_added(self.manga)

            self.add_button.set_sensitive(True)
            self.add_button.hide()
            self.read_button.show()
            self.activity_indicator.stop()

            return False

        self.activity_indicator.start()
        self.add_button.set_sensitive(False)

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def on_back_button_clicked(self, button):
        if self.page == 'servers':
            self.dialog.close()

        elif self.page == 'search':
            self.activity_indicator.stop()
            self.search_lock = False
            self.server = None
            self.show_page('servers')

        elif self.page == 'manga':
            self.activity_indicator.stop()
            self.manga_slug = None
            self.show_page('search')

    def on_manga_clicked(self, listbox, row):
        if row.manga_data is None:
            return

        self.show_manga(row.manga_data)

    def on_read_button_clicked(self, button):
        self.window.card.init(self.manga, transition=False)
        self.dialog.close()

    def on_server_clicked(self, listbox, row):
        self.server = getattr(row.server_data['module'], row.server_data['class_name'])()
        self.show_page('search')

    def open(self, action, param):
        self.dialog.set_modal(True)
        self.dialog.set_transient_for(self.window)
        self.dialog.present()

    def search(self, entry=None):
        if self.search_lock:
            return

        term = self.custom_title_search_page_searchentry.get_text().strip()

        # Find manga by Id
        if term.startswith('id:'):
            slug = term[3:]

            if not slug:
                return

            self.show_manga(dict(slug=slug))
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

            self.activity_indicator.stop()

            if most_populars:
                row = Gtk.ListBoxRow()
                row.get_style_context().add_class('add-dialog-search-section-listboxrow')
                row.manga_data = None
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                row.add(box)
                label = Gtk.Label(xalign=0, margin=6)
                label.set_text(_('MOST POPULARS'))
                box.pack_start(label, True, True, 0)

                self.search_page_listbox.add(row)

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

        def error(result, server, message=None):
            if server != self.server:
                return

            self.activity_indicator.stop()
            self.search_lock = False

            if message:
                self.show_notification(message)
            elif result is None:
                self.show_notification(_('Oops, search failed. Please try again.'), 2)
            elif len(result) == 0:
                self.show_notification(_('No results'))

        self.search_lock = True
        self.clear_results()
        self.activity_indicator.start()

        thread = threading.Thread(target=run, args=(self.server, ))
        thread.daemon = True
        thread.start()

    def show_manga(self, manga_data):
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
                    self.show_notification(user_error_message)

            if cover_data is None:
                pixbuf = Pixbuf.new_from_resource_at_scale(
                    '/info/febvre/Komikku/images/missing_file.png', 174 * self.window.hidpi_scale, -1, True)
            else:
                cover_stream = Gio.MemoryInputStream.new_from_data(cover_data, None)
                if get_buffer_mime_type(cover_data) != 'image/gif':
                    pixbuf = Pixbuf.new_from_stream_at_scale(cover_stream, 174 * self.window.hidpi_scale, -1, True, None)
                else:
                    pixbuf = scale_pixbuf_animation(PixbufAnimation.new_from_stream(cover_stream), 174, -1, True, True)

            if isinstance(pixbuf, PixbufAnimation):
                self.builder.get_object('cover_image').set_from_animation(pixbuf)
            else:
                self.builder.get_object('cover_image').set_from_surface(
                    Gdk.cairo_surface_create_from_pixbuf(pixbuf, self.window.hidpi_scale))

            authors = html_escape(', '.join(self.manga_data['authors'])) if self.manga_data['authors'] else '-'
            self.builder.get_object('authors_value_label').set_markup('<span size="small">{0}</span>'.format(authors))

            genres = html_escape(', '.join(self.manga_data['genres'])) if self.manga_data['genres'] else '-'
            self.builder.get_object('genres_value_label').set_markup('<span size="small">{0}</span>'.format(genres))

            status = _(Manga.STATUSES[self.manga_data['status']]) if self.manga_data['status'] else '-'
            self.builder.get_object('status_value_label').set_markup('<span size="small">{0}</span>'.format(status))

            scanlators = html_escape(', '.join(self.manga_data['scanlators'])) if self.manga_data['scanlators'] else '-'
            self.builder.get_object('scanlators_value_label').set_markup('<span size="small">{0}</span>'.format(scanlators))

            self.builder.get_object('server_value_label').set_markup(
                '<span size="small"><a href="{0}">{1} [{2}]</a>\n{3} chapters</span>'.format(
                    self.server.get_manga_url(self.manga_data['slug'], self.manga_data.get('url')),
                    html_escape(self.server.name),
                    self.server.lang.upper(),
                    len(self.manga_data['chapters'])
                )
            )

            self.builder.get_object('synopsis_value_label').set_text(self.manga_data['synopsis'] or '-')

            self.activity_indicator.stop()
            self.show_page('manga')

            return False

        def error(server, manga_slug, message=None):
            if server != self.server or manga_slug != self.manga_slug:
                return False

            self.activity_indicator.stop()

            self.show_notification(message or _("Oops, failed to retrieve manga's information."), 2)

            return False

        self.manga_slug = manga_data['slug']
        self.activity_indicator.start()

        thread = threading.Thread(target=run, args=(self.server, self.manga_slug, ))
        thread.daemon = True
        thread.start()

    def show_notification(self, message, interval=5):
        if not message:
            return

        self.builder.get_object('notification_label').set_text(message)
        self.builder.get_object('notification_revealer').set_reveal_child(True)

        revealer_timer = threading.Timer(interval, GLib.idle_add, args=[self.hide_notification])
        revealer_timer.start()

    def show_page(self, name):
        if name == 'search':
            if self.page == 'servers':
                self.custom_title_search_page_searchentry.set_placeholder_text(_('Search in {0}…').format(self.server.name))
                self.clear_search()
                self.search()
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
                self.manga = Manga.get(row['id'], self.server)

                self.read_button.show()
                self.add_button.hide()
            else:
                self.add_button.show()
                self.read_button.hide()

        self.custom_title_stack.set_visible_child_name(name)
        self.stack.set_visible_child_name(name)
        self.page = name
