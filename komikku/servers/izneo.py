# -*- coding: utf-8 -*-

# Copyright (C) 2020 GrownNed
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: GrownNed <grownned@gmail.com>

from bs4 import BeautifulSoup
import re
import requests
import json

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server


class Izneo(Server):
    id = 'izneo'
    name = 'Izneo'
    lang = 'en'
    has_login = True

    base_url = 'https://yieha.izneo.com'
    base_reader_url = 'https://reader.izneo.com'
    login_url = base_url + '/nl/login'
    manga_data_url = base_url + '/nl/api/serie/top/{}?abo=0'
    manga_chapter_url = base_url + '/nl/api/library/detail/{0}?offset={1}&order=10&text='
    manga_cover_url = base_url + '/nl/images/album/{}-275or365.jpg?v=undefined'
    chapters_pages = base_reader_url + '/read/{}?startpage=1'
    manga_collection_url = base_url + '/nl/api/library?offset={0}&order=3&text={1}'

    def __init__(self, username=None, password=None):
        self.init(username, password)

    def get_manga_data(self, initial_data):
        """
        Returns manga data
        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Id is missing in the initial_data'
        r = self.session_get(self.manga_data_url.format(initial_data['slug']))

        json_data = r.json()
        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[json_data['gender']],
            status='ongoing',
            chapters=[],
            synopsis=json_data['synopsis'],
            cover=self.manga_cover_url.format(json_data['ean_last_album']),
            server_id=self.id,
            url=self.base_url + json_data['url'],
        ))

        # Authors
        for author in json_data['authors']:
            data['authors'].append(author['nickname'])

        # Chapters
        offset = 0
        while offset != None:
            r = self.session_get(self.manga_chapter_url.format(initial_data['slug'], offset))
            offset = offset + 1
            json_data = r.json()
            if 'albums' not in json_data:
                offset = None
            else:
                for chapter in json_data['albums'][str(offset)]:
                    data['chapters'].append(dict(
                        slug=chapter['ean'],
                        title='{0} - {1}'.format(chapter['volume'], chapter['title']),
                        date=None,
                    ))
        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapters_pages.format(chapter_slug))
        soup = BeautifulSoup(r.content, 'lxml')
        j = soup.find('script').text.strip()
        pages = json.loads(j.split('resourcesIndex               = ')[1].split(';')[0])

        data = dict(
            pages=[],
        )

        for page in pages:
            if page['id'] != 'endingpage':
                data['pages'].append(dict(
                    slug=page['id'],
                    image=self.base_reader_url + page['url'],
                ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
        if r is None or r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['slug'],
        )

    @staticmethod
    def get_manga_url(slug, url):
        """
        Returns manga absolute URL
        """
        return url

    def get_most_populars(self):
        """
        Returns best noted manga list
        """
        return self.__get_maga_collection('')

    def search(self, term):
        return self.__get_maga_collection(term)


    def __get_maga_collection(self, term):
        results = []
        offset = 0
        while offset != None:
            r = self.session_get(self.manga_collection_url.format(offset, term))
            offset = offset + 1
            json_data = r.json()
            if 'error' in json_data: # Not logged in
                offset = None
            elif 'series' not in json_data: # No more mangas to load
                offset = None
            else:
                for comic in json_data['series']:
                    results.append(dict(
                        name=comic['name'],
                        slug=comic['id'],
                    ))
        return results

    def login(self, username, password):
        """
        Log in and initializes API
        """
        if not username or not password:
            return False

        r = self.session_get(self.login_url)

        soup = BeautifulSoup(r.content, 'lxml')

        self.session_post(
            self.login_url,
            data={
                'form[username]': username,
                'form[password]': password,
                'form[remember_me]': '1',
                'form[_token]': soup.findAll('input', {u'type': u'hidden'})[0].get('value'),
            }
        )

        r = self.session_get(self.manga_collection_url.format(0, ''))
        j = r.json()
        if 'error' in j:
            return False

        self.save_session()

        return True

class Yieha(Izneo):
    id = 'yieha:izneo'
    name = 'Yieha'
    lang = 'nl'
