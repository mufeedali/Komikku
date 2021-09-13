# -*- coding: utf-8 -*-

# Copyright (C) 2020 Liliana Prikler
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Liliana Prikler <liliana.prikler@gmail.com>

from bs4 import BeautifulSoup
from gettext import gettext as _
import json
import logging
from operator import itemgetter
import requests

from gi.repository import GLib

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT

logger = logging.getLogger('komikku.servers.bilibili')

SEARCH_RESULTS_LIMIT=10


class Bilibili(Server):
    lang = 'en'
    id = 'bilibili'
    name = 'Bilibili'

    base_url = 'https://www.bilibilicomics.com'
    manga_url = 'https://www.bilibilicomics.com/detail/mc{}'

    query_params = "?device=pc&platform=web"

    api_base_url = base_url + '/twirp/comic.v1.Comic'
    api_most_populars_url = api_base_url + '/ClassPage' + query_params
    api_search_url = api_base_url + '/Search' + query_params
    api_manga_url = api_base_url + '/ComicDetail' + query_params
    api_chapter_url = api_base_url + '/GetImageIndex' + query_params
    api_image_token_url = api_base_url + '/ImageToken' + query_params

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT,
                                         'referer': self.base_url,
                                         'accept': 'application/json, text/plain, */*'})

    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        r = self.session_post(self.api_manga_url,
                              json=dict(
                                  comic_id=int(initial_data['slug'])
                              ))
        if r.status_code != 200:
            return None

        json_data = r.json()['data']

        data = initial_data.copy()
        data.update(dict(
            name=json_data['title'],
            synopsis=json_data['evaluate'],
            authors=json_data['author_name'],
            scanlators=[],
            genres=json_data['styles'],
            status='completed' if json_data['is_finish'] else 'ongoing',
            cover=json_data['vertical_cover'],
            chapters=[
                dict(slug=str(ep['id']),
                     title='#{} - {}'.format(ep['short_title'], ep['title']),
                     date=convert_date_string(ep['pub_time']))
                for ep in sorted(json_data['ep_list'], key=itemgetter('ord'))
            ],
            server_id=self.id
        ))

        return data

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data from API

        Currently, only pages are expected.
        """
        r = self.session_post(self.api_chapter_url, json=dict(ep_id=int(chapter_slug)))
        if r.status_code == 404:
            raise NotFoundError
        if r.status_code != 200:
            return None

        images = r.json()['data']['images']

        data = dict(
            pages=[dict(slug=image['path'], image=None) for image in images]
        )

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        r = self.session_post(self.api_image_token_url, json=dict(urls='["{}"]'.format(page['slug'])))

        if r.status_code != 200:
            return None

        page = r.json()['data'][0]

        r = self.session_get(page['url'],
                             params=dict(token=page['token']),
                             headers=dict(user_agent=USER_AGENT,
                                          referer=self.base_url))

        print (r, r.text)

        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page['slug'].split('/')[1],
        )

    def get_most_populars(self):
        r = self.session_post(self.api_most_populars_url,
                              json=dict(
                                  area_id=-1,
                                  is_finish=-1,
                                  is_free=1,
                                  order=0,
                                  page_num=1,
                                  page_size=2*SEARCH_RESULTS_LIMIT,
                                  style_id=-1,
                                  style_prefer="[]"
                              ))

        if r.status_code != 200:
            return None

        results = []
        for manga in r.json()['data']:
            results.append(dict(
                slug=manga['season_id'],
                name=manga['title']
            ))

        return results

    def search(self, term):
        r = self.session_post(self.api_search_url,
                              json=dict(
                                  area_id=-1,
                                  is_finish=-1,
                                  is_free=1,
                                  order=0,
                                  page_num=1,
                                  page_size=SEARCH_RESULTS_LIMIT,
                                  style_id=-1,
                                  style_prefer="[]",
                                  key_word=term
                              ))

        if r.status_code != 200:
            return None

        results = []
        for manga in r.json()['data']['list']:
            results.append(dict(
                slug=(manga['id']),
                name=BeautifulSoup(manga['title'], 'lxml').text
            ))

        return results
