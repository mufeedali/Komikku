# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import dateparser
import datetime
from functools import lru_cache
from gi.repository import GLib
import importlib
import inspect
import io
import magic
from operator import itemgetter
import os
import pickle
from PIL import Image
import pkgutil
import requests
from requests.adapters import TimeoutSauce
import struct

# https://www.localeplanet.com/icu/
LANGUAGES = dict(
    id='Bahasa Indonesia',
    cs='Čeština',
    de='Deutsch',
    en='English',
    es='Español',
    fr='Français',
    it='Italiano',
    nl='Nederlands',
    nb='Norsk Bokmål',
    pl='Polski',
    pt='Português',
    pt_BR='Português (Brasil)',
    ru='Русский',
    vi='Tiếng Việt',
    ja='日本語',
    ko='한국어',
    th='ไทย',
    zh_Hans='中文 (简体)',
    zh_Hant='中文 (繁體)',
)

REQUESTS_TIMEOUT = 5
SESSIONS = dict()

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/60'
USER_AGENT_MOBILE = 'Mozilla/5.0 (Linux; U; Android 4.1.1; en-gb; Build/KLP) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Safari/534.30'


class CustomTimeout(TimeoutSauce):
    def __init__(self, *args, **kwargs):
        if kwargs['connect'] is None:
            kwargs['connect'] = REQUESTS_TIMEOUT
        if kwargs['read'] is None:
            kwargs['read'] = REQUESTS_TIMEOUT * 3
        super().__init__(*args, **kwargs)


# Set requests timeout globally, instead of specifying ``timeout=..`` kwarg on each call
requests.adapters.TimeoutSauce = CustomTimeout


class Server:
    id = NotImplemented
    name = NotImplemented
    lang = NotImplemented
    status = 'enabled'
    logged_in = False

    base_url = None

    @property
    def logo_resource_path(self):
        return get_server_logo_resource_path_by_id(self.id)

    @property
    def session(self):
        return SESSIONS.get(self.id)

    @session.setter
    def session(self, value):
        SESSIONS[self.id] = value

    @property
    def sessions_dir(self):
        dir = os.path.join(get_cache_dir(), 'sessions')
        if not os.path.exists(dir):
            os.mkdir(dir)

        return dir

    def clear_session(self):
        file_path = os.path.join(self.sessions_dir, '{0}.pickle'.format(get_server_main_id_by_id(self.id)))
        if os.path.exists(file_path):
            os.unlink(file_path)

        del SESSIONS[self.id]

    def get_manga_cover_image(self, url):
        """
        Returns manga cover (image) content
        """
        if url is None:
            return None

        r = self.session_get(url, headers={'referer': self.base_url})
        if r is None:
            return None

        if r.status_code != 200:
            return None

        buffer = r.content
        mime_type = magic.from_buffer(buffer[:128], mime=True)

        if not mime_type.startswith('image'):
            return None

        if mime_type == 'image/webp':
            buffer = convert_webp_buffer(buffer)

        return buffer

    def load_session(self):
        file_path = os.path.join(self.sessions_dir, '{0}.pickle'.format(get_server_main_id_by_id(self.id)))
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'rb') as f:
            self.session = pickle.load(f)

    def save_session(self):
        file_path = os.path.join(self.sessions_dir, '{0}.pickle'.format(get_server_main_id_by_id(self.id)))
        with open(file_path, 'wb') as f:
            pickle.dump(self.session, f)

    def session_get(self, *args, **kwargs):
        try:
            r = self.session.get(*args, **kwargs)
        except Exception:
            raise

        return r

    def session_post(self, *args, **kwargs):
        try:
            r = self.session.post(*args, **kwargs)
        except Exception:
            raise

        return r


def convert_date_string(date, format=None):
    if format is not None:
        try:
            d = datetime.datetime.strptime(date, format)
        except Exception:
            d = dateparser.parse(date)
    else:
        d = dateparser.parse(date)

    return d.date()


# https://github.com/italomaia/mangarock.py/blob/master/mangarock/mri_to_webp.py
def convert_mri_data_to_webp_buffer(data):
    size_list = [0] * 4
    size = len(data)
    header_size = size + 7

    # little endian byte representation
    # zeros to the right don't change the value
    for i, byte in enumerate(struct.pack('<I', header_size)):
        size_list[i] = byte

    buffer = [
        82,  # R
        73,  # I
        70,  # F
        70,  # F
        size_list[0],
        size_list[1],
        size_list[2],
        size_list[3],
        87,  # W
        69,  # E
        66,  # B
        80,  # P
        86,  # V
        80,  # P
        56,  # 8
    ]

    for bit in data:
        buffer.append(101 ^ bit)

    return bytes(buffer)


