# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import cairo
from contextlib import closing
import datetime
from functools import lru_cache
from functools import wraps
from gettext import gettext as _
import gi
import html
import json
import keyring
from keyring.credentials import Credential
import logging
import os
from PIL import Image
from PIL import ImageChops
import requests
import subprocess
import traceback

gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository.GdkPixbuf import Colorspace
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GdkPixbuf import PixbufLoader
from gi.repository.GdkPixbuf import PixbufSimpleAnim

keyring.core.init_backend()

logger = logging.getLogger('komikku')


def create_cairo_surface_from_pixbuf(pixbuf, hidpi_scale):
    if pixbuf.get_n_channels() == 3:
        format = cairo.Format.RGB24
    else:
        format = cairo.Format.ARGB32

    surface = cairo.ImageSurface(format, pixbuf.get_width(), pixbuf.get_height())
    surface.set_device_scale(hidpi_scale, hidpi_scale)

    context = cairo.Context(surface)
    context.scale(1 / hidpi_scale, 1 / hidpi_scale)
    Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
    context.paint()

    return surface


def folder_size(path):
    if not os.path.exists(path):
        return 0

    res = subprocess.run(['du', '-sh', path], stdout=subprocess.PIPE, check=False)

    return res.stdout.split()[0].decode()


@lru_cache(maxsize=None)
def get_cache_dir():
    cache_dir_path = GLib.get_user_cache_dir()

    # Check if inside flatpak sandbox
    if is_flatpak():
        return cache_dir_path

    cache_dir_path = os.path.join(cache_dir_path, 'komikku')
    if not os.path.exists(cache_dir_path):
        os.mkdir(cache_dir_path)

    return cache_dir_path


@lru_cache(maxsize=None)
def get_data_dir():
    data_dir_path = GLib.get_user_data_dir()

    # Check if inside flatpak sandbox
    if is_flatpak():
        return data_dir_path

    base_path = data_dir_path
    data_dir_path = os.path.join(base_path, 'komikku')
    if not os.path.exists(data_dir_path):
        os.mkdir(data_dir_path)

        # Until version 0.11.0, data files (chapters, database) were stored in a wrong place
        from komikku.servers import get_servers_list

        must_be_moved = ['komikku.db', 'komikku_backup.db', ]
        for server in get_servers_list(include_disabled=True):
            must_be_moved.append(server['id'])

        for name in must_be_moved:
            data_path = os.path.join(base_path, name)
            if os.path.exists(data_path):
                os.rename(data_path, os.path.join(data_dir_path, name))

    return data_dir_path


def html_escape(s):
    return html.escape(html.unescape(s), quote=False)


def if_network_available(func):
    """Decorator to disable an action when network is not avaibable"""

    @wraps(func)
    def wrapper(*args, **kwargs):

        window = args[0].parent if hasattr(args[0], 'parent') else args[0].window
        if not window.network_available:
            window.show_notification(_('You are currently offline'))
            return None

        return func(*args, **kwargs)

    return wrapper


def is_flatpak():
    return os.path.exists(os.path.join(GLib.get_user_runtime_dir(), 'flatpak-info'))


def log_error_traceback(e):
    from komikku.servers.exceptions import ServerException

    if isinstance(e, requests.exceptions.RequestException):
        return _('No Internet connection, timeout or server down')
    elif isinstance(e, ServerException):
        return e.message

    logger.info(traceback.format_exc())

    return None


def crop_pixbuf(pixbuf, src_x, src_y, width, height):
    pixbuf_cropped = Pixbuf.new(Colorspace.RGB, pixbuf.get_has_alpha(), 8, width, height)
    pixbuf.copy_area(src_x, src_y, width, height, pixbuf_cropped, 0, 0)

    return pixbuf_cropped


