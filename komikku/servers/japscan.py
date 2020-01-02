# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import cloudscraper
import magic
import re
import unicodedata
import unidecode

from komikku.servers import convert_date_string
from komikku.servers import Server

SERVER_NAME = 'JapScan'


class Japscan(Server):
    id = 'japscan'
    name = SERVER_NAME
    lang = 'fr'

    base_url = 'https://www.japscan.co'
    search_url = base_url + '/mangas/{0}/{1}'
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
            chapters=[],
            server_id=self.id,
            synopsis=None,
        ))

        card_element = soup.find_all('div', class_='card')[0]

        # Main name: japscan handles several names for mangas (main + alternatives)
        # Name provided by search can be one of the alternatives
        # First word (Manga, Manhwa, ...) must be removed from name
        data['name'] = ' '.join(card_element.find('h1').text.strip().split()[1:])
        if data.get('cover') is None:
            data['cover'] = self.cover_url.format(card_element.find('img').get('src'))

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
            if element.a.span:
                span = element.a.span.extract()
                # JapScan sometimes uploads some "spoiler preview" chapters, containing 2 or 3 untranslated pictures taken from a raw.
                # Sometimes they also upload full RAWs/US versions and replace them with a translation as soon as available.
                # Those have a span.badge "SPOILER", "RAW" or "VUS". We exclude these from the chapters list.
                if span.text.strip() in ('RAW', 'SPOILER', 'VUS', ):
                    continue

            slug = element.a.get('href').split('/')[3]

            data['chapters'].append(dict(
                slug=slug,
                title=element.a.text.strip(),
                date=convert_date_string(element.span.text.strip(), format='%d %b %Y'),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages and scrambled are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r is None:
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
        manga_slug = re.sub(r'[^a-zA-Z0-9\'\- ]+', '', manga_slug)  # remove not alphanum characters
        manga_slug = manga_slug.replace(' - ', ' ')
        manga_slug = manga_slug.replace("'", '-')
        manga_slug = manga_slug.replace(' ', '-')

        chapter_slug = chapter_slug.capitalize()

        url = self.image_url.format(manga_slug, chapter_slug, page['image'])
        imagename = url.split('/')[-1]

        r = self.session_get(url)
        if r is None:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (imagename, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns TOP manga
        """
        r = self.session_get(self.base_url)
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for li_element in soup.find('div', id='top_mangas_all_time').find_all('li'):
            a_element = li_element.find_all('a')[0]
            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-2],
            ))

        return results

    def search(self, term):
        """
        JapScan does not provide a search. At our disposal, we only have a list.
        Mangas are indexed by the first character of their name then paginated:

        /mangas/0-9/1
        /mangas/0-9/2
        /mangas/0-9/...
        /mangas/A/1
        /mangas/A/2
        /mangas/A/...
        /mangas/...
        """
        term = unidecode.unidecode(term).lower()
        if term[0] in '0123456789':
            index = '0-9'
        else:
            index = term[0].upper()

        r = self.session_get(self.search_url.format(index, 1))
        if r is None:
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        nb_pages = int(soup.find_all('div', class_='card')[0].find('ul', class_='pagination').find_all('a')[-1].text)

        for page in range(nb_pages):
            page_results = self.search_manga_list_page(term, index, page + 1)
            if page_results:
                results += page_results

        return sorted(results, key=lambda m: m['name'])

    def search_manga_list_page(self, term, index, page=1):
        r = self.session_get(self.search_url.format(index, page))
        if r is None:
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for element in soup.find_all('div', class_='card')[0].find('div', class_='d-flex').find_all('div'):
            name = element.p.a.text.strip()
            if term not in unidecode.unidecode(name).lower():
                continue

            slug = element.p.a.get('href').split('/')[-2]
            cover = self.cover_url.format(element.a.img.get('src'))

            results.append(dict(
                name=name,
                slug=slug,
                cover=cover,
            ))

        return results
