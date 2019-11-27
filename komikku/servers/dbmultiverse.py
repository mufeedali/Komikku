# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError
import textwrap

from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT

server_id = 'dbmultiverse'
server_name = 'Dragon Ball Multiverse'
server_lang = 'en'


class Dbmultiverse(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.dragonball-multiverse.com'
    manga_url = base_url + '/en/chapters.html'
    page_url = base_url + '/en/page-{0}.html'
    cover_url = base_url + '/image.php?comic=page&num=0&lg=en&ext=jpg&small=1&pw=8f3722a594856af867d55c57f31ee103'

    synopsis = "Dragon Ball Multiverse (DBM) is a free online comic, made by a whole team of fans. It's our personal sequel to DBZ."

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content
        """
        try:
            r = self.session.get(self.manga_url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            authors=['Gogeta Jr', 'Asura', 'Salagir'],
            scanlators=[],
            genres=['Shounen', ],
            status='ongoing',
            synopsis=self.synopsis,
            chapters=[],
            server_id=self.id,
            cover=self.cover_url,
        ))

        # Chapters
        for div_element in soup.find_all('div', class_='chapters'):
            slug = div_element.get('ch')
            if not slug:
                continue

            p_element = div_element.p

            chapter_data = dict(
                slug=slug,
                date=None,
                title=div_element.h4.text.strip(),
                pages=[],
            )

            for a_element in p_element.find_all('a'):
                chapter_data['pages'].append(dict(
                    slug=a_element.get('href')[:-5].split('-')[-1],
                    image=None,
                ))

            data['chapters'].append(chapter_data)

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga data by scraping manga HTML page content
        """
        try:
            r = self.session.get(self.manga_url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data =dict(
            pages=[],
        )
        for a_element in soup.find('div', class_='chapters', ch=chapter_slug).p.find_all('a'):
            data['pages'].append(dict(
                slug=a_element.get('href')[:-5].split('-')[-1],
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        try:
            r = self.session.get(self.page_url.format(page['slug']))
        except ConnectionError:
            return (None, None)

        soup = BeautifulSoup(r.text, 'html.parser')

        try:
            if page['slug'] == '0':
                image_url = soup.find('div', id='balloonsimg').get('style').split(';')[0].split(':')[1][4:-1]
            else:
                image_url = soup.find('img', id='balloonsimg').get('src')

            image_name = '{0}.png'.format(page['slug'])
        except Exception:
            return (None, None)

        try:
            r = self.session.get(self.base_url + image_url)
        except ConnectionError:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (image_name, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url

    def get_most_populars(self):
        return self.search()

    def search(self, term=None):
        return [dict(
            slug='dbm_{0}'.format(self.lang),
            name='Dragon Ball Multiverse (DBM)',
        )]
