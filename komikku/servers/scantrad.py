# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import dateparser
from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError
from urllib.parse import urlsplit

from komikku.servers import Server
from komikku.servers import USER_AGENT

server_id = 'scantrad'
server_name = 'Scantrad France'
server_lang = 'fr'


class Scantrad(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.scantrad.fr'
    search_url = base_url + '/mangas'
    manga_url = base_url + '/{0}'
    chapter_url = base_url + '/mangas/{0}/{1}'
    page_url = base_url + '/mangas/{0}/{1}?{2}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        try:
            r = self.session.get(self.manga_url.format(initial_data['slug']))
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

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

        data['name'] = soup.find('h1').text.strip()
        data['synopsis'] = soup.find('div', class_='synopsis').text.strip()

        # Chapters
        for li_element in soup.find('ul', id='project-chapters-list').find_all('li'):
            title_element = li_element.find('div', class_='name-chapter')
            number_element = title_element.span.extract()

            data['chapters'].append(dict(
                slug=li_element.find('div', class_='buttons').find_all('a')[0].get('href').split('/')[-1],
                date=dateparser.parse(li_element.find('span', class_='chapter-date').text).date(),
                title='{0} {1}'.format(number_element.text.strip(), title_element.text.strip()),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        url = self.chapter_url.format(manga_slug, chapter_slug)

        try:
            r = self.session.get(url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        pages_options_elements = soup.find('div', class_='controls').find_all('select')[2].find_all('option')

        data = dict(
            pages=[],
        )
        for option_element in pages_options_elements:
            data['pages'].append(dict(
                slug=option_element.get('value').split('?')[-1],
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        try:
            r = self.session.get(self.page_url.format(manga_slug, chapter_slug, page['slug']))
        except ConnectionError:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return (None, None)

        soup = BeautifulSoup(r.text, 'html.parser')

        image_url = soup.find('div', class_='image').find('a').img.get('src')
        image_name = image_url.split('/')[-1]

        try:
            r = self.session.get(image_url)
        except (ConnectionError, RuntimeError):
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (image_name, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_cover_image(self, url):
        """
        Returns manga cover (image) content
        """
        return None

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def search(self, term):
        try:
            r = self.session.get(self.search_url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for li_element in soup.find('ul', id='projects-list').find_all('li'):
            name = li_element.a.find_all('span')[0].text.strip()

            if name.lower().find(term.lower()) >= 0:
                results.append(dict(
                    slug=li_element.a.get('href').split('/')[-1],
                    name=li_element.a.find_all('span')[0].text.strip(),
                ))

        return results
