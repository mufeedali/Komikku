# -*- coding: utf-8 -*-

# Copyright (C) 2020 Leo Prikler
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Leo Prikler <leo.prikler@student.tugraz.at>

from bs4 import BeautifulSoup
import requests

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = 'NHentai (NSFW)'


class Nhentai(Server):
    id = 'nhentai'
    name = SERVER_NAME
    lang = 'en'
    lang_code = 'english'

    base_url = 'https://nhentai.net'
    search_url = base_url + '/search'
    manga_url = base_url + '/g/{0}'
    page_url = 'https://i.nhentai.net/galleries/{0}/{1}.jpg'

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
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

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

        info = soup.find('div', id='info')
        cover_el = soup.find('div', id='cover')
        cover_img = cover_el.find('img').get('data-src')
        data['cover'] = cover_img

        data['chapters'].append(dict(
            slug=cover_img.rstrip('/').split('/')[-2],
            title=info.find('h1').text.strip(),
        ))

        for tag_container in info.find_all('div', class_='tag-container'):
            category = tag_container.text.split(':')[0].strip()

            if category == 'Uploaded':
                time = tag_container.find('time').get('datetime')
                data['chapters'][0]['date'] = convert_date_string(time.split('T')[0], '%Y-%m-%d')

            for tag in tag_container.find_all('a', class_='tag'):
                clean_tag = tag.find('span', class_='name').text.strip()
                if category in ['Artists', 'Groups', ]:
                    data['authors'].append(clean_tag)
                if category in ['Tags', ]:
                    data['genres'].append(clean_tag)

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        assert chapter_slug is not None
        r = self.session_get(self.manga_url.format(manga_slug))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')
        pages = []

        info = soup.find('div', id='info')
        for tag_container in info.find_all('div', class_='tag-container'):
            category = tag_container.text.split(':')[0].strip()

            if category in ['Pages']:
                tag = tag_container.find('a', class_='tag')
                clean_tag = tag.find('span', class_='name').text.strip()
                for i in range(1, int(clean_tag) + 1):
                    page = dict(
                        image=None,
                        slug=str(i),
                    )
                    pages.append(page)

        return dict(pages=pages)

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        assert chapter_slug is not None
        print(self.page_url.format(chapter_slug, page['slug']))
        r = self.session_get(self.page_url.format(chapter_slug, page['slug']))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['slug'],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns most popular mangas (bayesian rating)
        """
        return self._search_common({'q': 'language:' + self.lang_code, 'sort': 'popular'})

    def _search_common(self, params):
        r = self.session_get(self.search_url, params=params)

        if r.status_code == 200:
            try:
                results = []
                soup = BeautifulSoup(r.text, 'lxml')
                elements = soup.find_all('div', class_='gallery')

                for element in elements:
                    a_element = element.find('a', class_='cover')
                    caption_element = element.find('div', class_='caption')
                    results.append(dict(
                        slug=a_element.get('href').rstrip('/').split('/')[-1],
                        name=caption_element.text.strip(),
                    ))

                return results
            except Exception:
                return None

        return None

    def search(self, term):
        term = term + ' language:' + self.lang_code
        return self._search_common({'q': term})


class Nhentai_chinese(Nhentai):
    id = 'nhentai_chinese'
    lang = 'zh_Hans'
    lang_code = 'chinese'


class Nhentai_japanese(Nhentai):
    id = 'nhentai_japanese'
    lang = 'ja'
    lang_code = 'japanese'
