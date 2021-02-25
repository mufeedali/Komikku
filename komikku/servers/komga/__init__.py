# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# Komga is a free and open source media server for your comics, mangas, BDs and magazines.
# Homepage: https://komga.org

from datetime import datetime
import functools
import logging

from requests.auth import HTTPBasicAuth

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server

logger = logging.getLogger('komikku.servers.komga')


def is_ready(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        server = args[0]
        if server.base_url is not None and server.logged_in:
            return func(*args, **kwargs)
        else:
            if server.base_url is None:
                logger.warning('Server base_url is not defined. Please check server address in Settings')
            else:
                logger.warning('Server is not logged in. Please check credential in Settings')

            return None

    return wrapper


class Komga(Server):
    id = 'komga'
    name = 'Komga'
    lang = 'en'
    has_login = True
    sync = True

    base_url = None  # Customizable via the settings

    headers = {
        'User-Agent': 'Komikku Komga',
    }

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
    def api_chapter_read_progress(self):
        return self.api_base_url + '/books/{0}/read-progress'

    @property
    def api_chapters_url(self):
        return self.api_base_url + '/series/{0}/books?unpaged=true&media_status=READY'

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

    @is_ready
    def get_manga_data(self, initial_data):
        """
        Returns manga data using API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.api_manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        resp_data = r.json()
        metadata = resp_data['metadata']
        books_metadata = resp_data['booksMetadata']

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],  # not available
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = metadata['title']
        data['cover'] = self.api_cover_url.format(data['slug'])

        # Details
        data['authors'] = [author['name'] for author in books_metadata['authors']]
        data['genres'] = [genre.capitalize() for genre in metadata['genres']]
        if metadata['status'] == 'ENDED':
            data['status'] = 'complete'
        elif metadata['status'] == 'ABANDONED':
            data['status'] = 'suspended'
        else:
            # Ongoing and hiatus
            data['status'] = metadata['status'].lower()
        data['reading_mode'] = metadata['readingDirection'].lower().replace('_', '-')

        data['synopsis'] = metadata['summary'] or books_metadata['summary']

        # Chapters
        r = self.session_get(self.api_chapters_url.format(data['slug']))
        if r.status_code != 200:
            return data

        items = r.json()['content']
        last_read = initial_data.get('last_read')  # only provided when updating
        for item in items:
            chapter_data = dict(
                slug=item['id'],
                title='#{0} {1}'.format(item['metadata']['number'], item['metadata']['title'].replace('_', ' ')),
                date=convert_date_string(item['metadata']['lastModified'].split('T')[0], format='%Y-%m-%d'),
            )

            if item.get('readProgress'):
                last_modified = datetime.fromisoformat(item['readProgress']['lastModified'])
                if not last_read or last_modified > last_read:
                    last_read = last_modified
                    chapter_data.update(dict(
                        read=item['readProgress']['completed'],
                        last_page_read_index=item['readProgress']['page'] - 1,
                    ))

            data['chapters'].append(chapter_data)

        data['last_read'] = last_read

        return data

    @is_ready
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

    @is_ready
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

    @is_ready
    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        return self.search('')

    def login(self, username, password):
        try:
            r = self.session.get(self.api_base_url, auth=HTTPBasicAuth(username, password))
        except Exception:
            return False

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return False

        self.save_session()

        return True

    @is_ready
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

    @is_ready
    def update_chapter_read_progress(self, data, manga_slug, manga_name, chapter_slug, chapter_url):
        r = self.session_patch(self.api_chapter_read_progress.format(chapter_slug), json=data)

        return r.status_code == 204
