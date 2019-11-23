# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from collections import OrderedDict
from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError
from urllib.parse import unquote_plus

from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT

server_id = 'ninemanga'
server_name = 'Nine Manga'
server_lang = 'en'

headers = OrderedDict(
    [
        ('User-Agent', USER_AGENT),
        ('Accept-Language', 'en-US,en;q=0.5'),
    ]
)


class Ninemanga(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'http://www.ninemanga.com'
    search_url = base_url + '/search/ajax/'
    most_populars_url = base_url + '/list/Hot-Book/'
    manga_url = base_url + '/manga/{0}.html'
    chapter_url = base_url + '/chapter/{0}/{1}'
    page_url = chapter_url

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

        if r.url == self.base_url:
            # Manga page doesn't exist, we have been redirected to homepage
            return None
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

        # Last word (Manga, Manhwa, ...) must be removed from name
        data['name'] = ' '.join(soup.find('div', class_='ttline').h1.text.strip().split()[:-1])
        data['cover'] = soup.find('a', class_='bookface').img.get('src')

        # Details
        elements = soup.find('ul', class_='message').find_all('li')
        for element in elements:
            label = element.b.text

            if label.startswith(('Author', 'Auteur', 'Autor')):
                data['authors'] = [element.a.text.strip(), ]
            elif label.startswith(('Genre', 'Genre', 'Género', 'Genere', 'Gênero')):
                for a_element in element.find_all('a'):
                    data['genres'].append(a_element.text)
            elif label.startswith(('Status', 'Statut', 'Estado', 'Stato')):
                value = element.find_all('a')[0].text.strip().lower()

                if value in ('ongoing', 'en cours', 'laufende', 'en curso', 'in corso', 'em tradução'):
                    data['status'] = 'ongoing'
                elif value in ('complete', 'complété', 'abgeschlossen', 'completado', 'completato', 'completo'):
                    data['status'] = 'complete'

        # Synopsis
        synopsis_element = soup.find('p', itemprop='description')
        if synopsis_element:
            synopsis_element.b.extract()
            data['synopsis'] = synopsis_element.text.strip()

        # Chapters
        div_element = soup.find('div', class_='chapterbox')
        if div_element:
            li_elements = div_element.find_all('li')
            for li_element in reversed(li_elements):
                slug = li_element.a.get('href').split('/')[-1].replace('.html', '')
                data['chapters'].append(dict(
                    slug=slug,
                    title=li_element.a.text.strip(),
                    date=convert_date_string(li_element.span.text.strip(), format='%b %d, %Y'),
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
        options_elements = soup.find('select', id='page').find_all('option')

        data = dict(
            pages=[],
        )
        for option_element in options_elements:
            data['pages'].append(dict(
                slug=option_element.get('value').split('/')[-1],
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        # Scrap HTML page to get image url
        url = self.page_url.format(manga_slug, page['slug'])

        try:
            r = self.session.get(url)
        except ConnectionError:
            return (None, None)

        soup = BeautifulSoup(r.text, 'html.parser')
        url = soup.find('img', id='manga_pic_1').get('src')
        imagename = url.split('/')[-1]

        # Get scan image
        r = self.session.get(url)
        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (imagename, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns Hot manga list
        """
        try:
            r = self.session.get(self.most_populars_url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for a_element in soup.find('ul', class_='direlist').find_all('a', class_='bookname'):
            results.append(dict(
                name=a_element.text.strip(),
                slug=unquote_plus(a_element.get('href')).split('/')[-1][:-5],
            ))

        return results

    def search(self, term):
        try:
            r = self.session.get(self.search_url, params=dict(term=term))
        except ConnectionError:
            return None

        if r.status_code == 200:
            try:
                # Returned data for each manga:
                # 0: cover path
                # 1: name of the manga
                # 2: slug of the manga
                # 3: UNUSED
                # 4: UNUSED
                data = r.json(strict=False)

                results = []
                for item in data:
                    results.append(dict(
                        slug=item[2],
                        name=item[1],
                    ))

                return results
            except Exception:
                return None
        else:
            return None
