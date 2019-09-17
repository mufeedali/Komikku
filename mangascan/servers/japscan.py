# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import cloudscraper
import magic
import re
from requests.exceptions import ConnectionError
import unicodedata

from mangascan.servers import Server

server_id = 'japscan'
server_name = 'JapScan'
server_lang = 'fr'


class Japscan(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.japscan.co'
    search_url = base_url + '/search/'
    manga_url = base_url + '/manga/{0}/'
    chapter_url = base_url + '/lecture-en-ligne/{0}/{1}/'
    image_url = 'https://c.japscan.co/lel/{0}/{1}/{2}'
    cover_url = base_url + '{0}'

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
            chapters=[],
            server_id=self.id,
            synopsis=None,
        ))

        card_element = soup.find_all('div', class_='card')[0]

        # Main name: japscan handles several names for mangas (main + alternatives)
        # Name provided by search can be one of the alternatives
        # First word (Manga, Manhwa, ...) must be removed from name
        data['name'] = ' '.join(card_element.find('h1').text.strip().split()[1:])

        # Details
        if not card_element.find_all('div', class_='d-flex'):
            # mobile version
            elements = card_element.find_all('div', class_='row')[0].find_all('p')
        else:
            # desktop version
            elements = card_element.find_all('div', class_='d-flex')[0].find_all('p', class_='mb-2')

        for element in elements:
            label = element.span.text
            element.span.extract()
            value = element.text.strip()

            if label.startswith(('Auteur', 'Artiste')):
                for t in value.split(','):
                    t = t.strip()
                    if t not in data['authors']:
                        data['authors'].append(t)
            elif label.startswith('Genre'):
                data['genres'] = [genre.strip() for genre in value.split(',')]
            elif label.startswith('Statut'):
                # Possible values: ongoing, complete
                data['status'] = 'ongoing' if value == 'En Cours' else 'complete'

        # Synopsis
        synopsis_element = card_element.find('p', class_='list-group-item-primary')
        if synopsis_element:
            data['synopsis'] = synopsis_element.text.strip()

        # Chapters
        elements = soup.find('div', id='chapters_list').find_all('div', class_='chapters_list')
        for element in reversed(elements):
            slug = element.a.get('href').split('/')[3]
            if element.a.span:
                element.a.span.extract()

            data['chapters'].append(dict(
                slug=slug,
                date=element.span.text.strip(),
                title=element.a.text.strip(),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages and scrambled are expected.
        """
        url = self.chapter_url.format(manga_slug, chapter_slug)

        try:
            r = self.session.get(url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        data = dict(
            pages=[],
            scrambled=0,
        )

        soup = BeautifulSoup(r.text, 'html.parser')

        # Scrambled ?
        scripts = soup.find('head').find_all('script')
        for script in scripts:
            src = script.get('src')
            if src and src.startswith('/js/iYFbYi_U'):
                data['scrambled'] = 1
                break

        pages_options = soup.find('select', id='pages').find_all('option')
        for option in pages_options:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url already
                image=option.get('data-img').split('/')[-1],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        # This server use a specific manga slug for images URLs
        manga_slug = unicodedata.normalize('NFKD', manga_name)
        manga_slug = manga_slug.encode('ascii', 'ignore').decode()
        manga_slug = re.sub(r'[^a-zA-Z0-9\- ]+', '', manga_slug)  # remove not alphanum characters
        manga_slug = manga_slug.replace(' - ', ' ')
        manga_slug = manga_slug.replace(' ', '-')

        chapter_slug = chapter_slug.capitalize()

        url = self.image_url.format(manga_slug, chapter_slug, page['image'])
        imagename = url.split('/')[-1]

        try:
            r = self.session.get(url)
        except ConnectionError:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (imagename, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_cover_image(self, cover_path):
        """
        Returns manga cover (image) content
        """
        try:
            r = self.session.get(self.cover_url.format(cover_path))
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
            self.session.get(self.base_url)

            r = self.session.post(self.search_url, data=dict(search=term))
        except ConnectionError:
            return None

        if r.status_code == 200:
            if r.content == b'':
                # No results
                return []

            try:
                results = r.json(strict=False)

                # Returned data for each manga:
                # name:  name of the manga
                # image: path of cover image
                # url:   path of manga page
                for result in results:
                    # Extract slug from url
                    result['slug'] = result.pop('url').split('/')[2]
                    result['cover'] = result.pop('image')

                return results
            except Exception:
                return None
        else:
            return None
