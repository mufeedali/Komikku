# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import requests
from urllib.parse import urlsplit

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import get_soup_element_inner_text
from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = 'Scantrad France'


class Scantrad(Server):
    id = 'scantrad'
    name = SERVER_NAME
    lang = 'fr'

    base_url = 'https://scantrad.net'
    search_url = base_url
    most_populars_url = base_url + '/mangas'
    manga_url = base_url + '/{0}'
    chapter_url = base_url + '/mangas/{0}/{1}'
    image_url = 'https://scan-trad.fr/{0}'

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

        r = self.session_get(self.manga_url.format(initial_data['slug']))
        if r is None:
            return None

        mime_type = get_buffer_mime_type(r.content)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[SERVER_NAME, ],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        container_element = soup.find('div', id='chap-top')
        title_element = container_element.find('div', class_='titre')
        data['name'] = get_soup_element_inner_text(title_element)
        data['cover'] = container_element.find('div', class_='ctt-img').img.get('src')

        # Details
        if authors_element := title_element.find('div', class_='titre-sub'):
            data['authors'] = authors_element.text.strip()[3:].split(', ')

        for element in container_element.find('div', class_='info').find_all('div', class_='sub-i'):
            label = get_soup_element_inner_text(element)

            if label.startswith('Genre'):
                data['genres'] = [span_element.text.strip() for span_element in element.find_all('span', class_='snm-button')]
            elif label.startswith('Status'):
                status = element.span.text.strip()
                if status == 'Arrêté':
                    data['status'] = 'suspended'
                elif status == 'En cours':
                    data['status'] = 'ongoing'
                elif status == 'Terminé':
                    data['status'] = 'complete'

        data['synopsis'] = container_element.find_all('div', class_='new-main')[0].p.text.strip()

        # Chapters
        if chapitres_container_element := soup.find('div', id='chapitres'):
            for element in reversed(chapitres_container_element.find_all('div', class_='chapitre')):
                data['chapters'].append(dict(
                    slug=element.a.get('href').split('/')[-1],
                    date=convert_date_string(element.find('div', class_='chl-date').text),
                    title='{0} {1}'.format(
                        element.find('span', class_='chl-num').text.strip(),
                        get_soup_element_inner_text(element.find('div', class_='chl-titre'))
                    ),
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

        imgs_elements = soup.find('div', class_='main_img').find_all('img')

        data = dict(
            pages=[],
        )
        for img_element in imgs_elements:
            url = img_element.get('data-src')
            if not url or not url.startswith('lel'):
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
        r = self.session_get(
            self.image_url.format(page['image']),
            headers={
                'Referer': self.base_url + '/',
                'Host': urlsplit(self.image_url).netloc,
                'Accept': 'image/webp,*/*',
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
            name=page['image'].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        r = self.session_get(self.most_populars_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for element in soup.find_all('div', class_='manga'):
            a_element = element.find('div', class_='mr-info').a

            results.append(dict(
                slug=a_element.get('href').split('/')[-1],
                name=a_element.text.strip(),
            ))

        return results

    def search(self, term=None):
        r = self.session_post(self.search_url, data=dict(q=term))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for a_element in soup.find_all('a'):
            name = a_element.find('div', class_='rgr-titre').text.strip()

            results.append(dict(
                slug=a_element.get('href').split('/')[-1],
                name=name,
            ))

        return results
