# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import magic
import requests
import textwrap

from komikku.servers import Server
from komikku.servers import USER_AGENT

server_id = 'peppercarrot'
server_name = 'Pepper&Carrot'
server_lang = 'en'


class Peppercarrot(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.peppercarrot.com'
    manga_url = base_url + '/{0}/'
    chapter_url = base_url + '/0_sources/episodes-v1.json'
    image_url = base_url + '/0_sources/{0}/low-res/{1}_{2}'
    cover_url = base_url + '/0_sources/0ther/artworks/low-res/2016-02-24_vertical-cover_remake_by-David-Revoy.jpg'

    synopsis = 'This is the story of the young witch Pepper and her cat Carrot in the magical world of Hereva. Pepper learns the magic of Chaosah, the magic of chaos, with his godmothers Cayenne, Thyme and Cumin. Other witches like Saffran, Coriander, Camomile and Schichimi learn magics that each have their specificities.'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content
        """
        r = self.session_get(self.manga_url.format(self.lang))
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            authors=['David Revoy', ],
            scanlators=[],
            genres=[],
            status='ongoing',
            synopsis=self.synopsis,
            chapters=[],
            server_id=self.id,
            cover=self.cover_url,
        ))

        # Chapters
        for index, element in enumerate(reversed(soup.find('div', class_='homecontent').find_all('figure'))):
            if 'notranslation' in element.get('class'):
                # Skipped not translated episodes
                continue

            data['chapters'].append(dict(
                slug=index,  # Fake slug, needed to find chapters info in episodes API service
                date=None,
                title=element.a.get('title'),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data using episodes API service

        Chapter slug is updated
        """
        r = self.session_get(self.chapter_url)
        if r is None:
            return None

        chapters_data = r.json()
        try:
            chapter_data = chapters_data[int(chapter_slug)]
        except Exception:
            for chapter_data in chapters_data:
                if chapter_data['name'] == chapter_slug:
                    break

        data = dict(
            slug=chapter_data['name'],  # real slug
            pages=[],
        )

        # Title page is first page
        data['pages'].append(dict(
            slug=chapter_data['pages']['title'],
            image=None,
        ))

        for key, page_name in chapter_data['pages'].items():
            if key == 'title':
                # Skipped title, cover and credits pages
                break

            data['pages'].append(dict(
                slug=page_name,
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(self.image_url.format(chapter_slug, self.lang, page['slug']))
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (page['slug'], r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(self.lang)

    def get_most_populars(self):
        return self.search()

    def search(self, term=None):
        return [dict(
            slug='',
            name='Pepper&Carrot',
        )]
