# -*- coding: utf-8 -*-

# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: ISO-morphism <me@iso-morphism.name>

import json
from collections import OrderedDict
import requests

from komikku.servers import get_buffer_mime_type
from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = 'MangaHub'

headers = OrderedDict(
    [
        ('User-Agent', USER_AGENT),
        ('Accept-Language', 'en-US,en;q=0.5'),
    ]
)


# GraphQL API has a `slug` field for chapters but that is often null.
# Chapter number (a float in the api but we treat/present as string just fine)
# is required, and it seems pretty consistent that when viewing the website the actual
# url slug is `chapter-{number}`. Komikku considers chapter slug to be the key, so we store
# `chapter-{number}` as the slug, as that's likely the URL slug for the website, and remember
# to deal with `chapter-`. An alternative approach could be to stuff the number in the `url`, but
# that also feels even more dishonest. For the most part, we're just ignoring the `slug` parameter
# returned by the API.
def convert_internal_chapter_slug_to_server_chapter_number(slug):
    return slug.replace('chapter-', '')


def convert_server_chapter_number_to_internal_chapter_slug(number):
    return f'chapter-{number}'


class Mangahub(Server):
    id = 'mangahub'
    name = SERVER_NAME
    lang = 'en'
    long_strip_genres = ['Webtoon', 'Webtoons', ]

    base_url = 'https://mangahub.io'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/chapter/{0}/{1}'
    api_url = 'https://api.mghubcdn.com/graphql'
    img_url = 'https://img.mghubcdn.com/file/imghub/{0}'
    cover_url = 'https://thumb.mghubcdn.com/{0}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = headers

    def get_manga_data(self, initial_data):
        """
        Returns manga data by hitting GraphQL API.

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        query = {
            'query': '{manga(x:m01,slug:"%s"){id,title,slug,status,image,author,artist,genres,description,updatedDate,chapters{slug,title,number,date}}}'
            % initial_data['slug']
        }
        resp = self.session.post(self.api_url, json=query)
        if not resp.ok:
            return None

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

        try:
            manga = resp.json()['data']['manga']

            data['name'] = manga['title']
            data['cover'] = self.cover_url.format(manga['image'])

            for author in (s.strip() for s in manga['author'].split(',')):
                data['authors'].append(author)
            for artist in (s.strip() for s in manga['artist'].split(',')):
                if artist not in data['authors']:
                    data['authors'].append(artist)

            data['genres'].extend(genre.strip() for genre in manga['genres'].split(','))
            if manga['status'] == 'ongoing':
                data['status'] = 'ongoing'
            elif manga['status'] == 'completed':
                data['status'] = 'complete'

            data['synopsis'] = manga['description']

            for chapter in sorted(manga['chapters'], key=lambda c: c['number']):
                title = chapter['title']
                if not title:
                    title = f"Chapter {chapter['number']}"
                data['chapters'].append(dict(
                    slug=convert_server_chapter_number_to_internal_chapter_slug(chapter['number']),
                    title=title,
                    date=convert_date_string(chapter['date']),
                ))

            return data
        except Exception as e:
            print(f'{self.name}: Failed to get manga data: {e}')
            return None

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga data by hitting GraphQL API.

        Currently, only pages are expected.
        """
        query = {
            'query': '{chapter(x:m01,slug:"%s",number:%s){pages}}' % (
                manga_slug,
                convert_internal_chapter_slug_to_server_chapter_number(chapter_slug),
            )
        }
        resp = self.session.post(self.api_url, json=query)
        if not resp.ok:
            return None

        try:
            data = dict(
                pages=[],
            )

            pages = json.loads(resp.json()['data']['chapter']['pages'])
            for path in pages.values():
                data['pages'].append(dict(
                    slug=None,
                    image=self.img_url.format(path),
                ))

            return data
        except Exception as e:
            print(f'{self.name}: Failed to get chapter data: {e}')
            return None

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page['image'],
            headers={
                'Accept': 'image/webp,image/*;q=0.8,*/*;q=0.5',
                'Referer': self.chapter_url.format(manga_slug, chapter_slug),
            },
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
        Returns most popular manga list
        """
        query = {'query': '{latestPopular(x:m01){title,slug}search(x:m01,mod:POPULAR,count:true,offset:0){rows{title,slug},count}}'}
        resp = self.session.post(self.api_url, json=query)
        if not resp.ok:
            return None

        try:
            return [{'name': row['title'], 'slug': row['slug']} for row in resp.json()['data']['search']['rows']]
        except Exception as e:
            print(f'{self.name}: Failed to get most populars: {e}')
            return None

    def search(self, term):
        query = {'query': '{search(x:m01,q:"%s",limit:10){rows{title,slug}}}' % term}
        resp = self.session.post(self.api_url, json=query)
        if not resp.ok:
            return None

        try:
            return [{'name': row['title'], 'slug': row['slug']} for row in resp.json()['data']['search']['rows']]
        except Exception as e:
            print(f'{self.name}: Failed to get search results: {e}')
            return None