def convert_webp_buffer(webp_buffer, format='JPEG'):
    image = Image.open(io.BytesIO(webp_buffer))

    buffer = io.BytesIO()
    image.convert('RGB').save(buffer, format)

    return buffer.getvalue()


def get_server_class_name_by_id(id):
    return id.split(':')[0].capitalize()


def get_server_dir_name_by_id(id):
    return id.split(':')[0]


def get_server_logo_resource_path_by_id(id):
    return '/info/febvre/Komikku/icons/ui/servers/{0}.ico'.format(get_server_main_id_by_id(id))


def get_server_main_id_by_id(id):
    return id.split(':')[0].split('_')[0]


def get_server_module_name_by_id(id):
    return id.split(':')[-1].split('_')[0]


@lru_cache(maxsize=None)
def get_cache_dir():
    cache_dir_path = GLib.get_user_cache_dir()

    # Check if inside flatpak sandbox
    is_flatpak = os.path.exists(os.path.join(GLib.get_user_runtime_dir(), 'flatpak-info'))
    if is_flatpak:
        return cache_dir_path

    cache_dir_path = os.path.join(cache_dir_path, 'komikku')
    if not os.path.exists(cache_dir_path):
        os.mkdir(cache_dir_path)

    return cache_dir_path


@lru_cache(maxsize=None)
def get_servers_list(include_disabled=False, order_by=('lang', 'name')):
    import komikku.servers

    def iter_namespace(ns_pkg):
        # Specifying the second argument (prefix) to iter_modules makes the
        # returned name an absolute name instead of a relative one. This allows
        # import_module to work without having to do additional modification to
        # the name.
        return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + '.')

    servers = []
    for finder, name, ispkg in iter_namespace(komikku.servers):
        module = importlib.import_module(name)
        for _name, obj in dict(inspect.getmembers(module)).items():
            if not hasattr(obj, 'id') or not hasattr(obj, 'name') or not hasattr(obj, 'lang'):
                continue

            if not include_disabled and obj.status == 'disabled':
                continue

            if inspect.isclass(obj) and obj.__module__.startswith('komikku.servers.'):
                servers.append(dict(
                    id=obj.id,
                    name=obj.name,
                    lang=obj.lang,
                    class_name=get_server_class_name_by_id(obj.id),
                    module=module,
                ))

    return sorted(servers, key=itemgetter(*order_by))


def search_duckduckgo(site, term):
    session = requests.Session()
    session.headers.update({'user-agent': USER_AGENT})

    params = dict(
        kd=-1,
        q=f'site:{site} {term}',
    )

    try:
        r = session.get('https://duckduckgo.com/lite', params=params)
    except Exception:
        raise

    soup = BeautifulSoup(r.content, 'html.parser')

    results = []
    for a_element in soup.find_all('a', class_='result-link'):
        results.append(dict(
            name=a_element.text.strip(),
            url=a_element.get('href'),
        ))

    return results


# https://github.com/Harkame/JapScanDownloader
def unscramble_image(scrambled_image, image_full_path):
    input_image = Image.open(scrambled_image)
    temp = Image.new('RGB', input_image.size)
    output_image = Image.new('RGB', input_image.size)

    for x in range(0, input_image.width, 200):
        col1 = input_image.crop((x, 0, x + 100, input_image.height))

        if x + 200 <= input_image.width:
            col2 = input_image.crop((x + 100, 0, x + 200, input_image.height))
            temp.paste(col1, (x + 100, 0))
            temp.paste(col2, (x, 0))
        else:
            col2 = input_image.crop((x + 100, 0, input_image.width, input_image.height))
            temp.paste(col1, (x, 0))
            temp.paste(col2, (x + 100, 0))

    for y in range(0, temp.height, 200):
        row1 = temp.crop((0, y, temp.width, y + 100))

        if y + 200 <= temp.height:
            row2 = temp.crop((0, y + 100, temp.width, y + 200))
            output_image.paste(row1, (0, y + 100))
            output_image.paste(row2, (0, y))
        else:
            row2 = temp.crop((0, y + 100, temp.width, temp.height))
            output_image.paste(row1, (0, y))
            output_image.paste(row2, (0, y + 100))

    os.remove(scrambled_image)

    output_image.save(image_full_path)
