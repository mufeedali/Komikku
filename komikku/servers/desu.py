# -*- coding: utf-8 -*-

# Copyright (C) 2020 GrownNed
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: GrownNed <grownned@gmail.com>

from datetime import datetime
import magic
import requests

from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = 'Desu'

headers = {
    'User-Agent': USER_AGENT,
}

class Desu(Server):
    id = 'desu'
    name = SERVER_NAME
    lang = 'ru'

    base_url = 'https://desu.me'
    api_manga_url = base_url + '/manga/api/{0}'
    api_chapter_url = base_url + '/manga/api/{0}/chapter/{1}'
    api_search_url = base_url + '/manga/api?limit=1&search='
    api_most_populars_url = base_url + '/manga/api?limit=32&order=popular'
    manga_url = base_url + '/manga/{0}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = headers

    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.api_manga_url.format(initial_data['slug']))
        if r is None or r.status_code != 200:
            return None

        resp_data = r.json()["response"]

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

        data['name'] = resp_data['russian']
        data['cover'] = resp_data['image']['original']
        data['scanlators'] = [t['name'] for t in resp_data['translators']]
        data['genres'] = [genre['russian'] for genre in resp_data['genres']]
        data['status'] = resp_data['status']
        data['synopsis'] = resp_data['description']

        for chapter in resp_data['chapters']['list']:
            data['chapters'].append(dict(
                slug=chapter['id'],
                title='#{0} - {1}'.format(chapter['ch'], chapter['title']),
                date=datetime.fromtimestamp(chapter['date']).date(),
            ))

        data['chapters'].reverse()

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data from API

        Currently, only pages are expected.
        """
        r = self.session_get(self.api_chapter_url.format(manga_slug, chapter_slug))
        if r is None or r.status_code != 200:
            return None

        resp_data = r.json()['response']

        data = dict(
            pages=[],
        )
        for page in resp_data['pages']['list']:
            data['pages'].append(dict(
                slug=page['page'],
                image=page['img'],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
        if r is None:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)
        image_name = page['image'].split('/')[-1]

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
        r = self.session_get(self.api_most_populars_url)
        if r is None or r.status_code != 200:
            return None

        resp_data = r.json()["response"]
        
        return [dict(slug=element['id'], name=element['russian']) for element in resp_data]

    def search(self, term):
        r = self.session_get(self.api_search_url + term)
        if r is None or r.status_code != 200:
            return None

        resp_data = r.json()["response"]

        return [dict(slug=element['id'], name=element['russian']) for element in resp_data]
