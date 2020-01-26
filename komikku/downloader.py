# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading
import time

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Notify

from komikku.models import create_db_connection
from komikku.models import Chapter
from komikku.models import Download
from komikku.models import Settings
from komikku.utils import log_error_traceback


class Downloader(GObject.GObject):
    """
    Chapters downloader
    """
    __gsignals__ = {
        'page-downloaded': (GObject.SIGNAL_RUN_FIRST, None, (int, int, )),
        'page-error': (GObject.SIGNAL_RUN_FIRST, None, (int, int, )),
        'ended': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'started': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    running = False
    stop_flag = False

    def __init__(self, window):
        GObject.GObject.__init__(self)

        self.window = window
        if Settings.get_default().downloader_state:
            self.start()

    def add(self, chapter):
        Download.new(chapter.id)

    def remove(self, chapters):
        if not isinstance(chapters, list):
            chapters = [chapters, ]

        was_running = self.running

        self.stop()

        while self.running:
            time.sleep(0.1)
            continue

        for chapter in chapters:
            download = Download.get_by_chapter_id(chapter.id)
            if download:
                download.delete()

            self.window.card.update_chapter_row(chapter)

        if was_running:
            self.start()

    def start(self):
        def run():
            GLib.idle_add(self.emit, 'started')

            interrupted = False
            exclude_errors = False
            while True:
                if self.stop_flag:
                    break

                download = Download.next(exclude_errors=exclude_errors)
                exclude_errors = True
                if download is None:
                    break

                download.update(dict(status='downloading'))

                chapter = download.chapter
                GLib.idle_add(update_ui, chapter)

                try:
                    if download.chapter.update_full():
                        error_counter = 0
                        for index, page in enumerate(chapter.pages):
                            if self.stop_flag:
                                interrupted = True
                                break

                            if chapter.get_page_path(index) is None:
                                path = chapter.get_page(index)
                                if path is not None:
                                    success = True
                                else:
                                    success = False
                                    error_counter += 1

                                download.update(dict(percent=(index + 1) * 100 / len(chapter.pages)))
                                GLib.idle_add(notify_progress, chapter, index, success)

                                if index < len(chapter.pages) - 1 and not self.stop_flag:
                                    time.sleep(1)

                        if interrupted:
                            download.update(dict(status='pending'))
                        else:
                            if error_counter == 0:
                                # All pages were successfully downloaded
                                chapter.update(dict(downloaded=1))
                                download.delete()
                                GLib.idle_add(notify_complete, chapter)
                            else:
                                # At least one page failed to be downloaded
                                download.update(dict(status='error'))
                                GLib.idle_add(update_ui, chapter)
                    else:
                        # Possible causes:
                        # - Outdated chapter info
                        # - Server has undergone changes (API, HTML) and code is outdated
                        download.update(dict(status='error'))
                        GLib.idle_add(update_ui, chapter)
                except Exception as e:
                    # Possible causes:
                    # - No Internet connection
                    # - Connexion timeout
                    # - Server down
                    download.update(dict(status='error'))
                    user_error_message = log_error_traceback(e)
                    GLib.idle_add(update_ui, chapter, user_error_message)

            self.running = False
            GLib.idle_add(self.emit, 'ended')

        def notify_progress(chapter, index, success):
            if notification is not None:
                summary = _('Download page {0}/{1}').format(index + 1, len(chapter.pages))
                if not success:
                    summary = '{0} ({1})'.format(summary, _('error'))

                notification.update(
                    summary,
                    _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title)
                )
                notification.show()

            self.emit('page-downloaded' if success else 'page-error', chapter.id, index + 1)

            return update_ui(chapter)

        def notify_complete(chapter):
            if notification is not None:
                notification.update(
                    _('Download completed'),
                    _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title)
                )
                notification.show()

            return update_ui(chapter)

        def update_ui(chapter, message=None):
            self.window.card.update_chapter_row(chapter)

            if message:
                self.window.show_notification(message)

            return False

        if self.running:
            return

        Settings.get_default().downloader_state = True
        self.running = True
        self.stop_flag = False

        if Settings.get_default().desktop_notifications:
            # Create notification
            notification = Notify.Notification.new('')
            notification.set_timeout(Notify.EXPIRES_DEFAULT)
        else:
            notification = None

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def stop(self, save_state=False):
        if self.running:
            self.stop_flag = True
            if save_state:
                Settings.get_default().downloader_state = False


