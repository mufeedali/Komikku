# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# Komga is a free and open source media server for your comics, mangas, BDs and magazines.

from requests.auth import HTTPBasicAuth

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT

headers = {
    'User-Agent': USER_AGENT,
}


class Komga(Server):
    id = 'komga'
    name = 'Komga'
    lang = 'en'
    has_login = True

    base_url = None  # Customizable via the settings

    def __init__(self, username=None, password=None, address=None):
        if address:
            self.base_url = address

        self.init(username, password)

    @property
    def api_base_url(self):
        return self.base_url + '/api/v1'

    @property
    def api_chapter_page_url(self):
        return self.api_base_url + '/books/{0}/pages/{1}'

    @property
    def api_chapter_pages_url(self):
        return self.api_base_url + '/books/{0}/pages'

    @property
    def api_chapters_url(self):
        return self.api_base_url + '/series/{0}/books'

    @property
    def api_cover_url(self):
        return self.api_base_url + '/series/{0}/thumbnail'

    @property
    def api_manga_url(self):
        return self.api_base_url + '/series/{0}'

    @property
    def api_search_url(self):
        return self.api_base_url + '/series'

    @property
    def manga_url(self):
        return self.base_url + '/series/{0}'

    def get_manga_data(self, initial_data):
        """
        Returns manga data using API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.api_manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        resp_data = r.json()['metadata']

        data = initial_data.copy()
        data.update(dict(
            authors=[],     # not available
            scanlators=[],  # not available
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = resp_data['title']
        data['cover'] = self.api_cover_url.format(data['slug'])

        # Details
        data['genres'] = [genre.capitalize() for genre in resp_data['genres']]
        if resp_data['status'] == 'ENDED':
            data['status'] = 'complete'
        elif resp_data['status'] == 'ABANDONED':
            data['status'] = 'suspended'
        else:
            # Ongoing and hiatus
            data['status'] = resp_data['status'].lower()

        data['synopsis'] = resp_data['summary']

        # Chapters
        r = self.session_get(self.api_chapters_url.format(data['slug']))
        if r.status_code != 200:
            return data

        resp_data = r.json()['content']

        for item in resp_data:
            data['chapters'].append(dict(
                slug=item['id'],
                title='#{0} {1}'.format(item['metadata']['number'], item['metadata']['title'].replace('_', ' ')),
                date=convert_date_string(item['metadata']['lastModified'].split('T')[0], format='%Y-%m-%d'),
                read=item['readProgress']['completed'],
                last_page_read_index=item['readProgress']['page'],
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data

        Currently, only pages are expected.
        """
        r = self.session_get(self.api_chapter_pages_url.format(chapter_slug))
        if r.status_code != 200:
            return None

        data = dict(
            pages=[],
        )
        for item in r.json():
            data['pages'].append(dict(
                slug=item['number'],
                image=item['fileName'].split('/')[-1],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(self.api_chapter_page_url.format(chapter_slug, page['slug']))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['image'],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        return self.search('')

    def login(self, username, password):
        r = self.session.get(self.api_base_url, auth=HTTPBasicAuth(username, password))

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        self.save_session()

        return True

    def search(self, term):
        r = self.session.get(self.api_search_url, params=dict(search=term))
        if r.status_code != 200:
            return None

        results = []
        term = term.lower()
        for item in r.json()['content']:
            results.append(dict(
                name=item['name'],
                slug=item['id'],
            ))

        return results
