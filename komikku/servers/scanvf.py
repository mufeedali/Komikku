# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import cloudscraper
import magic
from requests.exceptions import ConnectionError

from komikku.servers import Server

server_id = 'scanvf'
server_name = 'Scanvf'
server_lang = 'fr'


class Scanvf(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://scanvf.com'
    search_url = base_url + '/search.php'
    manga_url = base_url + '/{0}'
    chapter_url = base_url + '/{0}'
    page_url = base_url + '/{0}/{1}'
    image_url = base_url + '/{0}'
    cover_url = base_url + '/photos/{}.png'

    def __init__(self):
        if self.session is None:
            self.session = cloudscraper.create_scraper()

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        try:
            r = self.session.get(self.manga_url.format(initial_data['slug']))
        except (ConnectionError, RuntimeError):
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

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

        data['cover'] = self.cover_url.format(data['slug'].replace('mangas-', ''))

        # Details
        elements = soup.find_all('div', class_='col-md-9')[0].find_all('p')
        for element in elements:
            label = element.span.extract().text.strip()
            value = element.text[3:].strip()

            if label.startswith('Auteur'):
                data['authors'] = [value, ]
            elif label.startswith('Statu'):
                # possible values: ongoing, complete
                data['status'] = 'ongoing' if value.lower() == 'en cours' else 'complete'
            elif label.startswith('synopsis'):
                data['synopsis'] = value

        # Chapters
        elements = soup.find_all('div', class_='list-group')[0].find_all('a', recursive=False)
        for element in reversed(elements):
            element.i.extract()

            slug = element.get('href').split('/')[-1]
            title = element.text.strip().replace('Scan ', '')

            data['chapters'].append(dict(
                slug=slug,
                title=title,
                date=None,
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        url = self.chapter_url.format(chapter_slug)

        try:
            r = self.session.get(url)
        except (ConnectionError, RuntimeError):
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        options_elements = soup.find_all('select')[2].find_all('option')

        data = dict(
            pages=[],
        )
        for option_element in options_elements:
            data['pages'].append(dict(
                slug=option_element.get('value').strip().split('/')[-1],
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        # Scrap HTML page to get image path
        url = self.page_url.format(chapter_slug, page['slug'])

        try:
            r = self.session.get(url)
        except (ConnectionError, RuntimeError):
            return (None, None)

        soup = BeautifulSoup(r.text, 'lxml')
        path = soup.find('img', class_='img-fluid').get('src')
        imagename = url.split('/')[-1]

        # Get scan image
        r = self.session.get(self.image_url.format(path))
        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (imagename, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_cover_image(self, url):
        """
        Returns manga cover (image) content
        """
        try:
            r = self.session.get(url)
        except (ConnectionError, RuntimeError):
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return r.content if r.status_code == 200 and mime_type.startswith('image') else None

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def search(self, term):
        try:
            self.session.get(self.base_url)

            r = self.session.get(self.search_url, params=dict(key=term, send='Recherche'))
        except (ConnectionError, RuntimeError):
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        a_elements = soup.find('div', class_='col-lg-8').find_all('a')
        for a_element in a_elements:
            results.append(dict(
                slug=a_element.get('href'),
                name=a_element.text,
            ))

        return results
