# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading
import time

from gi.repository import GLib
from gi.repository import Notify

from komikku.models import Download
from komikku.models import create_db_connection
from komikku.utils import log_error_traceback


class Downloader():
    """
    Chapters downloader
    """
    status = None
    stop_flag = False

    def __init__(self, window):
        self.window = window
        self.start()

    def add(self, chapter):
        Download.new(chapter.id)

    def start(self):
        def run():
            db_conn = create_db_connection()
            rows = db_conn.execute('SELECT * FROM downloads ORDER BY date ASC').fetchall()
            db_conn.close()

            for row in rows:
                if self.stop_flag:
                    break

                download = Download.get(row['id'])
                download.update(dict(status='downloading'))

                chapter = download.chapter
                GLib.idle_add(start, chapter)

                try:
                    if download.chapter.update_full():
                        error_counter = 0
                        for index, page in enumerate(chapter.pages):
                            if self.stop_flag:
                                self.status = 'interrupted'
                                download.update(dict(status='pending'))
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

                        if self.status != 'interrupted':
                            if error_counter == 0:
                                chapter.update(dict(downloaded=1))
                            download.delete()
                            GLib.idle_add(complete, chapter)
                    else:
                        download.update(dict(status='error'))
                        GLib.idle_add(error, chapter)
                except Exception as e:
                    download.update(dict(status='pending'))
                    user_error_message = log_error_traceback(e)
                    GLib.idle_add(error, chapter, user_error_message)

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

            self.window.card.update_chapter_row(chapter)

            return False

        def error(chapter, message=None):
            self.window.card.update_chapter_row(chapter)

            if message:
                self.window.show_notification(message)

            return False

        def start(chapter):
            self.window.card.update_chapter_row(chapter)

            return False

        if self.status == 'running':
            return

        self.status = 'running'
        self.stop_flag = False

        # Create notification
        notification = Notify.Notification.new('')
        notification.set_timeout(Notify.EXPIRES_DEFAULT)

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def stop(self):
        if self.status == 'running':
            self.stop_flag = True
