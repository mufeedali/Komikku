# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import datetime
from gettext import gettext as _
import gi
import logging
from PIL import Image
from PIL import ImageChops
import requests
import subprocess
import traceback

gi.require_version('Secret', '1')

from gi.repository import GLib
from gi.repository import Secret
from gi.repository.GdkPixbuf import Colorspace
from gi.repository.GdkPixbuf import InterpType
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GdkPixbuf import PixbufLoader
from gi.repository.GdkPixbuf import PixbufSimpleAnim

SECRET_SCHEMA_NAME = 'info.febvre.Komikku'

logger = logging.getLogger()


def folder_size(path):
    res = subprocess.run(['du', '-sh', path], stdout=subprocess.PIPE, check=False)

    return res.stdout.split()[0].decode()


def log_error_traceback(e):
    if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ChunkedEncodingError)):
        return _('No Internet connection, timeout or server down')

    logger.info(traceback.format_exc())

    return None


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
        self.animated = False

    @classmethod
    def new_from_file(cls, path):
        try:
            pixbuf = Pixbuf.new_from_file(path)
        except GLib.GError:
            return None

        format, width, height = Pixbuf.get_file_info(path)

        if 'image/gif' in format.get_mime_types():
            # In case of GIF images, buffer is image raw data
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
            return animation.get_static_image()

        self.animated = True

        return animation

    def crop_borders(self):
        if not isinstance(self._buffer, Pixbuf) or self.path is None:
            return self

        bbox = self._compute_borders_crop_bbox()

        # Crop is possible if computed bbox is included in pixbuf
        if bbox[2] - bbox[0] < self.width or bbox[3] - bbox[1] < self.height:
            pixbuf = Pixbuf.new(Colorspace.RGB, self._buffer.get_has_alpha(), 8, bbox[2] - bbox[0], bbox[3] - bbox[1])
            self._buffer.copy_area(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1], pixbuf, 0, 0)

            return Imagebuf(self.path, pixbuf, pixbuf.get_width(), pixbuf.get_height())

        return self

    def get_pixbuf(self):
        if isinstance(self._buffer, bytes):
            return self._get_pixbuf_from_bytes(self.width, self.height)

        return self._buffer

    def get_scaled_pixbuf(self, width, height, preserve_aspect_ratio):
        if preserve_aspect_ratio:
            if width == -1:
                ratio = self.height / height
                width = self.width / ratio
            elif height == -1:
                ratio = self.width / width
                height = self.height / ratio

        if isinstance(self._buffer, bytes):
            return self._get_pixbuf_from_bytes(width, height)

        return self._buffer.scale_simple(width, height, InterpType.BILINEAR)


