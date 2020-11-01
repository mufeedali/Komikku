# -*- coding: utf-8 -*-

# Copyright (C) 2020 JaskaranSM
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: JaskaranSM

import requests

from komikku.servers import get_buffer_mime_type
from komikku.servers import USER_AGENT
from komikku.servers import Server

SERVER_NAME = 'Readmanhwa'


class ReadmanhwaException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class Readmanhwa(Server):
    id = 'readmanhwa'
    name = SERVER_NAME
    lang = 'en'
    lang_code = 'english'
    is_nsfw = False

    base_url = 'https://www.readmanhwa.com'
    manga_url = base_url + '/'+ lang + '/webtoon/{0}' # slug
    api_base_url = base_url + '/api/'
    api_search_url = api_base_url + 'comics?page={0}&q={1}&sort=popularity&order=desc&duration=week'
    api_most_populars_url = api_base_url + 'comics?page={0}&q=&sort=popularity&order=desc&duration=week'
    api_manga_slug_url = api_base_url +'comics/{0}'
    api_manga_chapters_slug =  api_manga_slug_url + '/chapters' # slug
    api_manga_url = api_base_url + 'comics?page={0}&q={1}&sort=popularity&order=desc'
    api_manga_chapter_images = api_manga_slug_url + '/images' # chapter_url 

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def do_api_request(self, url):
        resp = self.session.get(url)
        mime = get_buffer_mime_type(resp.content)
        if 'html' in mime:
            raise ReadmanhwaException(resp.text)
        return resp.json()

    def get_popular_manga(self, page=1):
        return self.do_api_request(self.api_most_populars_url.format(page))

    def get_manga_chapters_slug(self, slug):
        return self.do_api_request(self.api_manga_chapters_slug.format(slug))

    def get_manga_title(self, title, page=1):
        return self.do_api_request(self.api_search_url.format(page, title))

    def get_manga_slug(self, slug):
        return self.do_api_request(self.api_manga_slug_url.format(slug))

    def get_manga_chapter_images(self, chapter_url):
        return self.do_api_request(self.api_manga_chapter_images.format(chapter_url)) 

    def get_manga_data(self, initial_data):
        """
        Returns manga data by Doing API Requests

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'
        try:
            manga = self.get_manga_slug(initial_data['slug'])
        except (ReadmanhwaException, Exception):
            return None
        if not manga.get('slug', False):
            return None
        try:
            chapters = self.get_manga_chapters_slug(manga['slug'])
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

        # Details & Synopsis
        data['status'] = manga['status']
        for genre in manga.get('tags',[]):
            data['genres'].append(genre.get('name',''))

        data['synopsis'] = manga['description']
        # Chapters
        for chapter in chapters:
            data['chapters'].append(dict(
                slug=chapter['slug'],
                title=chapter['name']
                ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data
        """
        try:
            images = self.get_manga_chapter_images(manga_slug + '/' + chapter_slug)
        except (ReadmanhwaException, Exception):
            return None

        data = dict(
            pages=[],
            scrambled=0,
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
        if r is None or r.status_code != 200:
            return None

        buffer = r.content
        mime_type = get_buffer_mime_type(buffer)
        if mime_type == 'application/octet-stream':
            buffer = convert_mri_data_to_webp_buffer(buffer)
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

    def get_most_populars(self):
        """
        Returns Popular Manga
        """
        try:
            resp = self.get_popular_manga()
        except (ReadmanhwaException,Exception):
            return None

        results = []
        for item in resp['data']:
            results.append(dict(
                name=item['title'],
                slug=item['slug'],
            ))

        return results

    def search(self, term):
        """
        Returns Manga by search
        """
        try:
            resp = self.get_manga_title(term)
        except (ReadmanhwaException,Exception):
            return None
        results = []
        for manga in resp['data']:
            results.append(dict(
                    name=manga['title'],
                    slug=manga['slug'],
            ))

        return results
