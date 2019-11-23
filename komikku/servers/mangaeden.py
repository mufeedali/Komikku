# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import json
from collections import OrderedDict
from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError

from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT

server_id = 'mangaeden'
server_name = 'Manga Eden'
server_lang = 'en'

headers = OrderedDict(
    [
        ('User-Agent', USER_AGENT),
        ('Accept-Language', 'en-US,en;q=0.5'),
    ]
)


class Mangaeden(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'http://www.mangaeden.com'
    search_url = base_url + '/en/en-directory/'
    popular_url = search_url + '?order=1'
    manga_url = base_url + '/en/en-manga/{0}/'
    chapter_url = base_url + '/en/en-manga/{0}/{1}/1/'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = headers

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

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

        data['name'] = soup.find('span', class_='manga-title').text.strip()

        cover_element = soup.find('div', class_='mangaImage2')
        if cover_element:
            data['cover'] = 'https:{0}'.format(cover_element.img.get('src'))

        # Details
        for element in soup.find_all('div', class_='rightBox')[1].find_all():
            if element.name == 'h4':
                label = element.text.strip()

                if label.startswith(('Status', 'Stato')):
                    status = element.find_all_next(string=True, limit=2)[1].strip().lower()

                    if status in ('ongoing', 'in corso'):
                        data['status'] = 'ongoing'
                    elif status in ('completed', 'completato'):
                        data['status'] = 'complete'
                    elif status in ('suspended', 'sospeso'):
                        data['status'] = 'suspended'

                continue

            if element.name == 'a':
                if label.startswith(('Author', 'Autore', 'Artist', 'Artista')):
                    data['authors'].append(element.text.strip())
                elif label.startswith(('Genres', 'Genere')):
                    data['genres'].append(element.text.strip())

        # Synopsis
        synopsis_element = soup.find('h2', id='mangaDescription')
        if synopsis_element:
            data['synopsis'] = synopsis_element.text.strip()

        # Chapters
        elements = soup.find('table').tbody.find_all('tr')
        for element in reversed(elements):
            tds_elements = element.find_all('td')

            data['chapters'].append(dict(
                slug=tds_elements[0].a.get('href').split('/')[-3],
                title=tds_elements[0].b.text.strip(),
                date=convert_date_string(tds_elements[3].text.strip(), format='%b %d, %Y'),
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
        scripts_elements = soup.find_all('script')

        data = dict(
            pages=[],
        )
        for script_element in scripts_elements:
            script = script_element.text.strip()
            if script.startswith('var pages'):
                pages = json.loads(script.split('\n')[0].split('=')[1][:-1])
                for page in pages:
                    data['pages'].append(dict(
                        slug=None,  # not necessary, we know image url already
                        image='https:{0}'.format(page['fs']),
                    ))
                break

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        try:
            r = self.session.get(page['image'])
        except ConnectionError:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)
        imagename = page['image'].split('/')[-1]

        return (imagename, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_popular(self):
        """
        Returns most viewed manga list
        """
        try:
            r = self.session.get(self.popular_url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for tr_element in soup.find('table', id='mangaList').tbody.find_all('tr'):
            td_elements = tr_element.find_all('td')
            a_element = td_elements[0].a
            results.append(dict(
                slug=a_element.get('href').split('/')[-2],
                name=a_element.text.strip(),
            ))

        return results

    def search(self, term):
        try:
            r = self.session.get(self.search_url, params=dict(title=term))
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for tr_element in soup.find('table', id='mangaList').tbody.find_all('tr'):
            td_elements = tr_element.find_all('td')

            if td_elements[3].text.strip() == '0':
                # Skipped manga with no chapters
                continue

            a_element = td_elements[0].a
            results.append(dict(
                slug=a_element.get('href').split('/')[-2],
                name=a_element.text.strip(),
            ))

        return results
