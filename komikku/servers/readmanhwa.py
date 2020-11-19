# -*- coding: utf-8 -*-

# Copyright (C) 2020 JaskaranSM
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: JaskaranSM

from gettext import gettext as _
import requests

from komikku.models import Settings
from komikku.servers import get_buffer_mime_type
from komikku.servers import USER_AGENT
from komikku.servers import Server

SERVER_NAME = 'ReadManhwa'


class ReadmanhwaException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class Readmanhwa(Server):
    id = 'readmanhwa'
    name = SERVER_NAME
    lang = 'en'
    long_strip_genres = ['Webtoons', ]

    base_url = 'https://www.readmanhwa.com'
    manga_url = base_url + '/' + lang + '/webtoon/{0}'

    api_base_url = base_url + '/api/'
    api_search_url = api_base_url + 'comics?q={0}&per_page=20&nsfw={1}'
    api_most_populars_url = api_base_url + 'comics?page=1&q=&sort=popularity&order=desc&duration=year&nsfw={0}'
    api_manga_url = api_base_url + 'comics/{0}?nsfw=true'
    api_manga_chapters_url = api_base_url + 'comics/{0}/chapters?nsfw=true'
    api_manga_chapter_images_url = api_base_url + 'comics/{0}/{1}/images?nsfw=true'

    filters = [
        {
            'key': 'nsfw',
            'type': 'checkbox',
            'name': _('NSFW Content'),
            'description': _('Whether to show manga containing NSFW content'),
            'default': False,
        },
    ]

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

        # Update NSFW filter default value according to current settings
        if Settings.instance:
            self.filters[0]['default'] = Settings.get_default().nsfw_content

    def do_api_request(self, url):
        resp = self.session.get(url, headers={'X-Requested-With': 'XMLHttpRequest'})
        if get_buffer_mime_type(resp.content) != 'text/plain':
            raise ReadmanhwaException(resp.text)

        return resp.json()

    def get_manga_data(self, initial_data):
        """
        Returns manga data using API requests

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'
        try:
            manga = self.do_api_request(self.api_manga_url.format(initial_data['slug']))
        except (ReadmanhwaException, Exception):
            return None

        if not manga.get('slug', False):
            return None

        try:
            chapters = self.do_api_request(self.api_manga_chapters_url.format(manga['slug']))
        except (ReadmanhwaException, Exception):
            return None

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        # Name & cover
        data['name'] = manga['title']
        data['cover'] = manga['thumb_url']

        # Authors & Artists
        for author in manga['authors']:
            data['authors'].append(author['name'])
        for artist in manga['artists']:
            if artist['name'] not in data['authors']:
                data['authors'].append(artist['name'])

        # Status
        if manga['status'] == 'canceled':
            data['status'] = 'suspended'
        elif manga['status'] == 'onhold':
            data['status'] = 'hiatus'
        else:
            data['status'] = manga['status']

        # Genres
        for genre in manga.get('tags', []):
            data['genres'].append(genre['name'])

        data['synopsis'] = manga['description']

        # Chapters
        for chapter in reversed(chapters):
            data['chapters'].append(dict(
                slug=chapter['slug'],
                title=chapter['name'],
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data
        """
        try:
            images = self.do_api_request(self.api_manga_chapter_images_url.format(manga_slug, chapter_slug))
        except (ReadmanhwaException, Exception):
            return None

        data = dict(
            pages=[],
        )
        for image in images['images']:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url already
                image=image['source_url'],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
        if r.status_code != 200:
            return None

        buffer = r.content
        mime_type = get_buffer_mime_type(buffer)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=buffer,
            mime_type=mime_type,
            name=page['image'].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self, nsfw):
        """
        Returns Popular Manga
        """
        try:
            resp = self.do_api_request(self.api_most_populars_url.format('true' if nsfw else 'false'))
        except (ReadmanhwaException, Exception):
            return None

        results = []
        for item in resp['data']:
            results.append(dict(
                name=item['title'],
                slug=item['slug'],
            ))

        return results

    def search(self, term, nsfw):
        """
        Returns Manga by search
        """
        try:
            resp = self.do_api_request(self.api_search_url.format(term, 'true' if nsfw else 'false'))
        except (ReadmanhwaException, Exception):
            return None

        results = []
        for manga in resp['data']:
            results.append(dict(
                name=manga['title'],
                slug=manga['slug'],
            ))

        return results
