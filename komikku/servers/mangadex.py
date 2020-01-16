# -*- coding: utf-8 -*-

# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
from datetime import datetime
import html
import magic
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT

GENRES = {
    '2': 'Action',
    '3': 'Adventure',
    '5': 'Comedy',
    '8': 'Drama',
    '10': 'Fantasy',
    '13': 'Historical',
    '14': 'Horror',
    '17': 'Mecha',
    '18': 'Medical',
    '20': 'Mystery',
    '22': 'Psychological',
    '23': 'Romance',
    '25': 'Sci-Fi',
    '28': 'Shoujo Ai',
    '30': 'Shounen Ai',
    '31': 'Slice of Life',
    '33': 'Sports',
    '35': 'Tragedy',
    '37': 'Yaoi',
    '38': 'Yuri',
    '41': 'Isekai',
    '51': 'Crime',
    '52': 'Magical Girls',
    '53': 'Philosophical',
    '54': 'Superhero',
    '55': 'Thriller',
    '56': 'Wuxia',
}
LANGUAGES_CODES = dict(
    en='gb',
    es='es',
    fr='fr',
)
SERVER_NAME = 'MangaDex'

headers = {
    'User-Agent': USER_AGENT,
    'Host': 'mangadex.org',
    'Referer': 'https://mangadex.org',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,en-US;q=0.7,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
}


class Mangadex(Server):
    id = 'mangadex'
    name = SERVER_NAME
    lang = 'en'

    base_url = 'https://mangadex.org'
    api_manga_url = base_url + '/api/manga/{0}'
    api_chapter_url = base_url + '/api/chapter/{0}'
    search_url = base_url + '/search'
    most_populars_url = base_url + '/titles/7'
    manga_url = base_url + '/title/{0}'
    chapter_url = base_url + '/chapter/{0}'
    page_url = base_url + '/chapter/{0}/{1}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = headers

    @staticmethod
    def manga_id_from_slug(slug):
        return slug.split('/')[0]

    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(
            self.api_manga_url.format(self.manga_id_from_slug(initial_data['slug'])),
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': '*/*',
                'Referer': self.base_url,
                'Origin': self.base_url,
            }
        )
        if r is None or r.status_code != 200:
            return None

        resp_data = r.json()

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        data['name'] = resp_data['manga']['title']
        data['cover'] = '{0}{1}'.format(self.base_url, resp_data['manga']['cover_url'])

        data['authors'] += [t.strip() for t in resp_data['manga']['author'].split(',')]
        data['authors'] += [t.strip() for t in resp_data['manga']['artist'].split(',') if t.strip() not in data['authors']]
        data['genres'] = [GENRES[str(genre_id)] for genre_id in resp_data['manga']['genres'] if str(genre_id) in GENRES]

        if resp_data['manga']['status'] == 1:
            data['status'] = 'ongoing'
        elif resp_data['manga']['status'] == 2:
            data['status'] = 'complete'
        elif resp_data['manga']['status'] == 3:
            data['status'] = 'suspended'
        elif resp_data['manga']['status'] == 4:
            data['status'] = 'hiatus'

        data['synopsis'] = html.unescape(resp_data['manga']['description'])

        for slug, chapter in resp_data['chapter'].items():
            if LANGUAGES_CODES.get(self.lang) != chapter['lang_code']:
                continue
            if chapter['group_id'] == 9097:
                # Chapters from MANGA Plus can be read from MangaDex
                continue
            if datetime.fromtimestamp(chapter['timestamp']) > datetime.utcnow():
                # Future chapter
                continue

            data['chapters'].append(dict(
                slug=slug,
                title='#{0} - {1}'.format(chapter['chapter'], chapter['title']),
                date=datetime.fromtimestamp(chapter['timestamp']).date(),
            ))

        data['chapters'].reverse()

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data from API

        Currently, only pages are expected.
        """
        r = self.session_get(
            self.api_chapter_url.format(chapter_slug),
            headers={
                'Accept': '*/*',
                'Referer': self.chapter_url.format(chapter_slug),
            }
        )
        if r is None or r.status_code != 200:
            return None

        resp_data = r.json()

        data = dict(
            pages=[],
        )
        for page in resp_data['page_array']:
            data['pages'].append(dict(
                slug=None,
                image='{0}{1}/{2}'.format(resp_data['server'], resp_data['hash'], page),
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'], headers={
            'Accept': 'image/webp,image/*;q=0.8,*/*;q=0.5',
            'Referer': self.page_url.format(chapter_slug, 1),
        })
        if r is None:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)
        image_name = page['image'].split('?')[0].split('/')[-1]

        return (image_name, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns most popular mangas (bayesian rating)
        """
        r = self.session_get(self.most_populars_url)
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for element in soup.find_all('a', class_='manga_title'):
            results.append(dict(
                slug=element.get('href').replace('/title/', ''),
                name=element.text.strip(),
            ))

        return results

    def search(self, term):
        r = self.session_get(self.search_url, params=dict(
            tag_mode_exc='any',
            tag_mode_inc='all',
            title=term,
            s=2,
        ))
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for element in soup.find_all('a', class_='manga_title'):
            results.append(dict(
                slug=element.get('href').replace('/title/', ''),
                name=element.text.strip(),
            ))

        return results


class Mangadex_es(Mangadex):
    id = 'mangadex_es'
    name = SERVER_NAME
    lang = 'es'


class Mangadex_fr(Mangadex):
    id = 'mangadex_fr'
    name = SERVER_NAME
    lang = 'fr'
