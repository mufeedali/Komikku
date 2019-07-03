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
    started = False
    stop_flag = False

    def __init__(self, change_cb):
        self.change_cb = change_cb
        self.kill_event = threading.Event()

    def start(self):
        def run():
            while self.stop_flag is False:
                download = Download.next()

                if download:
                    chapter = Chapter(id=download.chapter_id)

                    download.update(dict(status='downloading'))
                    GLib.idle_add(start, chapter)

                    if chapter.update():

                        for index, page in enumerate(chapter.pages):
                            if self.stop_flag:
                                break

                            chapter.get_page(index)

                            download.update(dict(percent=(index + 1) * 100 / len(chapter.pages)))
                            GLib.idle_add(update_notification, chapter, index)

                            time.sleep(1)

                        if self.stop_flag is False:
                            chapter.update(dict(downloaded=1))
                            download.delete()
                            GLib.idle_add(complete, chapter)
                    else:
                        download.update(dict(status='error'))
                        GLib.idle_add(error, chapter)
                else:
                    self.stop_flag = True

            self.started = False

        def update_notification(chapter, index):
            notification.update(
                _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title),
                _('Download page {0} / {1}').format(index + 1, len(chapter.pages))
            )
            notification.show()

            return False

        def complete(chapter):
            notification.update(
                _('[{0}] Chapter {1}').format(chapter.manga.name, chapter.title),
                _('Download completed')
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

        if self.started:
            return

        self.started = True
        self.stop_flag = False

        # Create notification
        notification = Notify.Notification.new(_('Start chapters download'))
        notification.set_timeout(Notify.EXPIRES_DEFAULT)
        notification.show()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def stop(self):
        if self.started:
            self.stop_flag = True
