# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
from gettext import ngettext as n_
import threading

from gi.repository import GLib

from komikku.utils import error_message
from komikku.model import create_db_connection
from komikku.model import Manga


class Updater():
    """
    Mangas updater
    """
    queue = []
    status = None
    stop_flag = False
    update_library_flag = False

    def __init__(self, window, update_at_startup=False):
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
                    self.status = 'interrupted'
                    break

                manga = Manga.get(self.queue.pop(0))
                if manga is None:
                    continue

                try:
                    status, nb_recent_chapters = manga.update_full()
                    if status is True:
                        total_recent_chapters += nb_recent_chapters
                        GLib.idle_add(complete, manga, nb_recent_chapters)
                    else:
                        GLib.idle_add(error, manga)
                except Exception as e:
                    GLib.idle_add(error, None, error_message(e))

            self.status = 'done'

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

        def complete(manga, nb_recent_chapters):
            if nb_recent_chapters > 0:
                self.window.show_notification(
                    n_('{0}\n{1} new chapter has been found', '{0}\n{1} new chapters have been found', nb_recent_chapters).format(
                        manga.name, nb_recent_chapters
                    )
                )

                if self.window.page == 'library':
                    # Schedule a library redraw
                    self.window.library.flowbox.queue_draw()
                elif self.window.page == 'card':
                    # Update card if card manga is manga updated
                    if self.window.card.manga and self.window.card.manga.id == manga.id:
                        self.window.card.init(manga)

            return False

        def error(manga, message=None):
            self.window.show_notification(message or _('{0}\nOops, update has failed. Please try again.').format(manga.name))

            return False

        if self.status == 'running' or len(self.queue) == 0:
            return

        if self.update_library_flag:
            self.window.show_notification(_('Library update started'))
        else:
            self.window.show_notification(_('Update started'))

        self.status = 'running'
        self.stop_flag = False

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def remove(self, manga):
        if manga.id in self.queue:
            self.queue.remove(manga.id)

    def stop(self):
        if self.status == 'running':
            self.stop_flag = True

    def update_library(self):
        self.update_library_flag = True

        db_conn = create_db_connection()
        rows = db_conn.execute('SELECT * FROM mangas ORDER BY last_read DESC').fetchall()
        db_conn.close()

        for row in rows:
            self.add(Manga.get(row['id']))

        self.start()