def scale_pixbuf_animation(pixbuf, width, height, preserve_aspect_ratio, loop=False, rate=15):
    if preserve_aspect_ratio:
        if width == -1:
            ratio = pixbuf.get_height() / height
            width = pixbuf.get_width() / ratio
        elif height == -1:
            ratio = pixbuf.get_width() / width
            height = pixbuf.get_height() / ratio

    if pixbuf.is_static_image():
        # Unanimated image
        return pixbuf.get_static_image().scale_simple(width, height, InterpType.BILINEAR)

    pixbuf_scaled = PixbufSimpleAnim.new(width, height, rate)
    pixbuf_scaled.set_loop(loop)

    _res, timeval = GLib.TimeVal.from_iso8601(datetime.datetime.utcnow().isoformat())
    iter = pixbuf.get_iter(timeval)

    pixbuf_scaled.add_frame(iter.get_pixbuf().scale_simple(width, height, InterpType.BILINEAR))
    while not iter.on_currently_loading_frame():
        timeval.add(iter.get_delay_time() * 1000)
        iter.advance(timeval)
        pixbuf_scaled.add_frame(iter.get_pixbuf().scale_simple(width, height, InterpType.BILINEAR))

    return pixbuf_scaled


def skip_past(haystack, needle):
    if (idx := haystack.find(needle)) >= 0:
        return idx + len(needle)

    return None


class Imagebuf:
    def __init__(self, path, buffer, width, height):
        self._buffer = buffer
        self.path = path
        self.width = width
        self.height = height
        self.animated = isinstance(buffer, bytes)

    @classmethod
    def new_from_file(cls, path):
        try:
            pixbuf = Pixbuf.new_from_file(path)
        except GLib.GError:
            return None

        format, width, height = Pixbuf.get_file_info(path)

        if 'image/gif' in format.get_mime_types():
            # In case of GIF images (probably animated), buffer is image raw data
            with open(path, 'rb') as fp:
                buffer = fp.read()
        else:
            buffer = pixbuf

        return cls(path, buffer, width, height)

    @classmethod
    def new_from_resource(cls, path):
        buffer = Pixbuf.new_from_resource(path)
        width = buffer.get_width()
        height = buffer.get_height()

        return cls(None, buffer, width, height)

    def _compute_borders_crop_bbox(self):
        # TODO: Add a slider in settings
        threshold = 225

        def lookup(x):
            return 255 if x > threshold else 0

        im = Image.open(self.path).convert('L').point(lookup, mode='1')
        bg = Image.new(im.mode, im.size, 255)

        return ImageChops.difference(im, bg).getbbox()

    def _get_pixbuf_from_bytes(self, width, height):
        loader = PixbufLoader.new()
        loader.set_size(width, height)
        loader.write(self._buffer)
        loader.close()

        animation = loader.get_animation()
        if animation.is_static_image():
            self.animated = False
            return animation.get_static_image()

        return animation

    def crop_borders(self):
        """"Crop white borders

        :return: New cropped Imagebuf or self if it can't be cropped
        """
        if self.animated or self.path is None:
            return self

        bbox = self._compute_borders_crop_bbox()

        # Crop is possible if computed bbox is included in pixbuf
        if bbox[2] - bbox[0] < self.width or bbox[3] - bbox[1] < self.height:
            pixbuf = crop_pixbuf(self._buffer, bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])

            return Imagebuf(self.path, pixbuf, pixbuf.get_width(), pixbuf.get_height())

        return self

    def get_pixbuf(self):
        if isinstance(self._buffer, bytes):
            return self._get_pixbuf_from_bytes(self.width, self.height)

        return self._buffer

    def get_scaled_pixbuf(self, width, height, preserve_aspect_ratio, hidpi_scale):
        if preserve_aspect_ratio:
            if width == -1:
                ratio = self.height / height
                width = self.width / ratio
            elif height == -1:
                ratio = self.width / width
                height = self.height / ratio

        if isinstance(self._buffer, bytes):
            return self._get_pixbuf_from_bytes(width, height)

        return self._buffer.scale_simple(width * hidpi_scale, height * hidpi_scale, InterpType.BILINEAR)


class CustomCredential(Credential):
    """Custom credentials implementation with an additional 'address' attribute"""

    def __init__(self, username, password, address=None):
        self._username = username
        self._password = password
        self._address = address

    @property
    def address(self):
        return self._address

    @property
    def password(self):
        return self._password

    @property
    def username(self):
        return self._username


