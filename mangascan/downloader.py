# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gi.repository import GLib
from gi.repository import Notify

from gettext import gettext as _
import threading
import time

from mangascan.model import Chapter
from mangascan.model import Download


class Downloader():
    """
    Chapters downloader
    """
    status = None
    stop_flag = False

    def __init__(self, change_cb):
        self.change_cb = change_cb
        self.kill_event = threading.Event()

    def add(self, chapter_id):
        Download.new(chapter_id)

    def start(self):
        def run():
            while self.status == 'running':
                download = Download.next()

                if download:
                    chapter = Chapter(id=download.chapter_id)

                    download.update(dict(status='downloading'))
                    GLib.idle_add(start, chapter)

                    if chapter.update_full():
                        for index, page in enumerate(chapter.pages):
                            if self.stop_flag:
                                self.status = 'interrupted'
                                download.update(dict(status='pending'))
                                break

                            if chapter.get_page_path(index) is None:
                                path = chapter.get_page(index)

                                download.update(dict(percent=(index + 1) * 100 / len(chapter.pages)))
                                GLib.idle_add(notify_progress, chapter, index, path is not None)

                                if index < len(chapter.pages) - 1 and not self.stop_flag:
                                    time.sleep(1)

                        if self.status != 'interrupted':
                            chapter.update(dict(downloaded=1))
                            download.delete()
                            GLib.idle_add(complete, chapter)
                    else:
                        download.update(dict(status='error'))
                        GLib.idle_add(error, chapter)
                else:
                    self.status = 'done'

        def notify_progress(chapter, index, success):
            summary = _('Download page {0} / {1}').format(index + 1, len(chapter.pages))
            if not success:
                summary = '{0} ({1})'.format(summary, _('error'))

            notification.update(
                summary,
                _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title)
            )
            notification.show()

            return False

        def complete(chapter):
            notification.update(
                _('Download completed'),
                _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title)
            )
            notification.show()

            self.change_cb(chapter)

            return False

        def error(chapter):
            self.change_cb(chapter)

            return False

        def start(chapter):
            self.change_cb(chapter)

            return False

        if self.status == 'running':
            return

        self.status = 'running'
        self.stop_flag = False

        # Create notification
        notification = Notify.Notification.new(_('Start chapters download'))
        notification.set_timeout(Notify.EXPIRES_DEFAULT)
        notification.show()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def stop(self):
        if self.status == 'running':
            self.stop_flag = True