class DownloadManagerDialog():
    selection_count = 0
    selection_mode = False

    def __init__(self, window):
        self.window = window
        self.builder = window.builder
        self.builder.add_from_resource('/info/febvre/Komikku/ui/download_manager_dialog.ui')
        self.builder.add_from_resource('/info/febvre/Komikku/ui/menu/download_manager.xml')
        self.builder.add_from_resource('/info/febvre/Komikku/ui/menu/download_manager_selection_mode.xml')

        self.dialog = self.builder.get_object('dialog')
        self.dialog.set_transient_for(self.window)

        self.titlebar = self.builder.get_object('titlebar')

        self.builder.get_object('back_button').connect('clicked', self.on_back_button_clicked)

        self.start_stop_button = self.builder.get_object('start_stop_button')
        self.start_stop_button_image = self.builder.get_object('start_stop_button_image')
        self.start_stop_button.connect('clicked', self.on_start_stop_button_clicked)

        self.menu_button = self.builder.get_object('menu_button')
        self.menu_button.set_menu_model(self.builder.get_object('menu-download-manager'))

        self.stack = self.builder.get_object('stack')

        self.listbox = self.builder.get_object('listbox')
        self.listbox.connect('row-activated', self.on_download_row_clicked)

        # Gesture for multi-selection mode
        self.gesture = Gtk.GestureLongPress.new(self.listbox)
        self.gesture.set_touch_only(False)
        self.gesture.connect('pressed', self.enter_selection_mode)

        self.window.downloader.connect('page-downloaded', self.update_row)
        self.window.downloader.connect('page-error', self.update_row)
        self.window.downloader.connect('ended', self.update_headerbar)
        self.window.downloader.connect('started', self.update_headerbar)

        action_group = Gio.SimpleActionGroup.new()

        # Delete All action
        delete_all_action = Gio.SimpleAction.new('delete-all', None)
        delete_all_action.connect('activate', self.on_menu_delete_all_clicked)
        action_group.add_action(delete_all_action)

        # Delete Selected action
        delete_selected_action = Gio.SimpleAction.new('delete-selected', None)
        delete_selected_action.connect('activate', self.on_menu_delete_selected_clicked)
        action_group.add_action(delete_selected_action)

        self.dialog.insert_action_group('download-manager', action_group)

    @property
    def rows(self):
        return self.listbox.get_children()

    def enter_selection_mode(self, gesture, x, y):
        self.selection_mode = True
        self.selection_count = 0

        self.listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        self.titlebar.set_selection_mode(True)
        self.menu_button.set_menu_model(self.builder.get_object('menu-download-manager-selection-mode'))

    def leave_selection_mode(self):
        self.selection_mode = False

        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for row in self.rows:
            row._selected = False

        self.titlebar.set_selection_mode(False)
        self.menu_button.set_menu_model(self.builder.get_object('menu-download-manager'))

    def on_back_button_clicked(self, button):
        if self.selection_mode:
            self.leave_selection_mode()
        else:
            self.dialog.close()

    def on_download_row_clicked(self, listbox, row):
        if not self.selection_mode:
            return

        if row._selected:
            self.selection_count -= 1
            self.listbox.unselect_row(row)
            row._selected = False
        else:
            self.selection_count += 1
            self.listbox.select_row(row)
            row._selected = True

        if self.selection_count == 0:
            self.leave_selection_mode()

    def on_menu_delete_all_clicked(self, action, param):
        chapters = []
        for row in self.rows:
            chapters.append(row.download.chapter)
            row.destroy()

        self.window.downloader.remove(chapters)

        self.leave_selection_mode()
        self.update_headerbar()
        GLib.idle_add(self.stack.set_visible_child_name, 'empty')

    def on_menu_delete_selected_clicked(self, action, param):
        chapters = []
        for row in self.rows:
            if row._selected:
                chapters.append(row.download.chapter)
                row.destroy()

        self.window.downloader.remove(chapters)

        self.leave_selection_mode()
        self.update_headerbar()
        if not self.rows:
            GLib.idle_add(self.stack.set_visible_child_name, 'empty')

    def on_start_stop_button_clicked(self, button):
        self.start_stop_button.set_sensitive(False)

        if self.window.downloader.running:
            self.window.downloader.stop(save_state=True)
        else:
            self.window.downloader.start()

    def open(self, action, param):
        self.populate()
        self.update_headerbar()

        self.dialog.present()

    def populate(self):
        db_conn = create_db_connection()
        records = db_conn.execute('SELECT * FROM downloads ORDER BY date ASC').fetchall()
        db_conn.close()

        if records:
            for record in records:
                download = Download.get(record['id'])

                row = DownloadRow(download)
                self.listbox.add(row)

            self.listbox.show_all()
            self.stack.set_visible_child_name('list')
        else:
            self.stack.set_visible_child_name('empty')

    def update_headerbar(self, *args):
        if self.rows:
            if self.window.downloader.running:
                self.start_stop_button_image.set_from_icon_name('media-playback-stop-symbolic', Gtk.IconSize.MENU)
            else:
                self.start_stop_button_image.set_from_icon_name('media-playback-start-symbolic', Gtk.IconSize.MENU)

            self.start_stop_button.set_sensitive(True)
            self.start_stop_button.show()
            self.menu_button.show()
        else:
            self.start_stop_button.hide()
            self.menu_button.hide()

    def update_row(self, downloader, chapter_id, index):
        for row in self.rows:
            if row.download.chapter.id == chapter_id:
                if row.update(index) == 0:
                    row.destroy()
                break

        if not self.rows:
            self.stack.set_visible_child_name('empty')


