# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import dateparser
from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError

from mangascan.servers import Server
from mangascan.servers import USER_AGENT

server_id = 'mangakawaii'
server_name = 'Mangakawaii'
server_lang = 'fr'


class Mangakawaii(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.mangakawaii.to'
    search_url = base_url + '/recherche'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'
    image_url = 'https://cdn.mangakawaii.to/uploads/manga/{0}/chapters/{1}/{2}'
    cover_url = 'https://cdn.mangakawaii.to/uploads/manga/{0}/cover/cover_250x350.jpg'

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
        ))

        data['name'] = soup.find('h1', class_='manga-bg__title').text.strip()
        if data.get('cover') is None:
            data['cover'] = self.cover_url.format(data['slug'])

        # Details
        elements = soup.find('div', class_='manga-info').find_all(class_='info-list__row')
        for element in elements:
            label = element.strong.text.strip()

            if label.startswith('Auteur') or label.startswith('Artiste'):
                value = element.a.text.strip()
                for t in value.split(','):
                    t = t.strip()
                    if t not in data['authors']:
                        data['authors'].append(t)
            elif label.startswith('Scantrad'):
                a_element = element.find_all('a')[0]
                data['scanlators'] = [a_element.text.replace('[', '').replace(']', '').strip(), ]
            elif label.startswith('Genres'):
                a_elements = element.find_all('a')
                data['genres'] = [a_element.text.strip() for a_element in a_elements]
            elif label.startswith('Statut'):
                # possible values: ongoing, complete, None
                data['status'] = 'ongoing' if element.span.text.lower() == 'en cours' else 'complete'

        # Synopsis
        data['synopsis'] = soup.find('div', class_='info-desc__content').text.strip()

        # Chapters
        elements = soup.find('div', class_='chapters-list').find_all('div', class_='chapter-item')
        for element in reversed(elements):
            a_element = element.find('div', class_='chapter-item__name').a
            slug = a_element.get('href').split('/')[-1]
            title = a_element.text.strip()
            date = element.find('div', class_='chapter-item__date').text.strip()

            data['chapters'].append(dict(
                slug=slug,
                title=title,
                date=dateparser.parse(date, 'DD.MM.YYYY', settings={'DATE_ORDER': 'DMY'}).date(),
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

        pages_imgs = soup.find('div', id='all').find_all('img')

        data = dict(
            pages=[],
        )
        for img in pages_imgs:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url directly
                image=img.get('data-src').strip().split('/')[-1],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        url = self.image_url.format(manga_slug, chapter_slug, page['image'])

        try:
            r = self.session.get(url)
        except ConnectionError:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (page['image'], r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_cover_image(self, url):
        """
        Returns manga cover (image) content
        """
        try:
            r = self.session.get(url)
        except ConnectionError:
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
            r = self.session.get(self.search_url, params=dict(query=term))
        except ConnectionError:
            return None

        if r.status_code == 200:
            try:
                # Returned data for each manga:
                # value: name of the manga
                # data: slug of the manga
                results = r.json()['suggestions']

                for result in results:
                    result['slug'] = result.pop('data')
                    result['name'] = result.pop('value')
                    result['cover'] = result.pop('imageUrl')

                return results
            except Exception:
                return None
        else:
            return None
