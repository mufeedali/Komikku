# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import cloudscraper
import json
import magic
from requests.exceptions import ConnectionError

from mangascan.servers import convert_mri_data_to_webp_buffer
from mangascan.servers import convert_webp_buffer
from mangascan.servers import user_agent

server_id = 'mangarock'
server_name = 'Manga Rock'
server_lang = 'en'

scraper = None
headers = {
    'User-Agent': user_agent,
    'Origin': 'https://mangarock.com',
}


class Mangarock():
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://mangarock.com'
    api_url = 'https://api.mangarockhd.com/query/web401'
    api_search_url = api_url + '/mrs_search?country='
    api_manga_url = api_url + '/info?oid={0}&last=0'
    # api_chapter_url = api_url + '/pages?oid={0}'
    api_chapter_url = api_url + '/pagesv2?oid={0}'
    manga_url = base_url + '/manga/{0}'

    def __init__(self):
        global scraper

        if scraper is None:
            scraper = cloudscraper.create_scraper()
            scraper.headers.update(headers)

    def get_manga_data(self, initial_data):
        """
        Returns manga data

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        try:
            r = scraper.get(self.api_manga_url.format(initial_data['slug']))
        except ConnectionError:
            return None

        try:
            res = r.json()
        except json.decoder.JSONDecodeError:
            return None

        if res['code'] != 0:
            return None

        res = res['data']
        data = initial_data.copy()
        data.update(dict(
            authors=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            cover=None,
            server_id=self.id,
        ))

        # Name & cover
        data['name'] = res['name']
        data['cover'] = res['thumbnail']

        # Details & Synopsis
        for author in res['authors']:
            data['authors'].append('{0} ({1})'.format(author['name'], author['role']))
        for genre in res['rich_categories']:
            data['genres'].append(genre['name'])
        data['status'] = 'complete' if res['completed'] else 'ongoing'
        data['synopsis'] = res['description']

        # Chapters
        for chapter in res['chapters']:
            data['chapters'].append(dict(
                slug=chapter['oid'],
                date=None,
                title=chapter['name'],
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        url = self.api_chapter_url.format(chapter_slug)

        try:
            r = scraper.get(url)
        except ConnectionError:
            return None

        try:
            res = r.json()
        except json.decoder.JSONDecodeError:
            return None

        data = dict(
            pages=[],
            scrambled=0,
        )

        if res['code'] == 0:
            for page in res['data']:
                data['pages'].append(dict(
                    slug=None,  # not necessary, we know image url already
                    image=page['url'],
                ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        image_url = page['image']
        try:
            r = scraper.get(image_url)
        except ConnectionError:
            return (None, None)

        if r.status_code != 200:
            return (None, None)

        image_name = image_url.split('/')[-1]
        buffer = r.content
        mime_type = magic.from_buffer(r.content[:128], mime=True)
        if mime_type == 'application/octet-stream':
            buffer = convert_mri_data_to_webp_buffer(buffer)
            return (image_name, convert_webp_buffer(buffer))
        elif mime_type.startswith('image'):
            return (image_name, buffer)
        else:
            return (None, None)

    def get_manga_cover_image(self, cover_path):
        """
        Returns manga cover (image) content
        """
        try:
            r = scraper.get(cover_path)
        except ConnectionError:
            return None

        if r.status_code != 200:
            return None

        buffer = r.content
        mime_type = magic.from_buffer(buffer[:128], mime=True)
        if mime_type.startswith('image'):
            if mime_type == 'image/webp':
                buffer = convert_webp_buffer(buffer)

            return buffer
        else:
            return None

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def search(self, term):
        try:
            r = scraper.post(self.api_search_url, json={'type': 'series', 'keywords': term})
        except ConnectionError:
            return None

        if r.status_code == 200:
            try:
                res = r.json()
            except json.decoder.JSONDecodeError:
                return None

            if res['code'] != 0:
                return None

            # Returned data for each manga:
            # oid: slug of the manga
            results = []
            for oid in res['data']:
                data = self.get_manga_data(dict(slug=oid))
                if data:
                    results.append(dict(
                        name=data['name'],
                        slug=data['slug'],
                    ))

            return results
        else:
            return None
