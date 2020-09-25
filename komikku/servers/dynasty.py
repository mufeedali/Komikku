# -*- coding: utf-8 -*-

# Copyright (C) 2020 Leo Prikler
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Leo Prikler <leo.prikler@student.tugraz.at>

from bs4 import BeautifulSoup
from gettext import gettext as _
import json
import requests

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT


class Dynasty(Server):
    lang = 'en'
    id = 'dynasty'
    name = 'Dynasty'

    base_url = 'https://dynasty-scans.com'
    manga_url = base_url + '/{0}'
    search_url = base_url + '/search'
    chapter_url = base_url + '/chapters/{0}'
    tags_url = base_url + '/tags/suggest/'

    filters = [
        {
            'key': 'classes',
            'type': 'select',
            'name': _('Categories'),
            'description': _('Types of manga to search for'),
            'value_type': 'multiple',
            'options': [
                {'key': 'Anthology', 'name': _('Anthology'), 'default': True},
                {'key': 'Doujin', 'name': _('Doujins'), 'default': True},
                {'key': 'Issue', 'name': _('Issues'), 'default': True},
                {'key': 'Series', 'name': _('Series'), 'default': True},
            ],
        },
        {
            'key': 'with_tags',
            'type': 'entry',
            'name': _('With Tags'),
            'description': _('Tags to search for'),
            'default': '',
        },
        {
            'key': 'without_tags',
            'type': 'entry',
            'name': _('Without Tags'),
            'description': _('Tags to exclude from search'),
            'default': '',
        },
    ]

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
        if r is None:
            return None

        mime_type = get_buffer_mime_type(r.content)

        if r.status_code != 200 or mime_type != 'text/html':
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

        name_element = soup.find('h2', class_='tag-title')
        data['name'] = name_element.b.text.strip()
        if name_element.find('a'):
            data['authors'] = [name_element.a.text.strip()]

        if name_element.find('small'):
            # Status may contain additional information, such as 'Licensed'
            status = name_element.small.text.split(' ')
            if 'Ongoing' in status:
                data['status'] = 'ongoing'
            elif 'Completed' in status:
                data['status'] = 'complete'

        try:
            cover_rel = soup.find('div', class_='cover').find('img')['src']
            data['cover'] = self.base_url + cover_rel
        except AttributeError:  # relative cover not found
            pass

        try:
            elements = soup.find('div', class_='description').find_all('p')
            data['synopsis'] = "\n\n".join([p.text.strip() for p in elements])
        except AttributeError:  # no synopsis
            pass

        elements = soup.find('div', class_='tag-tags').find_all('a', class_='label')
        for element in elements:
            value = element.text.strip()
            if value not in data['genres']:
                data['genres'].append(value)

        elements = soup.find('dl', class_='chapter-list').find_all('dd')
        for element in elements:
            a_element = element.find('a')
            date_text = None
            for small in element.find_all('small'):
                small = small.text.strip()
                if small.startswith('released'):
                    date_text = small[len('released'):]

            data['chapters'].append(dict(
                slug=a_element.get('href').split('/')[-1],
                title=a_element.text.strip(),
                date=convert_date_string(date_text),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(chapter_slug))
        if r is None:
            return None

        mime_type = get_buffer_mime_type(r.content)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        pages = None
        for script_element in soup.find_all('script'):
            script = script_element.string
            if script is None:
                continue

            for line in script.split('\n'):
                line = line.strip()
                if line.startswith('var pages'):
                    pages = line.replace('var pages = ', '')[:-1]
                    break
            if pages is not None:
                pages = json.loads(pages)
                break

        if pages is None:
            return None

        data = dict(
            pages=[],
        )
        for page in pages:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url directly
                image=self.base_url + page['image'],
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
            name=page['image'].split('?')[0].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def resolve_tag(self, search_tag):
        r = self.session_post(self.tags_url, params=dict(query=search_tag))
        if r is None:
            return None

        tag_id = None
        if r.status_code == 200:
            for tag in r.json():
                if tag['name'].lower() == search_tag.lower():
                    tag_id = tag['id']
                    break

        return tag_id

    def search(self, term, classes=None, with_tags='', without_tags=''):
        if classes is None:
            classes = []
        classes = sorted(classes, key=str.lower)
        with_tags = [self.resolve_tag(t.strip()) for t in with_tags.split(',') if t]
        without_tags = [self.resolve_tag(t.strip()) for t in without_tags.split(',') if t]

        r = self.session_get(
            self.search_url,
            params={
                'q': term,
                'classes[]': classes,
                'with[]': with_tags,
                'without[]': without_tags,
            }
        )
        if r is None:
            return None

        if r.status_code == 200:
            try:
                results = []
                soup = BeautifulSoup(r.text, 'lxml')
                elements = soup.find('dl', class_='chapter-list').find_all('dd')

                for element in elements:
                    a_element = element.find('a', class_='name')
                    results.append(dict(
                        slug=a_element.get('href').lstrip('/'),
                        name=a_element.text.strip(),
                    ))

                return results
            except Exception:
                return None

        return None
