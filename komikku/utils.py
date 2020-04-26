# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import gi
import logging
import requests
import subprocess
import traceback

gi.require_version('Secret', '1')

from gi.repository import GLib
from gi.repository import Secret

SECRET_SCHEMA_NAME = 'info.febvre.Komikku'

logger = logging.getLogger()


def folder_size(path):
    res = subprocess.run(['du', '-sh', path], stdout=subprocess.PIPE, check=False)

    return res.stdout.split()[0].decode()


def log_error_traceback(e):
    if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return _('No Internet connection, timeout or server down')
    if isinstance(e, GLib.GError):
        return _('Failed to load image')

    logger.info(traceback.format_exc())

    return None


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
