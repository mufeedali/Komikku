# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import threading
import time

from gi.repository import GLib
from gi.repository import Notify

from komikku.models import Download
from komikku.models import Settings
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

    def remove(self, chapter):
        running = self.status == 'running'

        self.stop()

        while self.status == 'running':
            time.sleep(0.1)
            continue

        download = Download.get_by_chapter_id(chapter.id)
        download.delete()

        self.window.card.update_chapter_row(chapter)

        if running:
            self.start()

    def start(self):
        def run():
            exclude_errors = False
            while self.status == 'running':
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
                                self.status = 'interrupted'
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

                        if self.status == 'interrupted':
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

            self.status = 'done'

        def notify_progress(chapter, index, success):
            if notification is not None:
                summary = _('Download page {0} / {1}').format(index + 1, len(chapter.pages))
                if not success:
                    summary = '{0} ({1})'.format(summary, _('error'))

                notification.update(
                    summary,
                    _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title)
                )
                notification.show()

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

        if self.status == 'running':
            return

        self.status = 'running'
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

    def stop(self):
        if self.status == 'running':
            self.stop_flag = True
