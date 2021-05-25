# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
from functools import lru_cache
import html
import logging
from uuid import UUID

from komikku.servers import convert_date_string
from komikku.servers import do_login
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.utils import skip_past

logger = logging.getLogger('komikku.servers.mangadex')


SERVER_NAME = 'MangaDex'


CHAPTERS_PER_REQUEST = 100
AUTHORS_PER_REQUEST = 100
SCANLATORS_PER_REQUEST = 100


class Mangadex(Server):
    id = 'mangadex'
    name = SERVER_NAME
    lang = 'en'
    lang_code = 'en'
    long_strip_genres = ['Long Strip', ]
    has_login = True
    session_expiration_cookies = ['mangadex_rememberme_token', ]

    base_url = 'https://mangadex.org'
    action_url = base_url + '/ajax/actions.ajax.php?function={0}'
    api_base_url = 'https://api.mangadex.org'
    api_manga_url = api_base_url + '/manga/{0}'
    api_chapter_url = api_base_url + '/chapter/{0}'
    api_author_url = api_base_url + '/author/{0}'
    api_cover_url = api_base_url + '/cover/{0}'
    api_scanlator_url = api_base_url + '/group/{0}'
    api_server_url = api_base_url + '/at-home/server/{0}'
    api_page_url = '{0}/data/{1}'

    most_populars_url = base_url + '/titles?s=7'
    manga_url = base_url + '/title/{0}'
    chapter_url = base_url + '/chapter/{0}'
    page_url = base_url + '/chapter/{0}/{1}'
    cover_url = 'https://uploads.mangadex.org/covers/{0}/{1}'

    headers = {
        'User-Agent': USER_AGENT,
        'Host': api_base_url.split('/')[2],
        'Referer': base_url,
    }

    def __init__(self, username=None, password=None):
        if username and password:
            self.do_login(username, password)

    def convert_old_slug(self, slug):
        # Removing this will break manga that were added before the change to the manga slug
        slug = slug.split('/')[0]
        try:
            return str(UUID(slug, version=4))
        except ValueError:
            r = self.session_post(self.api_base_url + '/legacy/mapping', json={
                'type': 'manga',
                'ids': [int(slug)],
            })
            if r.status_code != 200:
                return None
            for result in r.json():
                if str(result['data']['attributes']['legacyId']) == slug:
                    return result['data']['attributes']['newId']

    @staticmethod
    def get_group_name(group_id, groups_list):
        """Get group name from group id."""
        matching_group = [group for group in groups_list if group['id'] == group_id]
        return matching_group[0]['name']


    def list_authors(self, authors):
        if authors == []:
            return []
        r = self.session_get(self.api_author_url.format(''), params={'ids[]': authors})
        if r.status_code != 200:
            return None
        return [result['data']['attributes']['name'] for result in r.json()['results']]

    def get_cover(self, manga_slug, cover):
        r = self.session_get(self.api_cover_url.format(cover))
        if r.status_code != 200:
            return None
        result = r.json()
        return self.cover_url.format(manga_slug, result['data']['attributes']['fileName'])

    def resolve_scanlators(self, chapter_or_chapters, scanlators):
        if scanlators == []:
            return chapter_or_chapters
        r = self.session_get(self.api_scanlator_url.format(''), params={'ids[]': scanlators})
        if r.status_code != 200:
            return None
        remap = {result['data']['id']: result['data']['attributes']['name'] for result in r.json()['results']}

        if isinstance(chapter_or_chapters, list):
            chapters = chapter_or_chapters
        else:
            chapters = [chapter_or_chapters]

        for chapter in chapters:
            chapter['scanlators'] = [
                remap[scanlator] if scanlator in remap else scanlator for scanlator in chapter['scanlators']
            ]
        return chapter_or_chapters

    def list_chapters(self, manga_slug):
        offset=0
        chapters = []
        scanlators = set()
        while True:
            r = self.session_get(self.api_chapter_url.format(''), params={
                'manga': manga_slug,
                'translatedLanguage[]': [self.lang_code],
                'limit': CHAPTERS_PER_REQUEST,
                'offset': offset
            })
            if r.status_code == 204:
                break
            elif r.status_code != 200:
                return None
            results = r.json()['results']

            for chapter in results:
                attributes = chapter['data']['attributes']
                data=dict(
                    slug=chapter['data']['id'],
                    title='#{0} - {1}'.format(attributes['chapter'], attributes['title']),
                    pages=[dict(slug=attributes['hash']+'/'+page, image=None)
                           for page in attributes['data']],
                    date=convert_date_string(attributes['publishAt']),
                    scanlators=[])
                rel_scanlators = [rel['id'] for rel in chapter['relationships'] if rel['type'] == 'scanlation_group']
                scanlators.update(rel_scanlators)
                data['scanlators'] = rel_scanlators
                chapters.append(data)

            if len(results) < CHAPTERS_PER_REQUEST:
                break
            offset += CHAPTERS_PER_REQUEST

        scanlators = list(scanlators)
        for n in range(0, len(scanlators), SCANLATORS_PER_REQUEST):
            chapters = self.resolve_scanlators(chapters, scanlators[n:n + SCANLATORS_PER_REQUEST])

        return chapters

    @do_login
    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        new_slug = self.convert_old_slug(initial_data['slug'])

        r = self.session_get(self.api_manga_url.format(new_slug))
        if r.status_code != 200:
            return None

        resp_json = r.json()

        data = initial_data.copy()
        data.update(dict(
            slug=new_slug,
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        attributes = resp_json['data']['attributes']

        # FIXME: Should probably be lang_code, but the API returns weird stuff
        data['name'] = html.unescape(attributes['title']['en'])
        data['cover'] = None # not yet supported
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

        # FIXME: lang_code
        data['synopsis'] = html.unescape(attributes['description']['en'])

        rel_authors = []

        for relationship in resp_json['relationships']:
            if relationship['type'] == 'author':
                rel_authors.append(relationship['id'])
            elif relationship['type'] == 'cover_art':
                data['cover'] = self.get_cover(data['slug'], relationship['id'])

        for n in range(0, len(rel_authors), AUTHORS_PER_REQUEST):
            data['authors'] += self.list_authors(rel_authors[n:n + AUTHORS_PER_REQUEST])

        data['chapters'] += self.list_chapters(data['slug'])

        return data

    @do_login
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data from API

        Currently, only pages are expected.
        """
        r = self.session_get(
            self.api_chapter_url.format(chapter_slug),
            headers={
                'Host': self.api_base_url.split('/')[2],
                'Referer': self.chapter_url.format(chapter_slug),
            }
        )
        if r.status_code != 200:
            return None

        resp_json = r.json()
        attributes = resp_json['data']['attributes']

        data = dict(
            slug=chapter_slug,
            title='#{0} - {1}'.format(attributes['chapter'], attributes['title']),
            pages=[dict(slug=attributes['hash']+'/'+page, image=None)
                   for page in attributes['data']],
            date=convert_date_string(attributes['publishAt']),
            scanlators=[rel['id'] for rel in resp_json['relationships'] if rel['type'] == 'scanlation_group']
        )

        for n in range(0, len(data['scanlators']), SCANLATORS_PER_REQUEST):
            data = self.resolve_scanlators(data, data['scanlators'][n:n + SCANLATORS_PER_REQUEST])

        return data

    @lru_cache(maxsize=1)
    def get_server_url(self, chapter_slug):
        r = self.session_get(self.api_server_url.format(chapter_slug))
        if r.status_code != 200:
            return None
        return r.json()['baseUrl']

    @do_login
    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        server_url = self.get_server_url(chapter_slug)
        if server_url == None:
            self.get_server_url.cache_clear()
            return None

        r = self.session_get(self.api_page_url.format(server_url, page['slug']),
                             headers={
                                 'Accept': 'image/webp,image/*;q=0.8,*/*;q=0.5',
                                 'Referer': self.page_url.format(chapter_slug, 1),
                             })

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

    def login(self, username, password):
        r = self.session_post(
            self.action_url.format('login'),
            data={
                'login_username': username,
                'login_password': password,
                'remember_me': '1',
            },
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': '*/*',
                'Referer': 'https://mangadex.org/login',
                'Origin': 'https://mangadex.org'
            }
        )

        if r.text != '':
            return False

        self.save_session()

        return True

    @do_login
    def search(self, term):
        r = self.session_get(self.api_manga_url.format(''), params=dict(
            title=term,
        ))
        if r.status_code != 200:
            return None

        results = []
        for result in r.json()['results']:
            if result['result'] != 'ok':
                continue
            result = result['data']
            if result['type'] != 'manga':
                continue
            results.append(dict(
                slug=result['id'],
                # FIXME: lang_code
                name=result['attributes']['title']['en']
            ))

        return results


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
