# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from functools import lru_cache
import html
import logging
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from uuid import UUID

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers.exceptions import NotFoundError

logger = logging.getLogger('komikku.servers.mangadex')

SERVER_NAME = 'MangaDex'

CHAPTERS_PER_REQUEST = 100
SEARCH_RESULTS_LIMIT = 100


class Mangadex(Server):
    id = 'mangadex'
    name = SERVER_NAME
    lang = 'en'
    lang_code = 'en'
    long_strip_genres = ['Long Strip', ]

    base_url = 'https://mangadex.org'
    api_base_url = 'https://api.mangadex.org'
    api_manga_base = api_base_url + '/manga'
    api_manga_url = api_manga_base + '/{0}'
    api_chapter_base = api_base_url + '/chapter'
    api_chapter_url = api_chapter_base + '/{0}'
    api_author_base = api_base_url + '/author'
    api_cover_url = api_base_url + '/cover/{0}'
    api_scanlator_base = api_base_url + '/group'
    api_server_url = api_base_url + '/at-home/server/{0}'
    api_page_url = '{0}/data/{1}'

    manga_url = base_url + '/title/{0}'
    cover_url = 'https://uploads.mangadex.org/covers/{0}/{1}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

            retry = Retry(total=5, backoff_factor=1, respect_retry_after_header=False, status_forcelist=Retry.RETRY_AFTER_STATUS_CODES)
            self.session.mount(self.api_base_url, HTTPAdapter(max_retries=retry))

    @staticmethod
    def get_group_name(group_id, groups_list):
        """Get group name from group id"""
        matching_group = [group for group in groups_list if group['id'] == group_id]

        return matching_group[0]['name']

    def convert_old_slug(self, slug, type):
        # Removing this will break manga that were added before the change to the manga slug
        slug = slug.split('/')[0]
        try:
            return str(UUID(slug, version=4))
        except ValueError:
            r = self.session_post(self.api_base_url + '/legacy/mapping', json={
                'type': type,
                'ids': [int(slug)],
            })
            if r.status_code != 200:
                return None

            for result in r.json():
                if result['result'] == 'ok' and str(result['data']['attributes']['legacyId']) == slug:
                    return result['data']['attributes']['newId']

            return None

    def _manga_title_from_attributes(self, attributes):
        if self.lang_code in attributes['title']:
            return attributes['title'][self.lang_code]
        elif 'en' in attributes['title']:
            return attributes['title']['en']

        else:
            lang_code_alt_name = None
            en_alt_name = None

            for alt_title in attributes['altTitles']:
                if not lang_code_alt_name and self.lang_code in alt_title:
                    lang_code_alt_name = alt_title['en']

                if not en_alt_name and 'en' in alt_title:
                    en_alt_name = alt_title['en']

            return lang_code_alt_name or en_alt_name

    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        slug = self.convert_old_slug(initial_data['slug'], type='manga')
        if slug is None:
            raise NotFoundError

        r = self.session_get(self.api_manga_url.format(slug), params={'includes[]': ['author', 'artist', 'cover_art']})
        if r.status_code != 200:
            return None

        resp_json = r.json()

        data = initial_data.copy()
        data.update(dict(
            slug=slug,
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            cover=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        attributes = resp_json['data']['attributes']

        # FIXME: Should probably be lang_code, but the API returns weird stuff
        _name = self._manga_title_from_attributes(attributes)
        data['name'] = html.unescape(_name)
        assert data['name'] is not None

        for relationship in resp_json['relationships']:
            if relationship['type'] == 'author':
                data['authors'].append(relationship['attributes']['name'])
            elif relationship['type'] == 'cover_art':
                data['cover'] = self.cover_url.format(slug, relationship['attributes']['fileName'])

        # FIXME: Same lang_code weirdness
        data['genres'] = [tag['attributes']['name']['en'] for tag in attributes['tags']]

        if attributes['status'] == 'ongoing':
            data['status'] = 'ongoing'
        elif attributes['status'] == 'completed':
            data['status'] = 'complete'
        elif attributes['status'] == 'cancelled':
            data['status'] = 'suspended'
        elif attributes['status'] == 'hiatus':
            data['status'] = 'hiatus'

        if self.lang_code in attributes['description']:
            data['synopsis'] = self._clean(attributes['description'][self.lang_code])
        elif 'en' in attributes['description']:
            # Fall back to english synopsis
            data['synopsis'] = self._clean(attributes['description']['en'])
        else:
            logger.warning('{}: No synopsis', data['name'])

        data['chapters'] += self.resolve_chapters(data['slug'])

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data from API

        Currently, only pages are expected.
        """
        r = self.session_get(self.api_chapter_url.format(chapter_slug), params={'includes[]': ['scanlation_group']})
        if r.status_code == 404:
            raise NotFoundError
        if r.status_code != 200:
            return None

        resp_json = r.json()

        attributes = resp_json['data']['attributes']
        title = f'#{attributes["chapter"]}'
        if attributes['title']:
            title = f'{title} - {attributes["title"]}'

        scanlators = [rel['attributes']['name'] for rel in resp_json['relationships'] if rel['type'] == 'scanlation_group']
        data = dict(
            slug=chapter_slug,
            title=title,
            pages=[dict(slug=attributes['hash'] + '/' + page, image=None) for page in attributes['data']],
            date=convert_date_string(attributes['publishAt'].split('T')[0], format='%Y-%m-%d'),
            scanlators=scanlators
        )

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        server_url = self.get_server_url(chapter_slug)
        if server_url is None:
            self.get_server_url.cache_clear()
            return None

        r = self.session_get(self.api_page_url.format(server_url, page['slug']))
        if r.status_code != 200:
            self.get_server_url.cache_clear()
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['slug'].split('/')[1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        return self.search('')

    @lru_cache(maxsize=1)
    def get_server_url(self, chapter_slug):
        r = self.session_get(self.api_server_url.format(chapter_slug))
        if r.status_code != 200:
            return None

        return r.json()['baseUrl']

    def resolve_chapters(self, manga_slug):
        chapters = []
        offset = 0
        scanlators = set()

        while True:
            r = self.session_get(self.api_chapter_base, params={
                'manga': manga_slug,
                'translatedLanguage[]': [self.lang_code],
                'limit': CHAPTERS_PER_REQUEST,
                'offset': offset,
                'includes[]': ['scanlation_group']
            })
            if r.status_code == 204:
                break
            if r.status_code != 200:
                return None

            results = r.json()['results']

            for chapter in results:
                attributes = chapter['data']['attributes']

                title = f'#{attributes["chapter"]}'
                if attributes['title']:
                    title = f'{title} - {attributes["title"]}'

                scanlators = [rel['attributes']['name'] for rel in chapter['relationships'] if rel['type'] == 'scanlation_group']

                data = dict(
                    slug=chapter['data']['id'],
                    title=title,
                    pages=[dict(slug=attributes['hash'] + '/' + page, image=None) for page in attributes['data']],
                    date=convert_date_string(attributes['publishAt'].split('T')[0], format='%Y-%m-%d'),
                    scanlators=scanlators,
                )
                chapters.append(data)

            if len(results) < CHAPTERS_PER_REQUEST:
                break
            offset += CHAPTERS_PER_REQUEST

        return chapters

    def search(self, term):
        params = dict(
            limit=SEARCH_RESULTS_LIMIT,
        )
        if term:
            params['title'] = term

        r = self.session_get(self.api_manga_base, params=params)
        if r.status_code != 200:
            return None

        results = []
        for result in r.json()['results']:
            if result['result'] != 'ok':
                continue

            result = result['data']
            if result['type'] != 'manga':
                continue

            name = self._manga_title_from_attributes(result['attributes'])

            if name:
                results.append(dict(
                    slug=result['id'],
                    # FIXME: lang_code
                    name=name,
                ))
            else:
                logger.warning("ignoring result {}, missing name".format(result['id']))

        return results

    @staticmethod
    def _clean(text):
        # HTML escaping
        text = html.unescape(text)

        parsing_dict = {
            # Pango escaping.
            # TODO: Check if more characters need escaping.
            r'&': r'&amp;',
            r'<': r'&lt;',
            r'>': r'&gt;',

            # bold, italic, underline, strikethrough, subscript, superscript
            r'\[\s*b\s*\]': r'<b>',
            r'\[\s*/b\s*\]': r'</b>',

            r'\[\s*i\s*\]': r'<i>',
            r'\[\s*/i\s*\]': r'</i>',

            r'\[\s*u\s*\]': r'<u>',
            r'\[\s*/u\s*\]': r'</u>',

            r'\[\s*s\s*\]': r'<s>',
            r'\[\s*/s\s*\]': r'</s>',

            r'\[\s*sub\s*\]': r'<sub>',
            r'\[\s*/sub\s*\]': r'</sub>',

            r'\[\s*sup\s*\]': r'<sup>',
            r'\[\s*/sup\s*\]': r'</sup>',

            # There's no "highlight" in Pango. Make it italic instead and pray it's somewhat suitable.
            r'\[\s*h\s*\]': r'<i>',
            r'\[\s*/h\s*\]': r'</i>',

            # Same deal with quotes.
            r'\[\s*quote\s*\]': r'<tt>',
            r'\[\s*/quote\s*\]': r'</tt>',

            # There's no equivalent to "code" either, but at least make it monospace.
            r'\[\s*code\s*\]': r'<tt>',
            r'\[\s*/code\s*\]': r'</tt>',

            # links
            r'\[\s*url=([^ \]]*)\s*\]': r'<a href="\1">',
            r'\[\s*/url\s*\]': r'</a>',

            # Remove images. (I don't think they're supported in descriptions anyway.)
            r'\[\s*img\s*\](.*)\[\s*/img\s*\]': r'',

            # Remove tags for left, right, center, justify, headings, rule, lists, etc.
            r'\[\s*left\s*\]': r'',
            r'\[\s*/left\s*\]': r'',

            r'\[\s*right\s*\]': r'',
            r'\[\s*/right\s*\]': r'',

            r'\[\s*center\s*\]': r'',
            r'\[\s*/center\s*\]': r'',

            r'\[\s*justify\s*\]': r'',
            r'\[\s*/justify\s*\]': r'',

            r'\[\s*h\d\s*\]': r'',
            r'\[\s*/h\d\s*\]': r'',

            r'\[\s*hr\s*\]': '',
            r'\[\s*/hr\s*\]': '',

            r'\[\s*list\s*\]': '',
            r'\[\s*/list\s*\]': '',

            r'\[\s*ul\s*\]': '',
            r'\[\s*/ul\s*\]': '',

            r'\[\s*ol\s*\]': '',
            r'\[\s*/ol\s*\]': '',

            r'\[\s*\*\s*\]': '- ',
        }

        for key, value in parsing_dict.items():
            text = re.sub(key, value, text, flags=re.IGNORECASE | re.DOTALL)

        spoiler_matches = re.finditer(r'\[\s*spoiler\s*\](.*)\[\s*/spoiler\s*\]', text, flags=re.IGNORECASE | re.DOTALL)
        for match in spoiler_matches:
            captured_group = html.escape(match.group(1))
            captured_group = re.sub('<[^<]+?>', '', captured_group)
            text = text.replace(match.group(0), f'<a title="{captured_group}" href="#">SPOILER</a>')

        return text


class Mangadex_cs(Mangadex):
    id = 'mangadex_cs'
    name = SERVER_NAME
    lang = 'cs'
    lang_code = 'cz'


class Mangadex_de(Mangadex):
    id = 'mangadex_de'
    name = SERVER_NAME
    lang = 'de'
    lang_code = 'de'


class Mangadex_es(Mangadex):
    id = 'mangadex_es'
    name = SERVER_NAME
    lang = 'es'
    lang_code = 'es'


class Mangadex_fr(Mangadex):
    id = 'mangadex_fr'
    name = SERVER_NAME
    lang = 'fr'
    lang_code = 'fr'


class Mangadex_id(Mangadex):
    id = 'mangadex_id'
    name = SERVER_NAME
    lang = 'id'
    lang_code = 'id'


class Mangadex_it(Mangadex):
    id = 'mangadex_it'
    name = SERVER_NAME
    lang = 'it'
    lang_code = 'it'


class Mangadex_ja(Mangadex):
    id = 'mangadex_ja'
    name = SERVER_NAME
    lang = 'ja'
    lang_code = 'jp'


class Mangadex_ko(Mangadex):
    id = 'mangadex_ko'
    name = SERVER_NAME
    lang = 'ko'
    lang_code = 'kr'


class Mangadex_nl(Mangadex):
    id = 'mangadex_nl'
    name = SERVER_NAME
    lang = 'nl'
    lang_code = 'nl'


class Mangadex_pl(Mangadex):
    id = 'mangadex_pl'
    name = SERVER_NAME
    lang = 'pl'
    lang_code = 'pl'


class Mangadex_pt(Mangadex):
    id = 'mangadex_pt'
    name = SERVER_NAME
    lang = 'pt'
    lang_code = 'pt'


class Mangadex_pt_br(Mangadex):
    id = 'mangadex_pt_br'
    name = SERVER_NAME
    lang = 'pt_BR'
    lang_code = 'pt-br'


class Mangadex_ru(Mangadex):
    id = 'mangadex_ru'
    name = SERVER_NAME
    lang = 'ru'
    lang_code = 'ru'


class Mangadex_th(Mangadex):
    id = 'mangadex_th'
    name = SERVER_NAME
    lang = 'th'
    lang_code = 'th'


class Mangadex_vi(Mangadex):
    id = 'mangadex_vi'
    name = SERVER_NAME
    lang = 'vi'
    lang_code = 'vn'


class Mangadex_zh_hans(Mangadex):
    id = 'mangadex_zh_hans'
    name = SERVER_NAME
    lang = 'zh_Hans'
    lang_code = 'cn'


class Mangadex_zh_hant(Mangadex):
    id = 'mangadex_zh_hant'
    name = SERVER_NAME
    lang = 'zh_Hant'
    lang_code = 'hk'
