# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import os
import shutil

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from komikku.models import Settings
from komikku.reader.controls import Controls
from komikku.reader.pager import Pager
from komikku.reader.pager.webtoon import WebtoonPager
from komikku.servers import get_file_mime_type
from komikku.utils import is_flatpak


class Reader:
    manga = None
    chapters_consulted = None
    pager = None

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/info/febvre/Komikku/ui/menu/reader.xml')

        self.overlay = self.window.reader_overlay
        self.scrolledwindow = self.window.reader_scrolledwindow
        self.viewport = self.window.reader_viewport

        # Headerbar
        self.title_label = self.window.reader_title_label
        self.subtitle_label = self.window.reader_subtitle_label
        self.fullscreen_button = self.window.fullscreen_button

        # Page number indicator
        self.page_number_label = Gtk.Label()
        self.page_number_label.get_style_context().add_class('reader-page-number-indicator-label')
        self.page_number_label.set_valign(Gtk.Align.END)
        self.overlay.add_overlay(self.page_number_label)

        # Controls
        self.controls = Controls(self)

    @property
    def background_color(self):
        return self.manga.background_color or Settings.get_default().background_color

    @property
    def borders_crop(self):
        if self.manga.borders_crop in (0, 1):
            return bool(self.manga.borders_crop)

        return Settings.get_default().borders_crop

    @property
    def reading_mode(self):
        return self.manga.reading_mode or Settings.get_default().reading_mode

    @property
    def scaling(self):
        return self.manga.scaling or Settings.get_default().scaling

    @property
    def size(self):
        window_size = self.window.get_size()

        size = Gtk.Requisition.new()
        size.width = window_size.width
        size.height = window_size.height

        if self.window.headerbar_revealer.get_child_revealed():
            size.height -= self.window.headerbar.get_preferred_size()[1].height

        return size

    def add_accelerators(self):
        self.window.application.set_accels_for_action('app.reader.save-page', ['<Control>s'])

    def add_actions(self):
        # Reading mode
        self.reading_mode_action = Gio.SimpleAction.new_stateful(
            'reader.reading-mode', GLib.VariantType.new('s'), GLib.Variant('s', 'right-to-left'))
        self.reading_mode_action.connect('change-state', self.on_reading_mode_changed)
        self.window.application.add_action(self.reading_mode_action)

        # Scaling
        self.scaling_action = Gio.SimpleAction.new_stateful(
            'reader.scaling', GLib.VariantType.new('s'), GLib.Variant('s', 'screen'))
        self.scaling_action.connect('change-state', self.on_scaling_changed)
        self.window.application.add_action(self.scaling_action)

        # Background color
        self.background_color_action = Gio.SimpleAction.new_stateful(
            'reader.background-color', GLib.VariantType.new('s'), GLib.Variant('s', 'white'))
        self.background_color_action.connect('change-state', self.on_background_color_changed)
        self.window.application.add_action(self.background_color_action)

        # Borders crop
        self.borders_crop_action = Gio.SimpleAction.new_stateful('reader.borders-crop', None, GLib.Variant('b', False))
        self.borders_crop_action.connect('change-state', self.on_borders_crop_changed)
        self.window.application.add_action(self.borders_crop_action)

        # Save page
        self.save_page_action = Gio.SimpleAction.new('reader.save-page', None)
        self.save_page_action.connect('activate', self.save_page)
        self.window.application.add_action(self.save_page_action)

    def init(self, manga, chapter):
        self.manga = manga

        # Reset list of chapters consulted
        self.chapters_consulted = set()

        # Init settings
        self.set_action_reading_mode()
        self.set_action_scaling()
        self.set_action_borders_crop()

        # Init pager
        self.init_pager(chapter)
        self.set_action_background_color()

        self.show()

    def init_pager(self, chapter, reverse_pages=False):
        self.remove_pager()

        if self.reading_mode == 'webtoon':
            self.pager = WebtoonPager(self)
        else:
            self.pager = Pager(self)

        self.set_orientation()

        self.viewport.add(self.pager)

        self.pager.init(chapter)

    def on_background_color_changed(self, action, variant):
        value = variant.get_string()
        if value == self.background_color:
            return

        self.manga.update(dict(background_color=value))
        self.set_action_background_color()

    def on_borders_crop_changed(self, action, variant):
        self.manga.update(dict(borders_crop=variant.get_boolean()))
        self.set_action_borders_crop()
        self.pager.crop_pages_borders()

    def on_reading_mode_changed(self, action, variant):
        value = variant.get_string()
        if value == self.reading_mode:
            return

        prior_reading_mode = self.reading_mode

        self.manga.update(dict(reading_mode=value))
        self.set_action_reading_mode()

        if value == 'webtoon' or prior_reading_mode == 'webtoon':
            self.init_pager(self.pager.current_page.chapter)
        else:
            if value == 'right-to-left' or prior_reading_mode == 'right-to-left':
                self.pager.reverse_pages()
            self.set_orientation()

    def on_resize(self):
        self.pager.resize_pages()

    def on_scaling_changed(self, action, variant):
        value = variant.get_string()
        if value == self.scaling:
            return

        self.manga.update(dict(scaling=value))
        self.set_action_scaling()

        self.pager.rescale_pages()

    def remove_pager(self):
        if self.pager:
            self.pager.clear()
            self.pager.destroy()
            self.pager = None

    def save_page(self, action, param):
        if self.window.page != 'reader':
            return

        page = self.pager.current_page
        if page.status != 'rendered' or page.error is not None:
            return

        extension = get_file_mime_type(page.path).split('/')[-1]
        filename = f'{self.manga.name}_{page.chapter.title}_{str(page.index + 1)}.{extension}'

        success = False
        xdg_pictures_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
        if not is_flatpak():
            chooser = Gtk.FileChooserDialog(
                _('Please choose a file'),
                self.window,
                Gtk.FileChooserAction.SAVE,
                (
                    _('Cancel'),
                    Gtk.ResponseType.CANCEL,
                    _('Save'),
                    Gtk.ResponseType.ACCEPT
                )
            )
            chooser.set_do_overwrite_confirmation(True)
            chooser.set_current_name(filename)
            if xdg_pictures_dir is not None:
                chooser.set_current_folder(xdg_pictures_dir)

            response = chooser.run()
            if response == Gtk.ResponseType.ACCEPT:
                dest_path = chooser.get_filename()
                success = True
            chooser.destroy()
        else:
            if xdg_pictures_dir:
                dest_path = os.path.join(xdg_pictures_dir, filename)
                success = True
            else:
                self.window.show_notification(_('Failed to save page: missing permission to access the XDG pictures directory'))

        if success:
            shutil.copy(page.path, dest_path)
            self.window.show_notification(_('Page successfully saved to {0}').format(dest_path.replace(os.path.expanduser('~'), '~')))

    def set_action_background_color(self):
        self.background_color_action.set_state(GLib.Variant('s', self.background_color))
        if self.background_color == 'white':
            self.pager.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        else:
            self.pager.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))

    def set_action_borders_crop(self):
        self.borders_crop_action.set_state(GLib.Variant('b', self.borders_crop))

    def set_action_reading_mode(self):
        self.reading_mode_action.set_state(GLib.Variant('s', self.reading_mode))

        # Scaling action is enabled in RTL and LTR reading modes only
        self.scaling_action.set_enabled(self.reading_mode != 'webtoon')

        # Additionally, direction of page slider in controls must be updated
        self.controls.set_scale_direction(inverted=self.reading_mode == 'right-to-left')

    def set_action_scaling(self, scaling=None):
        self.scaling_action.set_state(GLib.Variant('s', scaling or self.scaling))

    def set_orientation(self):
        if self.reading_mode in ('right-to-left', 'left-to-right'):
            orientation = Gtk.Orientation.HORIZONTAL
        else:
            orientation = Gtk.Orientation.VERTICAL

        self.pager.set_orientation(orientation)

    def show(self):
        def on_menu_popover_closed(menu_button):
            self.pager.grab_focus()

        self.window.library.search_button.hide()
        self.window.card.resume_read_button.hide()
        self.fullscreen_button.show()

        self.window.menu_button.set_menu_model(self.builder.get_object('menu-reader'))
        self.window.menu_button_image.set_from_icon_name('view-more-symbolic', Gtk.IconSize.MENU)
        # Watch when menu is closed to be able to restore focus to pager
        self.window.menu_button.get_popover().connect('closed', on_menu_popover_closed)

        self.page_number_label.hide()
        self.controls.hide()

        if Settings.get_default().fullscreen:
            self.window.set_fullscreen()

        self.window.show_page('reader')

    def toggle_controls(self):
        if self.controls.is_visible:
            self.controls.hide()
            self.page_number_label.show()
        else:
            self.controls.show()
            self.page_number_label.hide()

    def update_page_number(self, number, total):
        if total is not None:
            self.page_number_label.set_text('{0}/{1}'.format(number, total))

        if not self.controls.is_visible and total is not None:
            self.page_number_label.show()
        else:
            self.page_number_label.hide()

    def update_title(self, chapter):
        # Add chapter to list of chapters consulted
        # This list is used by the Card page to update chapters rows
        self.chapters_consulted.add(chapter)

        # Set title & subtitle (headerbar)
        self.title_label.set_text(chapter.manga.name)
        subtitle = chapter.title
        if chapter.manga.name in subtitle:
            subtitle = subtitle.replace(chapter.manga.name, '').strip()
        self.subtitle_label.set_text(subtitle)
