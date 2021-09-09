# -*- coding: utf-8 -*-

# Copyright (C) 2021 Mariusz Kurek
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Mariusz Kurek <mariuszkurek@pm.me>

from bs4 import BeautifulSoup
import datetime
import requests

from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT


class Guya(Server):
    base_url: str
    manga_url: str
    api_manga_url: str
    api_page_url: str

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.api_manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        resp_data = r.json()

        data = initial_data.copy()
        data.update(dict(
            authors=[resp_data['author']],
            scanlators=list(resp_data['groups'].values()),
            genres=[],
            status=None,
            cover=self.base_url + resp_data['cover'],
            synopsis=BeautifulSoup(resp_data['description'], 'html.parser').text.strip() if resp_data['description'] else None,
            chapters=self.resolve_chapters(initial_data['slug']),
            server_id=self.id,
        ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        chapters = self.resolve_chapters(manga_slug)
        if not chapters:
            return None

        for chapter in chapters:
            if chapter['slug'] == chapter_slug:
                return chapter

        return None

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(self.api_page_url.format(manga_slug, chapter_slug, page['slug']))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['slug'].split('_')[0],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        return self.search('')

    def resolve_chapters(self, manga_slug):
        data = []

        r = self.session_get(self.api_manga_url.format(manga_slug))
        if r.status_code != 200:
            return None

        resp_data = r.json()
        groups = resp_data['groups']
        chapters = resp_data['chapters']

        for chapter_id, chapter in chapters.items():
            title = '#' + chapter_id
            if chapter['title']:
                title += ' - ' + chapter['title']

            for group_id, pages in chapter['groups'].items():
                data.append(dict(
                    slug=chapter['folder'] + '/' + group_id,
                    title=title,
                    pages=[dict(slug=slug, image=None) for slug in pages],
                    scanlators=[groups[group_id]],
                    date=datetime.date.fromtimestamp(chapter['release_date'][group_id]),
                ))

        return data

    def search(self, term):
        params = None
        r = self.session_get(self.base_url + '/api/get_all_series/', params=params)
        if r.status_code != 200:
            return None

        resp_data = r.json()
        results = []

        for name, item in resp_data.items():
            if term and term.casefold() not in name.casefold():
                continue

            # The only indicator of a series being in Polish on Magical Translators is slug ending with PL.
            if self.id == 'magicaltranslators_pl':
                if not item['slug'].endswith('-PL'):
                    continue

            results.append(dict(
                slug=item['slug'],
                name=name,
            ))

        return results
