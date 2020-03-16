# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
from gettext import ngettext as n_
import threading

from gi.repository import GLib
from gi.repository import GObject

from komikku.utils import log_error_traceback
from komikku.models import create_db_connection
from komikku.models import Manga
from komikku.models import Settings


class Updater(GObject.GObject):
    """ Mangas updater """
    __gsignals__ = {
        'manga-updated': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_PYOBJECT, int, int, )),
    }

    queue = []
    running = False
    stop_flag = False
    update_library_flag = False

    def __init__(self, window, update_at_startup=False):
        GObject.GObject.__init__(self)

        self.window = window

        if update_at_startup:
            self.update_library()

    def add(self, mangas):
        if not isinstance(mangas, list):
            mangas = [mangas, ]

        for manga in mangas:
            if manga.status not in (None, 'ongoing'):
                # Suspended, complete, ...
                continue

            if manga.id not in self.queue:
                self.queue.append(manga.id)

    def start(self):
        def run():
            total_recent_chapters = 0

            while self.queue:
                if self.stop_flag is True:
                    break

                manga = Manga.get(self.queue.pop(0))
                if manga is None:
                    continue

                try:
                    status, recent_chapters_ids, nb_deleted_chapters = manga.update_full()
                    if status is True:
                        total_recent_chapters += len(recent_chapters_ids)
                        GLib.idle_add(complete, manga, recent_chapters_ids, nb_deleted_chapters)
                    else:
                        GLib.idle_add(error, manga)
                except Exception as e:
                    user_error_message = log_error_traceback(e)
                    GLib.idle_add(error, manga, user_error_message)

            self.running = False

            # End notification
            if self.update_library_flag:
                self.update_library_flag = False
                message = _('Library update completed')
            else:
                message = _('Update completed')

            if total_recent_chapters > 0:
                message = '{0}\n{1}'.format(
                    message,
                    n_('{0} new chapter found', '{0} new chapters found', total_recent_chapters).format(
                        total_recent_chapters
                    )
                )
            else:
                message = '{0}\n{1}'.format(message, _('No new chapter found'))

            self.window.show_notification(message)

        def complete(manga, recent_chapters_ids, nb_deleted_chapters):
            nb_recent_chapters = len(recent_chapters_ids)

            if nb_recent_chapters > 0:
                self.window.show_notification(
                    n_('{0}\n{1} new chapter has been found', '{0}\n{1} new chapters have been found', nb_recent_chapters).format(
                        manga.name, nb_recent_chapters
                    )
                )

                # Auto download new chapters
                if Settings.get_default().new_chapters_auto_download:
                    for chapter_id in recent_chapters_ids:
                        self.window.downloader.add(chapter_id)

                    self.window.downloader.start()

            self.emit('manga-updated', manga, nb_recent_chapters, nb_deleted_chapters)

            return False

        def error(manga, message=None):
            self.window.show_notification(message or _('{0}\nOops, update has failed. Please try again.').format(manga.name))

            return False

        if self.running or len(self.queue) == 0:
            return

        if self.update_library_flag:
            self.window.show_notification(_('Library update started'))
        else:
            self.window.show_notification(_('Update started'))

        self.running = True
        self.stop_flag = False

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def remove(self, manga):
        if manga.id in self.queue:
            self.queue.remove(manga.id)

    def stop(self):
        if self.running:
            self.stop_flag = True

    def update_library(self):
        self.update_library_flag = True

        db_conn = create_db_connection()
        rows = db_conn.execute('SELECT * FROM mangas ORDER BY last_read DESC').fetchall()
        db_conn.close()

        for row in rows:
            self.add(Manga.get(row['id']))

        self.start()
