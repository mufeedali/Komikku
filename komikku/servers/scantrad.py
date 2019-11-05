# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import dateparser
from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError

from komikku.servers import Server
from komikku.servers import USER_AGENT

server_id = 'scantrad'
server_name = 'Scantrad France'
server_lang = 'fr'


class Scantrad(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.scantrad.net'
    search_url = base_url + '/mangas'
    manga_url = base_url + '/{0}'
    chapter_url = base_url + '/mangas/{0}/{1}'
    cover_url = base_url + '/{0}'
    image_url = base_url + '/{0}'

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
            scanlators=['Scantrad France',],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        div_info = soup.find('div', class_='mf-info')
        data['name'] = div_info.find('div', class_='titre').text.strip()
        data['cover'] = div_info.find('div', class_='poster').img.get('src')

        data['synopsis'] = div_info.find('div', class_='synopsis').text.strip()
        status = div_info.find_all('div', class_='sub-i')[1].span.text.strip().lower()
        if status == 'en cours':
            data['status'] = 'ongoing'
        elif status == 'terminé':
            data['status'] = 'complete'

        # Chapters
        for div_element in soup.find('div', id='chap-top').find_all('div', class_='chapitre'):
            btns_elements = div_element.find('div', class_='ch-right').find_all('a')
            if len(btns_elements) < 2:
                continue

            data['chapters'].append(dict(
                slug=btns_elements[0].get('href').split('/')[-1],
                date=dateparser.parse(div_element.find('div', class_='chl-date').text).date(),
                title='{0} {1}'.format(
                    div_element.find('span', class_='chl-num').text.strip(),
                    div_element.find('span', class_='chl-titre').text.strip()
                ),
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

        imgs_elements = soup.find('div', class_='main_img').find_all('img')

        data = dict(
            pages=[],
        )
        for img_element in imgs_elements:
            url = img_element.get('data-src')
            if not url.startswith('lel'):
                continue

            data['pages'].append(dict(
                slug=None,
                image=url,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        try:
            r = self.session.get(self.image_url.format(page['image']))
        except ConnectionError:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)
        image_name = page['image'].split('/')[-1]

        return (image_name, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_cover_image(self, url):
        """
        Returns manga cover (image) content
        """
        try:
            r = self.session.get(self.cover_url.format(url))
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
            r = self.session.get(self.search_url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for a_element in soup.find('div', class_='h-left').find_all('a'):
            name = a_element.find('div', class_='hmi-titre').text.strip()

            if name.lower().find(term.lower()) >= 0:
                results.append(dict(
                    slug=a_element.get('href').split('/')[-1],
                    name=name,
                ))

        return results