class KeyringHelper:
    """Simple helper to store servers accounts credentials using Python keyring library"""

    appid = 'info.febvre.Komikku'

    def __init__(self, fallback_keyring='plaintext'):
        if not self.is_disabled and not self.has_recommended_backend:
            if fallback_keyring == 'plaintext':
                keyring.set_keyring(PlaintextKeyring())

    @property
    def has_recommended_backend(self):
        return self.keyring is not None and not isinstance(self.keyring, keyring.backends.fail.Keyring)

    @property
    def is_disabled(self):
        return hasattr(keyring.backends, 'null') and isinstance(self.keyring, keyring.backends.null.Keyring)

    @property
    def keyring(self):
        current_keyring_backend = keyring.get_keyring()

        if isinstance(current_keyring_backend, keyring.backends.chainer.ChainerBackend):
            # Search SecretService backend
            for backend in current_keyring_backend.backends:
                if isinstance(backend, keyring.backends.SecretService.Keyring):
                    return backend

            return None

        return current_keyring_backend

    def get(self, service):
        if self.is_disabled:
            return None

        if isinstance(self.keyring, keyring.backends.SecretService.Keyring):
            collection = self.keyring.get_preferred_collection()

            credential = None
            with closing(collection.connection):
                items = collection.search_items({'service': service})
                for item in items:
                    self.keyring.unlock(item)
                    username = item.get_attributes().get('username')
                    if username is None:
                        # Try to find username in 'login' attribute instead of 'username'
                        # Backward compatibility with the previous implementation which used libsecret
                        username = item.get_attributes().get('login')
                    if username:
                        credential = CustomCredential(username, item.get_secret().decode('utf-8'), item.get_attributes().get('address'))
        else:
            # Fallback on PlaintextKeyring
            credential = self.keyring.get_credential(service, None)

        if credential is None or credential.username is None:
            return None

        return credential

    def store(self, service, username, password, address=None):
        if self.is_disabled:
            return

        if isinstance(self.keyring, keyring.backends.SecretService.Keyring):
            # At this time, SecretService is the only backend that support a collection of items with arbitrary attributes
            # Known working implementations are:
            # - GNOME Keyring
            # - KeePassXC Secret Service integration (tested, work well)

            # Freedesktop.org Secret Service specification was written by both GNOME and KDE projects together
            # but it’s supported by the GNOME Keyring only
            # ksecretservice (https://community.kde.org/KDE_Utils/ksecretsservice) exists but is unfinished and seems unmaintained

            collection = self.keyring.get_preferred_collection()

            label = f'{self.appid}: {username}@{service}'
            attributes = {
                'application': self.appid,
                'service': service,
                'username': username,
            }
            if address is not None:
                attributes['address'] = address

            with closing(collection.connection):
                # Delete previous credential if exists
                items = collection.search_items({'service': service})
                for item in items:
                    item.delete()

                collection.create_item(label, attributes, password)
        else:
            # Fallback on PlaintextKeyring
            self.keyring.set_password(service, username, password, address)


class PlaintextKeyring(keyring.backend.KeyringBackend):
    """Simple File Keyring with no encryption

    Used as fallback when no Keyring backend is found
    """

    priority = 1

    def __init__(self):
        super().__init__()

    @property
    def filename(self):
        return os.path.join(self.folder, 'plaintext.keyring')

    @property
    def folder(self):
        return os.path.join(get_data_dir(), 'keyrings')

    def _read(self):
        if not os.path.exists(self.filename):
            return {}

        with open(self.filename, 'r') as fp:
            return json.load(fp)

    def _save(self, data):
        if not os.path.exists(self.folder):
            os.mkdir(self.folder)

        with open(self.filename, 'w+') as fp:
            return json.dump(data, fp, indent=2)

    def get_credential(self, service, username):
        data = self._read()
        if service in data:
            return CustomCredential(data[service]['username'], data[service]['password'], data[service].get('address'))
        return None

    def get_password(self, service, username):
        pass

    def set_password(self, service, username, password, address=None):
        data = self._read()
        data[service] = dict(
            username=username,
            password=password,
        )
        if address is not None:
            data[service]['address'] = address
        self._save(data)
