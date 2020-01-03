# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from collections import OrderedDict
from bs4 import BeautifulSoup
import magic
import requests
import unidecode

from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = 'Central de Mangás'

headers = OrderedDict(
    [
        ('User-Agent', USER_AGENT),
    ]
)


class Centraldemangas(Server):
    id = 'centraldemangas'
    name = SERVER_NAME
    lang = 'pt'

    base_url = 'http://centraldemangas.online'
    search_url = base_url + '/api/titulos'
    manga_url = base_url + '/titulos/{0}'
    chapter_url = base_url + '/titulos/{0}/manga/ler-online-completo/{1}'

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

        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r is None:
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

        # Details
        elements = soup.find('div', class_='relaxed').find_all('div', class_='item')
        for element in elements:
            label_element = element.find('div', class_='header')
            if not label_element:
                continue

            label = label_element.text.strip()
            value_element = element.find('div', class_='description')

            if label == 'Sinópse':
                cover_img = value_element.img.extract()
                data['cover'] = cover_img.get('src')
                data['synopsis'] = value_element.text.strip()
            elif label in ('Arte', 'Autor'):
                data['authors'].append(value_element.text.strip())
            elif label == 'Gênero':
                for a_element in value_element.find_all('a'):
                    data['genres'].append(a_element.text.strip())
            elif label == 'Scantrad':
                for a_element in value_element.find_all('a'):
                    data['scanlators'].append(a_element.text.strip())
            elif label == 'Status':
                value = value_element.a.text.strip()

                if value == 'Em publicação':
                    data['status'] = 'ongoing'
                elif value == 'Completo':
                    data['status'] = 'complete'
            elif label == 'Capítulos':
                for tr_element in reversed(value_element.find_all('div', class_='content')[0].table.tbody.find_all('tr')[1:]):
                    tds_elements = tr_element.find_all('td')

                    data['chapters'].append(dict(
                        slug=tds_elements[0].a.get('href').split('/')[-1],
                        title=tds_elements[0].a.text.strip(),
                        date=convert_date_string(tds_elements[1].text.strip(), format='%d/%m/%Y'),
                    ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        # Pages URLs infos are located in the last JS script at the bottom of document
        pages_slugs = None
        pages_url_start = None
        for line in soup.find_all('script')[-1].text.split('\n'):
            line = line.strip()[:-1]

            if line.startswith('var pages'):
                # Ex: var pages = ['01','02','03','04','05','06','07','08','09','10','11','12','13','14',]
                pages_slugs = line.split('=')[1].strip().replace('[', '').replace(']', '').replace("'", '')[:-1].split(',')
            elif line.startswith('var urlSulfix'):
                # Ex: var urlSulfix = 'http://mangas2016.centraldemangas.com.br/tales_of_demons_and_gods/tales_of_demons_and_gods002-'
                pages_url_start = line.split('=')[1].strip().replace("'", '')

        data = dict(
            pages=[],
        )
        if pages_slugs is not None and pages_url_start is not None:
            for page_slug in pages_slugs:
                data['pages'].append(dict(
                    slug=None,
                    image='{0}{1}.jpg'.format(pages_url_start, page_slug),
                ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        # Scrap HTML page to get image url
        url = page['image']

        r = self.session_get(url, headers={'Referer': self.chapter_url.format(manga_slug, chapter_slug)})
        if r is None:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)
        imagename = url.split('/')[-1]

        return (imagename, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns TOP 10 manga
        """
        r = self.session_get(self.base_url)
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for a_element in soup.find_all('div', class_='ui red segment')[0].find_all('a')[:-1]:
            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
            ))

        return results

    def search(self, term):
        r = self.session_get(self.search_url, headers={'X-Requested-With': 'XMLHttpRequest'})
        if r is None:
            return None

        if r.status_code == 200:
            data = r.json(strict=False)

            results = []
            term = unidecode.unidecode(term).lower()
            for item in data:
                if term not in unidecode.unidecode(item['title']).lower():
                    continue

                results.append(dict(
                    slug=item['url'].split('/')[-1],
                    name=item['title'],
                ))

            return results

        return None
