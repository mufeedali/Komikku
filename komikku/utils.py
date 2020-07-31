# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from contextlib import closing
import datetime
from functools import lru_cache
from gettext import gettext as _
import gi
import html
import json
import keyring
from keyring.credentials import SimpleCredential
import logging
import os
from PIL import Image
from PIL import ImageChops
import requests
import subprocess
import traceback

gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Secret', '1')

from gi.repository import GLib
from gi.repository import Secret
from gi.repository.GdkPixbuf import Colorspace
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GdkPixbuf import PixbufLoader
from gi.repository.GdkPixbuf import PixbufSimpleAnim

logger = logging.getLogger()


def folder_size(path):
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


def is_flatpak():
    return os.path.exists(os.path.join(GLib.get_user_runtime_dir(), 'flatpak-info'))


def log_error_traceback(e):
    if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ChunkedEncodingError)):
        return _('No Internet connection, timeout or server down')

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


class KeyringHelper:
    """Simple helper to store servers accounts credentials using Python keyring library"""

    appid = 'info.febvre.Komikku'

    def __init__(self, fallback_keyring='plaintext'):
        if not self.is_disabled and not self.has_recommended_backend:
            if fallback_keyring == 'plaintext':
                keyring.set_keyring(PlaintextKeyring())

    @property
    def has_recommended_backend(self):
        return not isinstance(self.keyring, keyring.backends.fail.Keyring)

    @property
    def is_disabled(self):
        return hasattr(keyring.backends, 'null') and isinstance(self.keyring, keyring.backends.null.Keyring)

    @property
    def keyring(self):
        return keyring.get_keyring()

    def get(self, service):
        if self.is_disabled:
            return None

        credential = self.keyring.get_credential(service, None)

        if isinstance(self.keyring, keyring.backends.SecretService.Keyring) and credential and credential.username is None:
            # Try to find username in 'login' attribute instead of 'username'
            # Backward compatibility with the previous implementation which used libsecret
            collection = self.keyring.get_preferred_collection()

            with closing(collection.connection):
                items = collection.search_items({'service': service})
                for item in items:
                    self.keyring.unlock(item)
                    username = item.get_attributes().get('login')
                    if username:
                        credential = SimpleCredential(username, item.get_secret().decode('utf-8'))

        if credential is None or credential.username is None:
            return None

        return credential

    def store(self, service, username, password):
        if self.is_disabled:
            return

        if isinstance(self.keyring, keyring.backends.SecretService.Keyring):
            collection = self.keyring.get_preferred_collection()
            label = f'{self.appid}: {username}@{service}'
            attributes = {
                'application': self.appid,
                'service': service,
                'username': username,
            }
            with closing(collection.connection):
                collection.create_item(label, attributes, password, replace=True)
        else:
            keyring.set_password(service, username, password)


class PlaintextKeyring(keyring.backend.KeyringBackend):
    """Simple File Keyring with no encryption

    Used as fallback when no Keyring backend is found
    """

    folder = os.path.join(get_data_dir(), 'keyrings')
    filename = os.path.join(folder, 'plaintext.keyring')
    priority = 1

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
            return SimpleCredential(data[service]['username'], data[service]['password'])
        else:
            return None

    def get_password(self, service, username):
        pass

    def set_password(self, service, username, password):
        data = self._read()
        data[service] = dict(
            username=username,
            password=password,
        )
        self._save(data)


class SecretAccountHelper:
    """Simple helper to store servers accounts credentials using libsecret"""

    schema_name = 'info.febvre.Komikku'

    def __init__(self):
        self.__secret_service = None
        Secret.Service.get(Secret.ServiceFlags.NONE, None, self.__on_get_secret_service)

    def __on_get_secret_service(self, source, result):
        """Store secret service

        :param GObject.Object source: the source object
        :param Gio.AsyncResult result: the result
        """
        try:
            self.__secret_service = source.get_finish(result)
        except Exception as e:
            self.__secret_service = -1
            logger.error('SecretAccountHelper::__on_get_secret_service(): %s', e)

    def __wait_for_secret_service(self, callback, *args):
        """Wait for secret service

        :param callable callback: called when the waiting ends
        :param args: params to be passed to the callback
        :raises exception: if waiting fails
        """
        if self.__secret_service is None:
            GLib.timeout_add(250, callback, *args)
        if self.__secret_service == -1:
            raise Exception('Error waiting for Secret service')

    def clear(self, service, callback=None, *args):
        """Clear password

        :param str service: the service
        :param callable callback: called when the operation completes
        :param args: params to be passed to the callback
        """
        try:
            self.__wait_for_secret_service(self.clear, service, callback, *args)
            if self.__secret_service is None:
                return

            def on_password_clear(source, result):
                Secret.password_clear_finish(result)
                if callback is not None:
                    callback(*args)

            attributes_names_and_types = {
                'service': Secret.SchemaAttributeType.STRING
            }
            attributes = {
                'service': service
            }
            schema = Secret.Schema.new(self.schema_name, Secret.SchemaFlags.NONE, attributes_names_and_types)
            Secret.password_clear(schema, attributes, None, on_password_clear)
        except Exception as e:
            logger.debug('SecretAccountHelper::clear(): %s', e)

    def get(self, service, callback, *args):
        """Get password

        :param str service: the service
        :param callable callback: called when the operation completes
        :param args: params to be passed to the callback
        """
        try:
            self.__wait_for_secret_service(self.get, service, callback, *args)
            if self.__secret_service is None:
                return

            def on_password_search(source, result):
                items = Secret.password_search_finish(result)
                if items:
                    def on_retrieve_secret(item, result):
                        secret = item.retrieve_secret_finish(result)
                        callback(item.get_attributes(), secret.get_text(), service, *args)

                    item = items[0]
                    item.retrieve_secret(None, on_retrieve_secret)

            attributes_names_and_types = {
                'service': Secret.SchemaAttributeType.STRING
            }
            attributes = {
                'service': service
            }
            schema = Secret.Schema.new(self.schema_name, Secret.SchemaFlags.NONE, attributes_names_and_types)
            Secret.password_search(schema, attributes, Secret.SearchFlags.ALL, None, on_password_search)
        except Exception as e:
            logger.debug('SecretAccountHelper::get(): %s', e)

    def store(self, service, login, password, callback):
        """Store password

        :param str service: the service
        :param str login: the login
        :param str password: the password
        :param callable callback: called when the operation completes
        """
        try:
            self.__wait_for_secret_service(self.store, callback, service, login, password, callback)
            if self.__secret_service is None:
                return

            def on_password_store(source, result):
                callback(source, result)

            label = f'{self.schema_name}: {service}@{login}'
            attributes_names_and_types = {
                'service': Secret.SchemaAttributeType.STRING,
                'login': Secret.SchemaAttributeType.STRING
            }
            attributes = {
                'service': service,
                'login': login
            }
            schema = Secret.Schema.new(self.schema_name, Secret.SchemaFlags.NONE, attributes_names_and_types)
            Secret.password_store(schema, attributes, Secret.COLLECTION_DEFAULT, label, password, None, on_password_store)
        except Exception as e:
            logger.debug('SecretAccountHelper::store(): %s', e)
