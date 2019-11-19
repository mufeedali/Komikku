# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError

from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT

# NOTE: https://mangakakalot.com seems to be a clone (same IP)
server_id = 'manganelo'
server_name = 'MangaNelo'
server_lang = 'en'


class Manganelo(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://manganelo.com'
    search_url = base_url + '/home_json_search'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/chapter/{0}/{1}'
    image_url = base_url + '/uploads/manga/{0}/chapters/{1}/{2}'

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

        # Name & cover
        data['name'] = soup.find('ul', class_='manga-info-text').find('h1').text.strip()
        if data.get('cover') is None:
            data['cover'] = soup.find('div', class_='manga-info-pic').img.get('src')

        # Details
        elements = soup.find('ul', class_='manga-info-text').find_all('li')
        for element in elements:
            text = element.text.strip().split(':')
            if len(text) != 2:
                continue

            label = text[0].strip()
            value = text[1].strip()

            if label.startswith('Author'):
                data['authors'] = [t.strip() for t in value.split(',') if t]
            elif label.startswith('Genres'):
                data['genres'] = [t.strip() for t in value.split(',')]
            elif label.startswith('Status'):
                status = value.lower()
                if status == 'completed':
                    data['status'] = 'complete'
                elif status == 'ongoing':
                    data['status'] = 'ongoing'

        # Synopsis
        div_synopsis = soup.find('div', id='noidungm')
        div_synopsis.h2.extract()
        data['synopsis'] = div_synopsis.text.strip()

        # Chapters
        elements = soup.find('div', class_='chapter-list').find_all('div', class_='row')
        for element in reversed(elements):
            spans_info = element.find_all('span')

            slug = spans_info[0].a.get('href').split('/')[-1]
            title = spans_info[0].a.text.strip()
            date = spans_info[2].text.strip()

            data['chapters'].append(dict(
                slug=slug,
                title=title,
                date=convert_date_string(date, format='%b-%d-%y'),
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

        pages_imgs = soup.find('div', id='vungdoc').find_all('img')

        data = dict(
            pages=[],
        )
        for img in pages_imgs:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url directly
                image=img.get('src').strip(),
            ))

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

        return (page['image'].split('/')[-1], r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

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
            r = self.session.post(self.search_url, data=dict(searchword=term))
        except ConnectionError:
            return None

        if r.status_code == 200:
            try:
                # Returned data for each manga:
                # name: name of the manga (HTML)
                # nameunsigned: slug of the manga
                # image: URL of the cover image
                data = r.json()

                results = []
                for item in data:
                    results.append(dict(
                        slug=item['nameunsigned'],
                        name=BeautifulSoup(item['name'], 'html.parser').text,
                        cover=item['image'],
                    ))

                return results
            except Exception:
                return None
        else:
            return None
