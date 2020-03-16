# -*- coding: utf-8 -*-

# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import cloudscraper
from bs4 import BeautifulSoup
import magic

from komikku.servers import convert_date_string
from komikku.servers import Server

SERVER_NAME = 'Mangakawaii'


class Mangakawaii(Server):
    id = 'mangakawaii'
    name = SERVER_NAME
    lang = 'fr'

    base_url = 'https://www.mangakawaii.com'
    search_url = base_url + '/recherche'
    most_populars_url = base_url + '/mieux-notes'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}/1'
    image_url = 'https://cdn.mangakawaii.com/uploads/manga/{0}/chapters/{1}/{2}'
    cover_url = 'https://cdn.mangakawaii.com/uploads/manga/{0}/cover/cover_250x350.jpg'

    def __init__(self):
        if self.session is None:
            self.session = cloudscraper.create_scraper()

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

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
        ))

        title_element = soup.find('h1', class_='manga-bg__title')
        if title_element is None:
            title_element = soup.find('h1', class_='manga__title')
        data['name'] = title_element.text.strip()
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
                status = element.span.text.strip().lower()
                if status == 'en cours':
                    data['status'] = 'ongoing'
                elif status == 'terminé':
                    data['status'] = 'complete'

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
                date=convert_date_string(date, format='%d.%m.%Y'),
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

        script_elements = soup.find_all('script')

        data = dict(
            pages=[],
        )
        for script_element in reversed(script_elements):
            script = script_element.text.strip()
            if not script.startswith('var $Imagesrc'):
                continue

            for line in script.split('\n'):
                if '.rdata-' not in line:
                    continue

                data['pages'].append(dict(
                    slug=line.strip().split('"')[-2].strip().split('/')[-1],
                    image=None,
                ))

            break

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """ Returns chapter page scan (image) content """
        r = self.session_get(self.image_url.format(manga_slug, chapter_slug, page['slug']))
        if r is None:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (page['slug'], r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """ Returns manga absolute URL """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """ Returns best noted manga list """
        r = self.session_get(self.most_populars_url)
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for tr_element in soup.find('table', class_='table').tbody.find_all('tr', recursive=False):
            a_element = tr_element.find_all('td')[2].a
            a_element.span.decompose()
            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
            ))

        return results

    def search(self, term):
        self.session_get(self.base_url)

        r = self.session_get(self.search_url, params=dict(query=term))
        if r is None:
            return None

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
