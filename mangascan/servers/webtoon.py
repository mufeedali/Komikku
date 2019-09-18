# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import dateparser
from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError
from urllib.parse import urlsplit

from mangascan.servers import Server
from mangascan.servers import USER_AGENT
from mangascan.servers import USER_AGENT_MOBILE


server_id = 'webtoon'
server_name = 'WEBTOON'
server_lang = 'en'


class Webtoon(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.webtoons.com'
    search_url = base_url + '/search'
    manga_url = base_url + '{0}'
    chapters_url = 'https://m.webtoons.com{0}'
    chapter_url = base_url + '{0}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's url (provided by search)
        """
        assert 'url' in initial_data, 'Manga url is missing in initial data'

        try:
            r = self.session.get(self.manga_url.format(initial_data['url']), headers={'user-agent': USER_AGENT})
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
            cover=None,
        ))

        # Details
        info_element = soup.find('div', class_='info')
        for element in info_element.find_all(class_='genre'):
            if element.span:
                element.span.extract()
            data['genres'].append(element.text.strip())

        for element in info_element.find_all(class_='author'):
            if element.span:
                element.span.extract()
            if element.a:
                element.a.extract()
            data['authors'].append(element.text.strip())

        detail_element = soup.find('div', class_='detail_body')
        if 'challenge' in data['url']:
            # Challenge (Canvas)
            data['cover'] = soup.find('div', class_='detail_header').img.get('src')
        else:
            # Original
            data['cover'] = detail_element.get('style').split(' ')[1][4:-1].split('?')[0] + '?type=q90'

            status_element = detail_element.find('p', class_='day_info')
            status_element.span.extract()
            data['status'] = 'complete' if status_element.text.lower() == 'completed' else 'ongoing'

        data['synopsis'] = detail_element.find('p', class_='summary').text.strip()

        # Chapters
        data['chapters'] = self.get_manga_chapters_data(data['url'])

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        url = self.chapter_url.format(chapter_url)

        try:
            r = self.session.get(url, headers={'user-agent': USER_AGENT})
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        imgs = soup.find('div', id='_imageList').find_all('img')

        data = dict(
            pages=[],
        )
        for img in imgs:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url directly
                image=img.get('data-url').strip(),
            ))

        return data

    def get_manga_chapters_data(self, url):
        """
        Returns manga chapters data by scraping content of manga Mobile HTML page
        """
        url = self.chapters_url.format(url)

        try:
            # Use a Mobile user agent
            r = self.session.get(url, headers={'user-agent': USER_AGENT_MOBILE})
        except ConnectionError:
            return []

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return []

        soup = BeautifulSoup(r.text, 'html.parser')

        lis_elements = soup.find('ul', id='_episodeList').find_all('li', recursive=False)

        data = []
        for li_element in reversed(lis_elements):
            if li_element.get('data-episode-no') is None:
                continue

            # Small difference here compared to other servers
            # the slug can't be used to forge chapter URL, we must store the full url
            url_split = urlsplit(li_element.a.get('href'))
            data.append(dict(
                slug=url_split.path.split('/')[-2],
                title=li_element.find('p', class_='sub_title').find('span', class_='ellipsis').text.strip(),
                date=dateparser.parse(li_element.find('p', class_='date').text.strip()).date(),
                url='{0}?{1}'.format(url_split.path, url_split.query),
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        try:
            r = self.session.get(page['image'], headers={'referer': self.base_url, 'user-agent': USER_AGENT})
        except ConnectionError:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code == 200 and mime_type.startswith('image'):
            return (page['image'].split('/')[-1].split('?')[0], r.content)

        return (None, None)

    def get_manga_cover_image(self, url):
        """
        Returns manga cover (image) content
        """
        try:
            r = self.session.get(url, headers={'referer': self.base_url, 'user-agent': USER_AGENT})
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return r.content if r.status_code == 200 and mime_type.startswith('image') else None

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(url)

    def search(self, term):
        try:
            r = self.session.get(self.search_url, params=dict(keyword=term), headers={'user-agent': USER_AGENT})
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        cards = soup.find_all('a', class_=['card_item', 'challenge_item'])
        for card in cards:
            # Small difference here compared to other servers
            # the slug can't be used to forge manga URL, we must store the full url
            results.append(dict(
                slug=card.get('href').split('=')[-1],
                url=card.get('href'),
                name=card.find('p', class_='subj').text,
            ))

        return results
