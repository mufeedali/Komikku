# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import datetime
import requests

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT


class Madara(Server):
    def __init__(self):
        self.api_url = self.base_url + 'wp-admin/admin-ajax.php'
        self.manga_url = self.base_url + 'manga/{0}/'
        self.chapter_url = self.base_url + 'manga/{0}/{1}/?style=list'

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
        data['cover'] = soup.find('div', class_='summary_image').a.img.get('data-src')
        if data['cover'] is None:
            data['cover'] = soup.find('div', class_='summary_image').a.img.get('src')

        # Details
        for element in soup.find('div', class_='summary_content').find_all('div', class_='post-content_item'):
            label = element.find('div', class_='summary-heading').text.strip()
            content_element = element.find('div', class_='summary-content')

            if label.startswith(('Author', 'Artist')):
                for a_element in content_element.find_all('a'):
                    author = a_element.text.strip()
                    if author not in data['authors']:
                        data['authors'].append(a_element.text.strip())
            elif label.startswith('Genre'):
                for a_element in content_element.find_all('a'):
                    data['genres'].append(a_element.text.strip())
            elif label.startswith('Status'):
                status = content_element.text.strip()
                if status in ('Completed', 'Completo', 'Concluído'):
                    data['status'] = 'complete'
                elif status in ('OnGoing', 'Продолжается', 'Updating', 'Em Lançamento', 'Em andamento'):
                    data['status'] = 'ongoing'

        summary_container = soup.find('div', class_='summary__content')
        if summary_container:
            if p_element := summary_container.find('p'):
                data['synopsis'] = p_element.text.strip()
            else:
                data['synopsis'] = summary_container.text.strip()

        # Chapters
        manga_id = soup.find('div', id='manga-chapters-holder').get('data-id')
        r = self.session_post(
            self.api_url,
            data=dict(
                action='manga_get_chapters',
                manga=manga_id,
            ),
            headers={
                'origin': self.base_url,
                'referer': self.manga_url.format(data['slug']),
                'x-requested-with': 'XMLHttpRequest',
            }
        )

        soup = BeautifulSoup(r.text, 'html.parser')

        elements = soup.find_all('li', class_='wp-manga-chapter')
        for element in reversed(elements):
            if date := element.span.text.strip():
                date = convert_date_string(date, format='%B %d, %Y')
            else:
                date = datetime.date.today().strftime('%Y-%m-%d')

            data['chapters'].append(dict(
                slug=element.a.get('href').split('/')[-2],
                title=element.a.text.strip(),
                date=date,
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
        for img_element in soup.find_all('img', class_='wp-manga-chapter-img'):
            img_url = img_element.get('data-src')
            if img_url is None:
                img_url = img_element.get('src')

            data['pages'].append(dict(
                slug=None,
                image=img_url,
            ))

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
            name=page['image'].split('/')[-1],
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
        return self.search('', True)

    def search(self, term, populars=False):
        data = {
            'action': 'madara_load_more',
            'page': 0,
            'template': 'madara-core/content/content-archive' if populars else 'madara-core/content/content-search',
            'vars[paged]': 1,
            'vars[orderby]': 'meta_value_num' if populars else '',
            'vars[template]': 'archive' if populars else 'search',
            'vars[sidebar]': 'right' if populars else 'full',
            'vars[post_type]': 'wp-manga',
            'vars[post_status]': 'publish',
            'vars[meta_query][relation]': 'OR',
            'vars[manga_archives_item_layout]': 'big_thumbnail',
        }
        if populars:
            data['vars[order]'] = 'desc'
            data['vars[posts_per_page]'] = 100
            data['vars[meta_key]'] = '_wp_manga_views'
        else:
            data['vars[s]'] = term
            data['vars[meta_query][0][relation]'] = 'AND'

        r = self.session_post(self.api_url, data=data)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for element in soup.find_all('div', class_='post-title'):
            a_element = element.h3.a
            results.append(dict(
                slug=a_element.get('href').split('/')[-2],
                name=a_element.text.strip(),
            ))

        return results


class Aloalivn(Madara):
    id = 'aloalivn:madara'
    name = 'Aloalivn'
    lang = 'en'

    base_url = 'https://aloalivn.com/'


class Apollcomics(Madara):
    id = 'apollcomics:madara'
    name = 'Apoll Comics'
    lang = 'es'

    base_url = 'https://apollcomics.xyz/'


class Wakascan(Madara):
    id = 'wakascan:madara'
    name = 'Wakascan'
    lang = 'fr'

    base_url = 'https://wakascan.com/'
