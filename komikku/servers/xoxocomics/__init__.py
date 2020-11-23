# -*- coding: utf-8 -*-

# Copyright (C) 2019-2020 Valéry Febvre
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
    'Origin': 'https://xoxocomics.com',
}


class Xoxocomics(Server):
    id = 'xoxocomics'
    name = 'Xoxocomics'
    lang = 'en'

    base_url = 'https://xoxocomics.com'
    most_populars_url = base_url + '/popular-comics'
    search_url = base_url + '/ajax/search'
    manga_url = base_url + '/comic/{0}?page={1}'
    chapter_url = base_url + '/comic/{0}/{1}/all'

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

        data['name'] = soup.find('ul', class_='breadcrumb').find_all('a')[-1].text.strip()
        data['cover'] = soup.find(id='item-detail').find('div', class_="col-image").img.get('src')

        for li_element in soup.find('ul', class_='list-info').find_all('li'):
            if 'author' in li_element.get('class'):
                data['authors'] = [a_element.text.strip() for a_element in li_element.find_all('a')]

            elif 'kind' in li_element.get('class'):
                data['genres'] = [a_element.text.strip() for a_element in li_element.find_all('a')]

            elif 'status' in li_element.get('class'):
                status = li_element.find_all('p')[-1].text.strip()
                if status == 'Completed':
                    data['status'] = 'complete'
                elif status == 'Ongoing':
                    data['status'] = 'ongoing'

        data['synopsis'] = soup.find('div', class_='detail-content').p.text.strip()

        # Chapters
        def walk_chapters_pages(num=None, soup=None):
            if soup is None and num is not None:
                r = self.session_get(self.manga_url.format(initial_data['slug'], num))
                if r.status_code != 200:
                    return None

                mime_type = get_buffer_mime_type(r.content)
                if mime_type != 'text/html':
                    return None

                soup = BeautifulSoup(r.content, 'html.parser')

            for li_element in soup.find(id='nt_listchapter').find('ul').find_all('li'):
                if 'heading' in li_element.get('class'):
                    continue

                col_elements = li_element.find_all('div', recursive=False)

                data['chapters'].append(dict(
                    slug='/'.join(col_elements[0].a.get('href').split('/')[-2:]),
                    title=col_elements[0].a.text.strip(),
                    date=convert_date_string(col_elements[1].text.strip(), '%m/%d/%Y'),
                ))

            next_element = soup.find('a', rel='next')
            next_num = next_element.get('href')[-1] if next_element else None
            if next_num:
                walk_chapters_pages(num=next_num)

        walk_chapters_pages(soup=soup)
        data['chapters'] = list(reversed(data['chapters']))

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
        for element in soup.find_all(class_='page-chapter'):
            data['pages'].append(dict(
                slug=None,
                image=element.img.get('data-original'),
            ))

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
        return self.manga_url.format(slug, 1)

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

        for element in soup.find(class_='items').find_all(class_='item'):
            a_element = element.figure.figcaption.h3.a
            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
            ))

        return results

    def search(self, term):
        results = []
        term = term.lower()

        r = self.session.get(self.search_url, params=dict(q=term))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.content, 'html.parser')

        for a_element in soup.find_all('a'):
            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-1],
            ))

        return results
