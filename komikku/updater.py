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

    def __init__(self, window):
        self.window = window

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
                        GLib.idle_add(complete, manga, nb_recent_chapters)
                    else:
                        GLib.idle_add(error, manga)
                except Exception as e:
                    GLib.idle_add(error, None, error_message(e))

            self.status = 'done'

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
                    # Update card only if manga has not changed
                    if self.window.card.manga and self.window.card.manga.id == manga.id:
                        self.window.card.init(manga)

            return False

        def error(manga, message=None):
            self.window.show_notification(message or _('{0}\nOops, update has failed. Please try again.').format(manga.name))

            return False

        if self.status == 'running':
            return

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
