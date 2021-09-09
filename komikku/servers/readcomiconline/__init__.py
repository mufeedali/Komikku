# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import requests

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT

headers = {
    'User-Agent': USER_AGENT,
    'Origin': 'https://readcomiconline.li',
}


class Readcomiconline(Server):
    id = 'readcomiconline'
    name = 'Read Comic Online'
    lang = 'en'

    base_url = 'https://readcomiconline.li'
    most_populars_url = base_url + '/ComicList/MostPopular'
    search_url = base_url + '/Search/SearchSuggest'
    manga_url = base_url + '/Comic/{0}'
    chapter_url = base_url + '/Comic/{0}/{1}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = headers

    def get_manga_data(self, initial_data):
        """
        Returns comic data by scraping manga HTML page content

        Initial data should contain at least comic's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_get(self.manga_url.format(initial_data['slug'], 1))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],  # not available
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        soup = BeautifulSoup(r.content, 'html.parser')

        info_elements = soup.find_all('div', class_='barContent')

        data['name'] = info_elements[0].div.a.text.strip()
        cover_path = info_elements[3].find('img').get('src')
        if cover_path.startswith('http'):
            data['cover'] = cover_path
        else:
            data['cover'] = '{0}{1}'.format(self.base_url, cover_path)

        for p_element in info_elements[0].find_all('p'):
            if not p_element.span:
                continue

            span_element = p_element.span.extract()
            label = span_element.text.strip()

            if label.startswith('Genres'):
                data['genres'] = [a_element.text.strip() for a_element in p_element.find_all('a')]

            elif label.startswith(('Writer', 'Artist')):
                for a_element in p_element.find_all('a'):
                    value = a_element.text.strip()
                    if value not in data['authors']:
                        data['authors'].append(value)

            elif label.startswith('Status'):
                value = p_element.text.strip()
                if 'Completed' in value:
                    data['status'] = 'complete'
                elif 'Ongoing' in value:
                    data['status'] = 'ongoing'

            elif label.startswith('Summary'):
                data['synopsis'] = p_element.text.strip()

        # Chapters (Issues)
        for tr_element in reversed(soup.find('table', class_='listing').find_all('tr')[2:]):
            td_elements = tr_element.find_all('td')

            data['chapters'].append(dict(
                slug=td_elements[0].a.get('href').split('?')[0].split('/')[-1],
                title=td_elements[0].a.text.strip(),
                date=convert_date_string(td_elements[1].text.strip(), '%m/%d/%Y'),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns comic chapter data

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
            if not script or not script.strip().startswith('function isNumber'):
                continue

            for line in script.split('\n'):
                line = line.strip()
                if not line.startswith('lstImages.push'):
                    continue

                data['pages'].append(dict(
                    slug=None,
                    image=line[16:-3],
                ))

            break

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
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
        Returns comic absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns most popular comics list
        """
        results = []

        r = self.session.get(self.most_populars_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.content, 'html.parser')

        for tr_element in soup.find('table', class_='listing').find_all('tr'):
            if tr_element.get('class') and 'head' in tr_element.get('class'):
                continue

            td_elements = tr_element.find_all('td')
            if not td_elements:
                continue

            a_element = td_elements[0].a
            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
            ))

        return results

    def search(self, term):
        results = []
        term = term.lower()

        r = self.session.post(
            self.search_url,
            data=dict(
                type='Comic',
                keyword=term
            ),
            headers={
                'x-requested-with': 'XMLHttpRequest',
                'referer': self.base_url
            }
        )
        if r.status_code != 200:
            return None
        if not r.text:
            # No results
            return results

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.content, 'html.parser')

        for a_element in soup:
            if not a_element.get('href'):
                continue

            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
            ))

        return results