class DownloadRow(Gtk.ListBoxRow):
    _selected = False

    def __init__(self, download):
        Gtk.ListBoxRow.__init__(self)

        self.get_style_context().add_class('download-manager-download-listboxrow')

        self.download = download

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        # Manga
        label = Gtk.Label(xalign=0)
        label.get_style_context().add_class('download-manager-download-label')
        label.set_valign(Gtk.Align.CENTER)
        label.set_line_wrap(True)
        label.set_text(download.chapter.manga.name)
        hbox.pack_start(label, True, True, 0)

        # Progress label
        self.progress_label = Gtk.Label(xalign=0)
        self.progress_label.get_style_context().add_class('download-manager-download-label')
        self.progress_label.set_valign(Gtk.Align.CENTER)
        self.progress_label.set_line_wrap(True)
        hbox.pack_start(self.progress_label, False, False, 0)

        vbox.pack_start(hbox, True, True, 0)

        # Chapter
        label = Gtk.Label(xalign=0)
        label.get_style_context().add_class('download-manager-download-sublabel')
        label.set_valign(Gtk.Align.CENTER)
        label.set_line_wrap(True)
        label.set_text(download.chapter.title)
        vbox.pack_start(label, True, True, 0)

        # Progress bar
        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_show_text(False)
        vbox.pack_start(self.progressbar, True, True, 0)

        self.add(vbox)

    def update(self, index):
        """
        Updates chapter download progress

        :return: number of remaining pages
        :rtype: int
        """
        chapter = Chapter.get(self.download.chapter.id)

        nb_pages = len(chapter.pages)
        percent = index / nb_pages

        self.progressbar.set_fraction(percent)
        self.progress_label.set_text('{0}/{1}'.format(index, nb_pages))

        return nb_pages - index