# Heavily adapted from PasswordsHelper class of Lollypop music player
# https://gitlab.gnome.org/World/lollypop/-/blob/master/lollypop/helper_passwords.py
class SecretAccountHelper:
    """
        Simple helper to store servers accounts credentials using libsecret
    """

    def __init__(self):
        """
            Init helper
        """
        self.__secret = None
        Secret.Service.get(Secret.ServiceFlags.NONE, None, self.__on_get_secret)

    def get(self, service, callback, *args):
        """
        Call function
        @param service as str
        @param callback as function
        @param args
        """
        try:
            self.__wait_for_secret(self.get, service, callback, *args)
            SecretSchema = {
                "service": Secret.SchemaAttributeType.STRING
            }
            attributes = {
                "service": service
            }
            schema = Secret.Schema.new(SECRET_SCHEMA_NAME, Secret.SchemaFlags.NONE, SecretSchema)
            self.__secret.search(
                schema,
                attributes,
                Secret.SearchFlags.ALL,
                None,
                self.__on_secret_search,
                service,
                callback,
                *args
            )
        except Exception as e:
            logger.debug("SecretAccountHelper::get(): %s", e)

    def store(self, service, login, password, callback, *args):
        """
            Store password
            @param service as str
            @param login as str
            @param password as str
            @param callback as function
        """
        try:
            self.__wait_for_secret(self.store,
                                   service,
                                   login,
                                   password,
                                   callback,
                                   *args)
            schema_string = f'{SECRET_SCHEMA_NAME}: {service}@{login}'
            SecretSchema = {
                "service": Secret.SchemaAttributeType.STRING,
                "login": Secret.SchemaAttributeType.STRING,
            }
            attributes = {
                "service": service,
                "login": login
            }
            schema = Secret.Schema.new(SECRET_SCHEMA_NAME,
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            Secret.password_store(schema, attributes,
                                  Secret.COLLECTION_DEFAULT,
                                  schema_string,
                                  password,
                                  None,
                                  callback,
                                  *args)
        except Exception as e:
            logger.debug("SecretAccountHelper::store(): %s", e)

    def clear(self, service, callback=None, *args):
        """
            Clear password
            @param service as str
            @param callback as function
        """
        try:
            self.__wait_for_secret(self.clear, service, callback, *args)
            SecretSchema = {
                "service": Secret.SchemaAttributeType.STRING
            }
            attributes = {
                "service": service
            }
            schema = Secret.Schema.new(SECRET_SCHEMA_NAME,
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            self.__secret.search(schema,
                                 attributes,
                                 Secret.SearchFlags.ALL,
                                 None,
                                 self.__on_clear_search,
                                 callback,
                                 *args)
        except Exception as e:
            logger.debug("SecretAccountHelper::clear(): %s", e)

    #######################
    # PRIVATE             #
    #######################
    def __wait_for_secret(self, call, *args):
        """
            Wait for secret
            @param call as function to call
            @param args
            @raise exception if waiting
        """
        # Wait for secret
        if self.__secret is None:
            GLib.timeout_add(250, call, *args)
            raise Exception("Waiting Secret service")
        if self.__secret == -1:
            raise Exception("Error waiting for Secret service")

    @staticmethod
    def __on_clear_search(source, result, callback=None, *args):
        """
            Clear passwords
            @param source as GObject.Object
            @param result as Gio.AsyncResult
        """
        try:
            if result is not None:
                items = source.search_finish(result)
                for item in items:
                    item.delete(None, None)
            if callback is not None:
                callback(*args)
        except Exception as e:
            logger.debug("SecretAccountHelper::__on_clear_search(): %s", e)

    @staticmethod
    def __on_load_secret(source, result, service, callback, *args):
        """
            Set userservice/password input
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param service as str
            @param index as int
            @param count as int
            @param callback as function
            @param args
        """
        secret = source.get_secret()
        if secret is not None:
            callback(source.get_attributes(),
                     secret.get().decode('utf-8'),
                     service,
                     *args)
        else:
            logger.debug("SecretAccountHelper: no secret!")
            callback(None, None, service, *args)

    def __on_secret_search(self, source, result, service, callback, *args):
        """
            Set userservice/password input
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param service as str/None
            @param callback as function
            @param args
        """
        try:
            if result is not None:
                items = source.search_finish(result)
                for item in items:
                    item.load_secret(None,
                                     self.__on_load_secret,
                                     service,
                                     callback,
                                     *args)
                if not items:
                    logger.debug("SecretAccountHelper: no items!")
                    callback(None, None, service, *args)
            else:
                logger.debug("SecretAccountHelper: no result!")
                callback(None, None, service, *args)
        except Exception as e:
            logger.debug("SecretAccountHelper::__on_secret_search(): %s", e)
            callback(None, None, service, *args)

    def __on_get_secret(self, source, result):
        """
            Store secret proxy
            @param source as GObject.Object
            @param result as Gio.AsyncResult
        """
        try:
            self.__secret = source.get_finish(result)
        except Exception as e:
            self.__secret = -1
            logger.debug("SecretAccountHelper::__on_get_secret(): %s", e)
