# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import cloudscraper
import json
import re

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT_MOBILE

RE_API_CHAPTERS_URL = re.compile(r'.*(/arrilot/load-widget\?id=.*)\",.*')
SERVER_NAME = 'MangaKawaii'


class Mangakawaii(Server):
    id = 'mangakawaii'
    name = SERVER_NAME
    lang = 'fr'
    long_strip_genres = ['Webtoon', ]

    base_url = 'https://www.mangakawaii.net'
    search_url = base_url + '/recherche-manga'
    most_populars_url = base_url + '/filterMangaList?page=1&cat=&alpha=&sortBy=views&asc=false&author='
    most_populars_referer_url = base_url + '/liste-manga'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}/1'
    cdn_base_url = 'https://cdn.mangakawaii.net'
    image_url = cdn_base_url + '/uploads/manga/{0}/chapters_fr/{1}/{2}'
    cover_url = cdn_base_url + '/uploads/manga/{0}/cover/cover_250x350.jpg'

    csrf_token = None

    def __init__(self):
        if self.session is None:
            self.session = cloudscraper.create_scraper()
            self.session.headers.update({'User-Agent': USER_AGENT_MOBILE})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
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

        data['name'] = soup.find('h1').text.strip()
        if data.get('cover') is None:
            data['cover'] = self.cover_url.format(data['slug'])

        # Details
        elements = soup.find('div', class_='col-md-8 mt-4 mt-md-0').find_all('dl')
        for element in elements:
            label = element.dt.text.strip()

            if label.startswith('Auteur') or label.startswith('Artiste'):
                value = element.dd.span.text.strip()
                for t in value.split(','):
                    t = t.strip()
                    if t not in data['authors']:
                        data['authors'].append(t)

            elif label.startswith('Scantrad'):
                for a_element in element.dd.find_all('a', itemprop='name'):
                    data['scanlators'].append(a_element.text.replace('[', '').replace(']', '').strip())

            elif label.startswith('Genres'):
                a_elements = element.dd.find_all('a')
                data['genres'] = [a_element.text.strip() for a_element in a_elements]

            elif label.startswith('Statut'):
                status = element.dd.span.text.strip().lower()
                if status == 'en cours':
                    data['status'] = 'ongoing'
                elif status == 'terminé':
                    data['status'] = 'complete'
                elif status == 'abandonné':
                    data['status'] = 'suspended'
                elif status == 'en pause':
                    data['status'] = 'hiatus'

            elif label.startswith('Description'):
                data['synopsis'] = element.dd.text.strip()

        # Chapters
        element = soup.find('div', id='arrilot-widget-container-2')
        if element and element.script:
            api_chapters_url = RE_API_CHAPTERS_URL.findall(element.script.string)[0]
            r = self.session_get(self.base_url + api_chapters_url, headers={'Referer': self.manga_url.format(data['slug'])})
            if r.status_code != 200:
                return None

            mime_type = get_buffer_mime_type(r.content)
            if mime_type != 'text/html':
                return None

            soup = BeautifulSoup(r.text, 'html.parser')

            elements = soup.find_all('tr')
            for element in reversed(elements):
                if not element.get('class'):
                    # Skip volume row
                    continue

                a_element = element.find('td', class_='table__chapter').a
                date = list(element.find('td', class_='table__date').stripped_strings)[0]

                data['chapters'].append(dict(
                    slug=a_element.get('href').split('/')[-1],
                    title=a_element.text.strip(),
                    date=convert_date_string(date, format='%d.%m.%Y'),
                ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = dict(
            pages=[],
        )
        for script_element in reversed(soup.find_all('script')):
            script = script_element.string
            if not script or not script.strip().startswith('var title'):
                continue

            for line in script.split('\n'):
                line = line.strip()
                if not line.startswith('var pages'):
                    continue

                pages = json.loads(line[12:-1])
                for index, page in enumerate(pages):
                    data['pages'].append(dict(
                        slug=None,
                        image=page['page_image'],
                        index=index,
                    ))

                break

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            self.image_url.format(manga_slug, chapter_slug, page['image']),
            headers={
                'Referer': self.chapter_url.format(manga_slug, chapter_slug),
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['image'].split('?')[0].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns list of most viewed manga
        """
        r = self.session_get(
            self.most_populars_url,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.most_populars_referer_url,
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/plain':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.find_all('div', class_='media-thumbnail'):
            results.append(dict(
                name=element.find('div', class_='media-thumbnail__overlay').find('h3').text.strip(),
                slug=element.find('a').get('href').split('/')[-1],
            ))

        return results

    def search(self, term):
        r = self.session_get(
            self.search_url,
            params=dict(query=term, search_type='manga'),
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.base_url,
            }
        )

        if r.status_code == 200:
            try:
                # Returned data for each manga:
                # value: name of the manga
                # data: slug of the manga
                # imageUrl: cover of the manga
                data = r.json()['suggestions']

                results = []
                for item in data:
                    results.append(dict(
                        slug=item['data'],
                        name=item['value'],
                        cover=item['imageUrl'],
                    ))

                return results
            except Exception:
                return None

        return None
