# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError
from urllib.parse import urlsplit

from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT
from komikku.servers import USER_AGENT_MOBILE

LANGUAGES_CODES = dict(
    en='en',
    id='id',
    th='th',
    zh_HANT='zh-hant',
)

server_id = 'webtoon'
server_name = 'WEBTOON'
server_lang = 'en'


class Webtoon(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.webtoons.com'
    search_url = base_url + '/search'
    popular_url = base_url + '/{0}/top'
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

        # Get true URL after redirects
        split_url = urlsplit(r.url)
        url = '{0}?{1}'.format(split_url.path, split_url.query)

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            url=url,
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

            # Status
            value = detail_element.find('p', class_='day_info').text.strip()
            if value.find('COMPLETED') >= 0:
                data['status'] = 'complete'
            elif value.find('UP') >= 0:
                data['status'] = 'ongoing'

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

        li_elements = soup.find('ul', id='_episodeList').find_all('li', recursive=False)

        data = []
        for li_element in reversed(li_elements):
            if li_element.get('data-episode-no') is None:
                continue

            date_element = li_element.find('p', class_='date')
            if date_element.span:
                date_element.span.decompose()

            # Small difference here compared to other servers
            # the slug can't be used to forge chapter URL, we must store the full url
            url_split = urlsplit(li_element.a.get('href'))

            data.append(dict(
                slug=url_split.query,
                title=li_element.find('p', class_='sub_title').find('span', class_='ellipsis').text.strip(),
                date=convert_date_string(date_element.text.strip(), format='%b %d, %Y'),
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

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(url)

    def get_popular(self):
        """
        Returns TOP 10 manga
        """
        try:
            r = self.session.get(self.popular_url.format(LANGUAGES_CODES[self.lang]))
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for li_element in soup.find('ul', class_='lst_type1').find_all('li'):
            results.append(dict(
                name=li_element.a.find('p', class_='subj').text.strip(),
                slug=li_element.a.get('href').split('=')[-1],
            ))

        return results

    def search(self, term):
        try:
            referer_url = '{0}/{1}'.format(self.base_url, LANGUAGES_CODES[self.lang])
            self.session.get(referer_url)
        except ConnectionError:
            return None

        results = None

        webtoon_results = self.search_by_type(term, 'WEBTOON')
        if webtoon_results is not None:
            results = webtoon_results

        challenge_results = self.search_by_type(term, 'CHALLENGE')
        if challenge_results is not None:
            if results is None:
                results = challenge_results
            else:
                results += challenge_results

        return results

    def search_by_type(self, term, type):
        assert type in ('CHALLENGE', 'WEBTOON', ), 'Invalid type'

        try:
            r = self.session.get(
                self.search_url,
                params=dict(keyword=term, type=type),
            )
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        if type == 'CHALLENGE':
            a_elements = soup.find_all('a', class_='challenge_item')
        elif type == 'WEBTOON':
            a_elements = soup.find_all('a', class_='card_item')

        results = []
        for a_element in a_elements:
            # Small difference here compared to other servers
            # the slug can't be used to forge manga URL, we must store the full url
            results.append(dict(
                slug=a_element.get('href').split('=')[-1],
                url=a_element.get('href'),
                name=a_element.find('p', class_='subj').text.strip(),
            ))

        return results
