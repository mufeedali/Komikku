# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: ISO-morphism <me@iso-morphism.name>

from bs4 import BeautifulSoup
import json
import logging
import requests
import time

from gi.repository import GLib
from gi.repository import WebKit2

from komikku.servers import get_buffer_mime_type
from komikku.servers import convert_date_string
from komikku.servers import get_soup_element_inner_text
from komikku.servers import headless_browser
from komikku.servers import Server
from komikku.servers import USER_AGENT

headers = {
    'User-Agent': USER_AGENT,
}
logger = logging.getLogger('komikku.servers.mangahub')

SERVER_NAME = 'MangaHub'


def get_chapter_page_html(url):
    error = None
    html = None

    def load_page():
        settings = dict(
            auto_load_images=False,
        )
        if not headless_browser.open(server.base_url, user_agent=USER_AGENT, settings=settings):
            return True

        headless_browser.connect_signal('load-changed', on_load_changed)
        headless_browser.connect_signal('load-failed', on_load_failed)
        headless_browser.connect_signal('notify::title', on_title_changed)

    def on_get_html_finish(webview, result, user_data=None):
        nonlocal error
        nonlocal html

        js_result = webview.run_javascript_finish(result)
        if js_result:
            js_value = js_result.get_js_value()
            if js_value:
                html = js_value.to_string()

        if html is None:
            error = f'Failed to get chapter page html: {url}'

        headless_browser.close()

    def on_load_changed(_webview, event):
        if event != WebKit2.LoadEvent.FINISHED:
            return

        # Wait until all images are inserted in DOM
        # Only 3 are inserted at page load, others are added later via AJAX
        js = """
            const checkReady = setInterval(() => {
                if (document.querySelectorAll('._2aWyJ .hidden').length === 0) {
                    clearInterval(checkReady);
                    document.title = 'ready';
                }
            }, 100);
        """

        headless_browser.webview.run_javascript(js, None, None, None)

    def on_load_failed(_webview, _event, _uri, gerror):
        nonlocal error

        error = f'Failed to load chapter page: {url}'

        headless_browser.close()

    def on_title_changed(_webview, _title):
        if headless_browser.webview.props.title == 'ready':
            # All images have been inserted in DOM, we can retrieve page HTML
            headless_browser.webview.run_javascript('document.documentElement.outerHTML', None, on_get_html_finish, None)

    GLib.timeout_add(100, load_page)

    while html is None and error is None:
        time.sleep(.1)

    if error:
        logger.warning(error)
        raise requests.exceptions.RequestException()

    return html


class Mangahub(Server):
    id = 'mangahub'
    name = SERVER_NAME
    lang = 'en'
    long_strip_genres = ['Webtoon', 'Webtoons', ]

    base_url = 'https://mangahub.io'
    search_url = base_url + '/search'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/chapter/{0}/{1}'
    api_url = 'https://api.mghubcdn.com/graphql'
    image_url = 'https://img.mghubcdn.com/file/imghub/{0}'

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

        r = self.session.get(self.manga_url.format(initial_data['slug']))
        if r.status_code != 200:
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

        data['name'] = get_soup_element_inner_text(soup.find('h1'))
        data['cover'] = soup.find('img', class_='manga-thumb').get('src')

        # Details
        for element in soup.find_all('span', class_='_3SlhO'):
            label = element.text.strip()

            if label.startswith('Author'):
                data['authors'] = [a.strip() for a in element.next_sibling.text.split(';')]

            elif label.startswith('Artist'):
                for a in element.next_sibling.text.split(';'):
                    if a.strip() not in data['authors']:
                        data['authors'].append(a.strip())

            elif label.startswith('Status'):
                status = element.next_sibling.text.strip()
                if status == 'Completed':
                    data['status'] = 'complete'
                else:
                    data['status'] = 'ongoing'

        for a_element in soup.find('p', class_='_3Czbn'):
            data['genres'].append(a_element.text.strip())

        data['synopsis'] = soup.find('p', class_='ZyMp7').text.strip()

        # Chapters
        for ul_element in reversed(soup.find_all('ul', class_='list-group')):
            for li_element in reversed(ul_element.find_all('li', class_='list-group-item')):
                date_text = li_element.find(class_='UovLc').text.strip()
                date_format = '%Y-%m-%d' if len(date_text) == 10 else None

                data['chapters'].append(dict(
                    slug=li_element.a.get('href').split('/')[-1],
                    title=li_element.find('span', class_='text-secondary').text.strip(),
                    date=convert_date_string(date_text, date_format),
                ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns chapter's data via GraphQL API or headless browser + HTML parsing

        Currently, only pages are expected.
        """
        query = {
            'query': '{chapter(x:m01,slug:"%s",number:%s){pages}}' % (
                manga_slug,
                chapter_slug.replace('chapter-', ''),
            )
        }
        r = self.session.post(self.api_url, json=query)

        data = dict(
            pages=[],
        )

        if r.status_code == 200:
            try:
                pages = json.loads(r.json()['data']['chapter']['pages'])
                for path in pages.values():
                    data['pages'].append(dict(
                        slug=path,
                        image=None,
                    ))
            except Exception as e:
                logger.warning(f'Failed to get chapter data: {self.name} - {e}')

                return None
        else:
            # Alternative: retrieve chapter page HTML using headless browser
            html = get_chapter_page_html(self.chapter_url.format(manga_slug, chapter_slug))

            soup = BeautifulSoup(html, 'html.parser')

            for img_element in soup.find_all('img', class_='PB0mN'):
                data['pages'].append(dict(
                    slug='/'.join(img_element.get('src').split('/')[-3:]),
                    image=None,
                ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            self.image_url.format(page['slug']),
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
            name=page['slug'].split('/')[-1],
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
        return self.search('', populars=True)

    def search(self, term, populars=False):
        params = dict(
            q=term,
            genres='all',
            order='POPULAR' if populars else 'ALPHABET',
        )

        r = self.session_get(self.search_url, params=params)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for h_element in soup.find_all('h4', class_='media-heading'):
            results.append(dict(
                slug=h_element.a.get('href').split('/')[-1],
                name=h_element.a.text.strip(),
            ))

        return results
