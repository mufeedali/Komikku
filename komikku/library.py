# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import cairo
from gettext import gettext as _
import time

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GdkPixbuf import PixbufAnimation

from komikku.downloader import DownloadManagerDialog
from komikku.models import create_db_connection
from komikku.models import Manga
from komikku.servers import get_file_mime_type
from komikku.utils import scale_pixbuf_animation


class Library():
    search_mode = False
    selection_mode = False
    selection_mode_count = 0
    selection_mode_range = False
    selection_mode_last_child_index = None

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/info/febvre/Komikku/ui/menu/library_selection_mode.xml')

        # Search
        self.title_stack = self.builder.get_object('library_page_title_stack')
        self.search_entry = self.builder.get_object('library_page_search_searchentry')
        self.search_entry.connect('activate', self.on_search_entry_activate)
        self.search_entry.connect('changed', self.search)
        self.search_button = self.builder.get_object('library_page_search_button')
        self.search_button.connect('toggled', self.toggle_search_mode)

        self.flowbox = self.builder.get_object('library_page_flowbox')
        self.flowbox.connect('child-activated', self.on_manga_clicked)
        self.gesture = Gtk.GestureLongPress.new(self.flowbox)
        self.gesture.set_touch_only(False)
        self.gesture.connect('pressed', self.on_gesture_long_press_activated)

        self.window.connect('key-press-event', self.on_key_press)
        self.window.updater.connect('manga-updated', self.on_manga_updated)

        def _filter(child):
            manga = child.get_children()[0].manga
            term = self.search_entry.get_text().lower()

            # Search in name
            ret = term in manga.name.lower()

            # Search in server name
            ret = ret or term in manga.server.name.lower()

            # Search in genres (exact match)
            ret = ret or term in [genre.lower() for genre in manga.genres]

            return ret

        def _sort(child1, child2):
            """
            This function gets two children and has to return:
            - a negative integer if the firstone should come before the second one
            - zero if they are equal
            - a positive integer if the second one should come before the firstone
            """
            manga1 = child1.get_children()[0].manga
            manga2 = child2.get_children()[0].manga

            if manga1.last_read > manga2.last_read:
                return -1

            if manga1.last_read < manga2.last_read:
                return 1

            return 0

        self.populate()

        self.flowbox.set_filter_func(_filter)
        self.flowbox.set_sort_func(_sort)

    @property
    def cover_size(self):
        default_width = 180
        default_height = 250

        box_width = self.window.get_size().width
        # Padding of flowbox children is 4px
        # https://pastebin.com/Q4ahCcgu
        padding = 4
        child_width = default_width + padding * 2
        if box_width / child_width != box_width // child_width:
            nb = box_width // child_width + 1
            width = box_width // nb - (padding * 2)
            height = default_height // (default_width / width)
        else:
            width = default_width
            height = default_height

        return width, height

    def add_actions(self):
        # Menu actions
        update_action = Gio.SimpleAction.new('library.update', None)
        update_action.connect('activate', self.update_all)
        self.window.application.add_action(update_action)

        download_manager_action = Gio.SimpleAction.new('library.download-manager', None)
        download_manager_action.connect('activate', self.open_download_manager)
        self.window.application.add_action(download_manager_action)

        # Menu actions in selection mode
        delete_selected_action = Gio.SimpleAction.new('library.delete-selected', None)
        delete_selected_action.connect('activate', self.delete_selected)
        self.window.application.add_action(delete_selected_action)

        update_selected_action = Gio.SimpleAction.new('library.update-selected', None)
        update_selected_action.connect('activate', self.update_selected)
        self.window.application.add_action(update_selected_action)

        select_all_action = Gio.SimpleAction.new('library.select-all', None)
        select_all_action.connect('activate', self.select_all)
        self.window.application.add_action(select_all_action)

    def add_manga(self, manga, position=-1):
        width, height = self.cover_size

        overlay = Gtk.Overlay()
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)
        overlay.manga = manga
        overlay._pixbuf = None
        overlay._selected = False

        # Cover
        overlay.add_overlay(Gtk.Image())
        self.set_manga_cover_image(overlay, width, height)

        # Name (bottom)
        label = Gtk.Label(xalign=0)
        label.get_style_context().add_class('library-manga-name-label')
        label.set_valign(Gtk.Align.END)
        label.set_line_wrap(True)
        label.set_text(manga.name)
        overlay.add_overlay(label)

        # Server logo (top left corner)
        drawingarea = Gtk.DrawingArea()
        drawingarea.connect('draw', self.draw_cover_server_logo, manga)
        overlay.add_overlay(drawingarea)

        # Badges: number of recents chapters and number of downloaded chapters (top right corner)
        drawingarea = Gtk.DrawingArea()
        drawingarea.connect('draw', self.draw_cover_badges, manga)
        overlay.add_overlay(drawingarea)

        overlay.show_all()
        self.flowbox.insert(overlay, position)

    def delete_selected(self, action, param):
        def confirm_callback():
            # Stop Downloader & Updater
            self.window.downloader.stop()
            self.window.updater.stop()

            while self.window.downloader.running or self.window.updater.running:
                time.sleep(0.1)
                continue

            # Safely delete mangas in DB
            for child in self.flowbox.get_selected_children():
                child.get_children()[0].manga.delete()

            # Restart Downloader & Updater
            self.window.downloader.start()
            self.window.updater.start()

            # Finally, update library
            self.populate()

            self.leave_selection_mode()

        self.window.confirm(
            _('Delete?'),
            _('Are you sure you want to delete selected mangas?'),
            confirm_callback
        )

    def draw_cover_badges(self, da, ctx, manga):
        """
        Draws badges in top right corner of cover
        * Unread chapter: green
        * Recent chapters: blue
        * Downloaded chapters: red
        """
        nb_unread_chapters = manga.nb_unread_chapters
        nb_recent_chapters = manga.nb_recent_chapters
        nb_downloaded_chapters = manga.nb_downloaded_chapters

        if nb_unread_chapters == nb_recent_chapters == nb_downloaded_chapters == 0:
            return

        cover_width, _cover_height = self.cover_size
        spacing = 5  # with top and right borders, between badges
        x = cover_width

        ctx.save()
        ctx.set_font_size(13)

        def draw_badge(nb, color_r, color_g, color_b):
            nonlocal x

            if nb == 0:
                return

            text = str(nb)
            text_extents = ctx.text_extents(text)
            width = text_extents.x_advance + 2 * 3 + 1
            height = text_extents.height + 2 * 5

            # Draw rectangle
            x = x - spacing - width
            ctx.set_source_rgb(color_r, color_g, color_b)
            ctx.rectangle(x, spacing, width, height)
            ctx.fill()

            # Draw number
            ctx.set_source_rgb(1, 1, 1)
            ctx.move_to(x + 3, height)
            ctx.show_text(text)

        draw_badge(nb_unread_chapters, 0.2, 0.5, 0)        # #338000
        draw_badge(nb_recent_chapters, 0.2, 0.6, 1)        # #3399FF
        draw_badge(nb_downloaded_chapters, 1, 0.266, 0.2)  # #FF4433

        ctx.restore()

    @staticmethod
    def draw_cover_server_logo(da, ctx, manga):
        size = 75

        ctx.save()

        # Draw triangle
        gradient = cairo.LinearGradient(0, 0, size / 2, size / 2)
        gradient.add_color_stop_rgba(0, 0, 0, 0, 0.75)
        gradient.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(gradient)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.rel_line_to(0, size)
        ctx.rel_line_to(size, -size)
        ctx.close_path()
        ctx.fill()

        # Draw server logo
        pixbuf = Pixbuf.new_from_resource_at_scale(manga.server.logo_resource_path, 20, 20, True)
        Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 4, 4)
        ctx.paint()

        ctx.restore()

    def enter_search_mode(self):
        if self.selection_mode:
            # 'Search mode' is not allowed in 'Selection mode'
            return

        self.search_button.set_active(True)

    def enter_selection_mode(self, x=None, y=None, selected_child=None):
        if self.search_mode:
            # 'Selection mode' is not allowed in 'Search mode'
            return

        # Set search button insensitive: disable search
        self.search_button.set_sensitive(False)

        self.selection_mode = True
        self.selection_mode_count = 1

        self.flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        if selected_child is None:
            if x is not None and y is not None:
                selected_child = self.flowbox.get_child_at_pos(x, y)
            else:
                selected_child = self.flowbox.get_child_at_index(0)
        selected_overlay = selected_child.get_children()[0]
        self.flowbox.select_child(selected_child)
        selected_overlay._selected = True
        self.selection_mode_last_child_index = selected_child.get_index()

        self.window.titlebar.set_selection_mode(True)
        self.window.left_button_image.set_from_icon_name('go-previous-symbolic', Gtk.IconSize.MENU)
        self.window.menu_button.set_menu_model(self.builder.get_object('menu-library-selection-mode'))

    def leave_search_mode(self):
        self.search_button.set_active(False)

    def leave_selection_mode(self):
        self.selection_mode = False

        # Set search button sensitive: re-enable search
        self.search_button.set_sensitive(True)

        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for child in self.flowbox.get_children():
            overlay = child.get_children()[0]
            overlay._selected = False

        self.window.titlebar.set_selection_mode(False)
        self.window.left_button_image.set_from_icon_name('list-add-symbolic', Gtk.IconSize.MENU)
        self.window.menu_button.set_menu_model(self.builder.get_object('menu'))

    def on_gesture_long_press_activated(self, gesture, x, y):
        if self.selection_mode:
            # Enter in 'Range' selection mode
            # Long press on a manga then long press on another to select everything in between
            self.selection_mode_range = True

            selected_child = self.flowbox.get_child_at_pos(x, y)
            self.flowbox.select_child(selected_child)
            self.on_manga_clicked(self.flowbox, selected_child)
        else:
            self.enter_selection_mode(x, y)

    def on_key_press(self, widget, event):
        """Search can be triggered by simply typing a printable character"""

        if self.window.page != 'library':
            return Gdk.EVENT_PROPAGATE

        modifiers = event.get_state() & Gtk.accelerator_get_default_mod_mask()
        is_printable = GLib.unichar_isgraph(chr(Gdk.keyval_to_unicode(event.keyval)))
        if is_printable and modifiers in (Gdk.ModifierType.SHIFT_MASK, 0) and not self.search_mode:
            self.enter_search_mode()

        return Gdk.EVENT_PROPAGATE

    def on_manga_added(self, manga):
        """Called from 'Add dialog' when user clicks on [+] button"""
        db_conn = create_db_connection()
        nb_mangas = db_conn.execute('SELECT count(*) FROM mangas').fetchone()[0]
        db_conn.close()

        if nb_mangas == 1:
            # Library was previously empty
            self.populate()
        else:
            self.add_manga(manga, position=0)

    def on_manga_clicked(self, flowbox, child):
        overlay = child.get_children()[0]
        _ret, state = Gtk.get_current_event_state()
        modifiers = state & Gtk.accelerator_get_default_mod_mask()

        # Enter selection mode if <Control>+Click or <Shift>+Click is done
        if modifiers in (Gdk.ModifierType.CONTROL_MASK, Gdk.ModifierType.SHIFT_MASK) and not self.selection_mode:
            self.enter_selection_mode(selected_child=child)
            return Gdk.EVENT_PROPAGATE

        if self.selection_mode:
            if modifiers == Gdk.ModifierType.SHIFT_MASK:
                # Enter range selection mode if <Shift>+Click is done
                self.selection_mode_range = True
            if self.selection_mode_range and self.selection_mode_last_child_index is not None:
                # Range selection mode: select all mangas between last selected manga and clicked manga
                walk_index = self.selection_mode_last_child_index
                last_index = child.get_index()

                while walk_index != last_index:
                    walk_child = self.flowbox.get_child_at_index(walk_index)
                    walk_overlay = walk_child.get_children()[0]
                    if walk_child and not walk_overlay._selected:
                        self.selection_mode_count += 1
                        self.flowbox.select_child(walk_child)
                        walk_overlay._selected = True

                    if walk_index < last_index:
                        walk_index += 1
                    else:
                        walk_index -= 1

            self.selection_mode_range = False

            if overlay._selected:
                self.selection_mode_count -= 1
                self.selection_mode_last_child_index = None
                self.flowbox.unselect_child(child)
                overlay._selected = False
            else:
                self.selection_mode_count += 1
                self.selection_mode_last_child_index = child.get_index()
                overlay._selected = True
            if self.selection_mode_count == 0:
                self.leave_selection_mode()
        else:
            self.window.card.init(overlay.manga)

    def on_manga_deleted(self, manga):
        # Remove manga cover in flowbox
        for child in self.flowbox.get_children():
            overlay = child.get_children()[0]
            if overlay.manga.id == manga.id:
                child.destroy()
                break

    def on_manga_updated(self, updater, manga, nb_recent_chapters, nb_deleted_chapters):
        for child in self.flowbox.get_children():
            overlay = child.get_children()[0]

            if overlay.manga.id != manga.id:
                continue

            overlay.manga = manga

            # Update cover
            width, height = self.cover_size
            self.set_manga_cover_image(overlay, width, height, True)

            # Update manga name
            name_label = overlay.get_children()[1]
            name_label.set_text(manga.name)

            break

        # Schedule a redraw. It will update drawing areas (servers logos and badges)
        self.flowbox.queue_draw()

    def on_resize(self):
        if self.window.first_start_grid.is_ancestor(self.window):
            return

        width, height = self.cover_size

        for child in self.flowbox.get_children():
            overlay = child.get_children()[0]
            self.set_manga_cover_image(overlay, width, height)

    def on_search_entry_activate(self, _entry):
        """Open first manga in search when <Enter> is pressed"""
        child = self.flowbox.get_child_at_pos(0, 0)
        if child:
            self.on_manga_clicked(self.flowbox, child)

    def open_download_manager(self, action, param):
        DownloadManagerDialog(self.window).open(action, param)

    def populate(self):
        db_conn = create_db_connection()
        mangas_rows = db_conn.execute('SELECT * FROM mangas ORDER BY last_read DESC').fetchall()

        if len(mangas_rows) == 0:
            if self.window.overlay.is_ancestor(self.window):
                self.window.remove(self.window.overlay)

            # Display first start message
            self.window.add(self.window.first_start_grid)

            return

        if self.window.first_start_grid.is_ancestor(self.window):
            self.window.remove(self.window.first_start_grid)

        if not self.window.overlay.is_ancestor(self.window):
            self.window.add(self.window.overlay)

        # Clear library flowbox
        for child in self.flowbox.get_children():
            child.destroy()

        # Populate flowbox with mangas
        for row in mangas_rows:
            self.add_manga(Manga.get(row['id']))

        db_conn.close()

    def search(self, search_entry):
        self.flowbox.invalidate_filter()

    def select_all(self, action=None, param=None):
        if not self.selection_mode:
            self.enter_selection_mode()
        if not self.selection_mode:
            return

        self.selection_mode_count = len(self.flowbox.get_children())

        for child in self.flowbox.get_children():
            overlay = child.get_children()[0]
            if overlay._selected:
                continue
            overlay._selected = True
            self.flowbox.select_child(child)

    @staticmethod
    def set_manga_cover_image(overlay, width, height, update=False):
        if overlay._pixbuf is None or update:
            manga = overlay.manga

            if manga.cover_fs_path is None:
                overlay._pixbuf = Pixbuf.new_from_resource('/info/febvre/Komikku/images/missing_file.png')
            else:
                if get_file_mime_type(manga.cover_fs_path) != 'image/gif':
                    overlay._pixbuf = Pixbuf.new_from_file_at_scale(manga.cover_fs_path, 200, -1, True)
                else:
                    overlay._pixbuf = scale_pixbuf_animation(PixbufAnimation.new_from_file(manga.cover_fs_path), 200, -1, True)

        overlay.set_size_request(width, height)
        image = overlay.get_children()[0]
        if isinstance(overlay._pixbuf, PixbufAnimation):
            image.set_from_animation(scale_pixbuf_animation(overlay._pixbuf, width, height, False, loop=True))
        else:
            image.set_from_pixbuf(overlay._pixbuf.scale_simple(width, height, InterpType.BILINEAR))

    def show(self, invalidate_sort=False):
        self.window.left_button_image.set_from_icon_name('list-add-symbolic', Gtk.IconSize.MENU)

        self.builder.get_object('fullscreen_button').hide()

        self.window.menu_button.set_menu_model(self.builder.get_object('menu'))
        self.window.menu_button_image.set_from_icon_name('open-menu-symbolic', Gtk.IconSize.MENU)

        if self.search_mode:
            self.search_entry.grab_focus_without_selecting()

        if invalidate_sort:
            self.flowbox.invalidate_sort()

        self.window.show_page('library')

    def toggle_search_mode(self, button):
        if button.get_active():
            self.search_mode = True

            self.title_stack.set_visible_child_name('searchentry')
            self.search_entry.grab_focus()
        else:
            self.search_mode = False

            self.title_stack.set_visible_child_name('title')
            self.search_entry.set_text('')
            self.search_entry.grab_remove()

    def update_all(self, action, param):
        self.window.updater.update_library()

    def update_selected(self, action, param):
        self.window.updater.add([child.get_children()[0].manga for child in self.flowbox.get_selected_children()])
        self.window.updater.start()

        self.leave_selection_mode()
