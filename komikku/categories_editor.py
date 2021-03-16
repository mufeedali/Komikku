# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Handy

from komikku.models import Category
from komikku.models import create_db_connection


@Gtk.Template.from_resource('/info/febvre/Komikku/ui/categories_editor_window.ui')
class CategoriesEditorWindow(Handy.Window):
    __gtype_name__ = 'CategoriesEditorWindow'

    parent = NotImplemented
    edited_row = None

    back_button = Gtk.Template.Child('back_button')
    add_entry = Gtk.Template.Child('add_entry')
    add_button = Gtk.Template.Child('add_button')

    stack = Gtk.Template.Child('stack')
    listbox = Gtk.Template.Child('listbox')

    def __init__(self, window):
        Handy.Window.__init__(self)

        self.parent = window

        self.back_button.connect('clicked', self.on_back_button_clicked)
        self.add_entry.connect('activate', self.add_category)
        self.add_button.connect('clicked', self.add_category)

        self.connect('key-press-event', self.on_key_press)

    @property
    def rows(self):
        return self.listbox.get_children()

    def add_category(self, _button):
        label = self.add_entry.get_text().strip()
        if not label:
            return

        category = Category.new(label)
        if category:
            self.stack.set_visible_child_name('list')

            self.add_entry.set_text('')
            row = CategoryRow(category)
            row.delete_button.connect('clicked', self.delete_category, row)
            row.save_button.connect('clicked', self.update_category, row)
            row.connect('edit-mode-changed', self.on_category_edit_mode_changed)

            self.listbox.add(row)

            self.parent.library.categories_list.populate()

    def close(self):
        self.destroy()

    def delete_category(self, _button, row):
        def confirm_callback():
            row.category.delete()
            row.destroy()

            if not self.rows:
                self.stack.set_visible_child_name('empty')

            self.parent.library.categories_list.populate(refresh_library=True)

        self.parent.confirm(
            _('Delete?'),
            _('Are you sure you want to delete the "{0}" category?').format(row.category.label),
            confirm_callback
        )

    def on_back_button_clicked(self, button=None):
        self.close()

    def on_category_edit_mode_changed(self, row, active):
        if not active:
            if self.edited_row == row:
                self.edited_row = None
            return

        if self.edited_row:
            self.edited_row.set_edit_mode(active=False)

        self.edited_row = row

    def on_key_press(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def open(self, _action, _param):
        self.set_transient_for(self.parent)
        self.populate()
        self.present()

    def populate(self):
        db_conn = create_db_connection()
        records = db_conn.execute('SELECT * FROM categories ORDER BY label ASC').fetchall()
        db_conn.close()

        if records:
            for record in records:
                category = Category.get(record['id'])

                row = CategoryRow(category)
                row.delete_button.connect('clicked', self.delete_category, row)
                row.save_button.connect('clicked', self.update_category, row)
                row.connect('edit-mode-changed', self.on_category_edit_mode_changed)

                self.listbox.add(row)

            self.stack.set_visible_child_name('list')
        else:
            self.stack.set_visible_child_name('empty')

    def update_category(self, _button, row):
        label = row.edit_entry.get_text().strip()
        if not label:
            return

        res = row.category.update(dict(
            label=label,
        ))
        if res:
            row.set_label(label)
            row.set_edit_mode(active=False)

            self.parent.library.categories_list.populate()


class CategoryRow(Gtk.ListBoxRow):
    __gsignals__ = {
        'edit-mode-changed': (GObject.SIGNAL_RUN_FIRST, None, (bool, )),
    }

    category = None

    def __init__(self, category):
        Gtk.ListBoxRow.__init__(self, visible=True)

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, visible=True, margin=6)

        self.category = category

        label = category.label
        if nb_mangas := category.nb_mangas:
            label = f'{label} ({nb_mangas})'
        self.label = Gtk.Label(label, visible=True)
        self.label.set_halign(Gtk.Align.START)
        self.box.pack_start(self.label, True, True, 0)

        self.edit_entry = Gtk.Entry(visible=False)
        self.edit_entry.set_valign(Gtk.Align.CENTER)
        self.box.pack_start(self.edit_entry, True, True, 0)

        self.edit_button = Gtk.Button.new_from_icon_name('document-edit-symbolic', Gtk.IconSize.MENU)
        self.edit_button.set_valign(Gtk.Align.CENTER)
        self.edit_button.show()
        self.edit_button.connect('clicked', self.set_edit_mode, True)
        self.box.pack_end(self.edit_button, False, True, 0)

        self.delete_button = Gtk.Button.new_from_icon_name('user-trash-symbolic', Gtk.IconSize.MENU)
        self.delete_button.set_valign(Gtk.Align.CENTER)
        self.delete_button.show()
        self.box.pack_end(self.delete_button, False, True, 0)

        self.cancel_button = Gtk.Button.new_from_icon_name('edit-undo-symbolic', Gtk.IconSize.MENU)
        self.cancel_button.set_valign(Gtk.Align.CENTER)
        self.cancel_button.connect('clicked', self.set_edit_mode, False)
        self.box.pack_end(self.cancel_button, False, True, 0)

        self.save_button = Gtk.Button.new_from_icon_name('document-save-symbolic', Gtk.IconSize.MENU)
        self.save_button.set_valign(Gtk.Align.CENTER)
        self.box.pack_end(self.save_button, False, True, 0)

        self.add(self.box)

    def set_edit_mode(self, _button=None, active=False):
        if active:
            self.label.hide()
            self.edit_entry.set_text(self.category.label)
            self.edit_entry.show()
            self.delete_button.hide()
            self.edit_button.hide()
            self.cancel_button.show()
            self.save_button.show()
        else:
            self.label.show()
            self.edit_entry.set_text('')
            self.edit_entry.hide()
            self.delete_button.show()
            self.edit_button.show()
            self.cancel_button.hide()
            self.save_button.hide()

        self.emit('edit-mode-changed', active)

    def set_label(self, text):
        self.label.set_text(text)
