# -*- coding: utf-8 -*-

# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import requests

from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = 'Scan Manga'


class Scanmanga(Server):
    id = 'scanmanga'
    name = SERVER_NAME
    lang = 'fr'
    long_strip_genres = ['Webcomic', ]

    base_url = 'https://www.scan-manga.com'
    search_url = base_url + '/qsearch.json'
    most_populars_url = base_url + '/Tout-le-TOP.html'
    manga_url = base_url + '{0}'
    chapter_url = base_url + '/lecture-en-ligne/{0}-{1}.html'
    cover_url = base_url + '/img{0}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's relative url and slug (provided by search)
        """
        assert 'url' in initial_data and 'slug' in initial_data, 'Manga url or slug are missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['url']))
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

        data['name'] = soup.find('div', class_='h2_titre').h2.text.strip()
        if data.get('cover') is None:
            data['cover'] = soup.find('div', class_='image_manga').img.get('src')

        # Details
        li_elements = soup.find('div', class_='contenu_texte_fiche_technique').find_all('li')
        for a_element in li_elements[0].find_all('a'):
            data['authors'].append(a_element.text.strip())

        data['genres'] = [g.strip() for g in li_elements[1].text.split()]
        for a_element in li_elements[2].find_all('a'):
            a_element.span.extract()
            data['genres'].append(a_element.text.strip())

        status = li_elements[6].text.strip().lower()
        if status == 'en cours':
            data['status'] = 'ongoing'
        elif status in ('one shot', 'terminé'):
            data['status'] = 'complete'
        elif status == 'en pause':
            data['status'] = 'hiatus'

        for a_element in li_elements[7].find_all('a'):
            data['scanlators'].append(a_element.text.strip())

        # Synopsis
        p_element = soup.find('div', class_='texte_synopsis_manga').find('p', itemprop='description')
        p_element.span.extract()
        data['synopsis'] = p_element.text.strip()

        # Chapters
        for element in reversed(soup.find_all('div', class_='chapitre_nom')):
            a_element = element.a
            if not a_element:
                continue

            data['chapters'].append(dict(
                slug=a_element.get('href').split('/')[-1].replace(data['slug'], '').replace('.html', ''),
                title=element.text.strip(),
                date=None,
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

        soup = BeautifulSoup(r.content, 'html.parser')

        data = dict(
            pages=[],
        )

        for script_element in soup.find_all('script'):
            script = script_element.string
            if not script or not script.strip().startswith('(function(d, s, id)'):
                continue

            image_base_url = None
            for line in script.split('\n'):
                line = line.strip()

                if 'var nPa = new Array' in line:
                    array_name = line.split(' ')[1]

                    for item in line.split(';'):
                        if not item.startswith(f'{array_name}['):
                            continue

                        data['pages'].append(dict(
                            slug=None,
                            image=item.split('"')[1],
                        ))

                elif line.startswith(('tlo =', "$('#preload')")):
                    image_base_url = line.split("'")[-2]
                    break

            if image_base_url:
                for page in data['pages']:
                    page['image'] = image_base_url + page['image']

            break

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page['image'],
            headers={
                'referer': self.chapter_url.format(manga_slug, chapter_slug),
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
        return self.manga_url.format(url)

    def get_most_populars(self):
        """
        Returns list of top manga
        """
        r = self.session_get(
            self.most_populars_url,
            headers={
                'referer': self.base_url
            }
        )
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for element in soup.find_all('div', class_='titre_fiche_technique'):
            a_element = element.h3.a
            name = a_element.text.strip()
            if 'Novel' in name:
                # Ignored, it's a novel
                continue

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1].replace('.html', ''),
                url=a_element.get('href').replace(self.base_url, ''),
            ))

        return results

    def search(self, term):
        r = self.session_get(
            self.search_url,
            params=dict(term=term),
            headers={
                'x-requested-with': 'XMLHttpRequest',
                'referer': self.base_url,
            }
        )

        if r.status_code == 200:
            try:
                data = r.json()

                results = []
                for item in data:
                    if 'Novel' in item[0]:
                        # Ignored, it's a novel
                        continue

                    results.append(dict(
                        url=item[1].replace(self.base_url, ''),
                        slug=item[1].split('/')[-1].replace('.html', ''),
                        name=item[0],
                        cover=self.cover_url.format(item[4]),
                    ))

                return results
            except Exception:
                return None

        return None
