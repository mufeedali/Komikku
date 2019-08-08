# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf

from mangascan.model import create_db_connection
from mangascan.model import Manga


class Library():
    selection_mode = False

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/info/febvre/MangaScan/menu_library_selection_mode.xml')

        self.flowbox = self.builder.get_object('library_page_flowbox')
        self.flowbox.connect('child-activated', self.on_manga_clicked)
        self.gesture = Gtk.GestureLongPress.new(self.flowbox)
        self.gesture.set_touch_only(False)
        self.gesture.connect('pressed', self.enter_selection_mode)

        def sort(child1, child2):
            """
            This function gets two children and has to return:
            - a negative integer if the firstone should come before the second one
            - zero if they are equal
            - a positive integer if the second one should come before the firstone
            """
            manga1 = Manga(child1.get_children()[0].manga.id)
            manga2 = Manga(child2.get_children()[0].manga.id)

            if manga1.last_read > manga2.last_read:
                return -1
            elif manga1.last_read < manga2.last_read:
                return 1
            else:
                return 0

        self.flowbox.set_sort_func(sort)

        self.populate()

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
        # Menu actions in selection mode
        delete_selected_action = Gio.SimpleAction.new('library.delete-selected', None)
        delete_selected_action.connect('activate', self.delete_selected)
        self.window.application.add_action(delete_selected_action)

        update_selected_action = Gio.SimpleAction.new('library.update-selected', None)
        update_selected_action.connect('activate', self.update_selected)
        self.window.application.add_action(update_selected_action)

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
        label = Gtk.Label()
        label.get_style_context().add_class('library-manga-name-label')
        label.set_valign(Gtk.Align.END)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_text(manga.name)
        overlay.add_overlay(label)

        # Server logo (top left corner)
        def draw(da, ctx):
            size = 40

            ctx.save()

            # Draw triangle
            ctx.set_source_rgba(0, 0, 0, .5)
            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.rel_line_to(0, size)
            ctx.rel_line_to(size, -size)
            ctx.close_path()
            ctx.fill()

            # Draw logo
            pixbuf = Pixbuf.new_from_resource_at_scale(
                '/info/febvre/MangaScan/icons/ui/favicons/{0}.ico'.format(manga.server_id), 16, 16, True)
            Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 2, 2)
            ctx.paint()

            ctx.restore()

        drawingarea = Gtk.DrawingArea()
        drawingarea.connect('draw', draw)
        overlay.add_overlay(drawingarea)

        overlay.show_all()
        self.flowbox.insert(overlay, position)

    def delete_selected(self, action, param):
        def confirm_callback():
            for child in self.flowbox.get_selected_children():
                manga = child.get_children()[0].manga
                manga.delete()

            self.populate()

            self.leave_selection_mode()

        self.window.confirm(
            _('Delete?'),
            _('Are you sure you want to delete selected mangas?'),
            confirm_callback
        )

    def enter_selection_mode(self, gesture, x, y):
        self.selection_mode = True

        self.flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        selected_child = self.flowbox.get_child_at_pos(x, y)
        selected_overlay = selected_child.get_children()[0]
        self.flowbox.select_child(selected_child)
        selected_overlay._selected = True

        self.window.titlebar.set_selection_mode(True)
        self.builder.get_object('left_button_image').set_from_icon_name('go-previous-symbolic', Gtk.IconSize.MENU)
        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu-library-selection-mode'))

    def leave_selection_mode(self):
        self.selection_mode = False

        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for child in self.flowbox.get_children():
            overlay = child.get_children()[0]
            overlay._selected = False

        self.window.titlebar.set_selection_mode(False)
        self.builder.get_object('left_button_image').set_from_icon_name('list-add-symbolic', Gtk.IconSize.MENU)
        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu'))

    def on_manga_added(self, manga):
        """
        Called from 'Add dialog' when user clicks on [+] button
        """
        db_conn = create_db_connection()
        nb_mangas = db_conn.execute('SELECT count(*) FROM mangas').fetchone()[0]
        db_conn.close()

        if nb_mangas == 1:
            # Library was previously empty
            self.populate()
        else:
            self.add_manga(manga, position=0)

    def on_manga_clicked(self, flowbox, child):
        if self.selection_mode:
            overlay = child.get_children()[0]
            if overlay._selected:
                self.flowbox.unselect_child(child)
                overlay._selected = False
            else:
                overlay._selected = True
        else:
            self.window.card.init(child.get_children()[0].manga)

    def on_manga_deleted(self, manga):
        # Remove manga cover in flowbox
        for child in self.flowbox.get_children():
            if child.get_children()[0].manga.id == manga.id:
                child.destroy()
                break

    def on_resize(self):
        if self.window.first_start_grid.is_ancestor(self.window):
            return

        width, height = self.cover_size

        for child in self.flowbox.get_children():
            overlay = child.get_children()[0]
            self.set_manga_cover_image(overlay, width, height)

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
            self.add_manga(Manga(row['id']))

        db_conn.close()

    def set_manga_cover_image(self, overlay, width, height):
        overlay.set_size_request(width, height)

        if overlay._pixbuf is None:
            manga = overlay.manga
            if manga.cover_fs_path is not None:
                overlay._pixbuf = Pixbuf.new_from_file(manga.cover_fs_path)
            else:
                overlay._pixbuf = Pixbuf.new_from_resource('/info/febvre/MangaScan/images/missing_file.png')

        pixbuf = overlay._pixbuf.scale_simple(width, height, InterpType.BILINEAR)
        image = overlay.get_children()[0]
        image.set_from_pixbuf(pixbuf)

    def show(self):
        self.window.headerbar.set_title('Manga Scan')

        self.builder.get_object('left_button_image').set_from_icon_name('list-add-symbolic', Gtk.IconSize.MENU)

        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu'))
        self.builder.get_object('menubutton_image').set_from_icon_name('open-menu-symbolic', Gtk.IconSize.MENU)

        self.flowbox.invalidate_sort()
        self.window.show_page('library')

    def update_selected(self, action, param):
        def run():
            self.window.show_notification(_('Start update'))

            for child in self.flowbox.get_selected_children():
                manga = child.get_children()[0].manga
                if manga.update():
                    GLib.idle_add(complete, manga)
                else:
                    GLib.idle_add(error, manga)

        def complete(manga):
            self.window.show_notification(_('{0} successfully updated').format(manga.name))
            return False

        def error(manga):
            self.window.show_notification(_('Oops, {0} update failed. Please try again.').format(manga.name))
            return False

        if not self.window.application.connected:
            self.window.show_notification(_('No Internet connection'))
            return

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

        self.leave_selection_mode()
