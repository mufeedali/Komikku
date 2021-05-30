# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
from io import BytesIO
import json
import requests
import time

from gi.repository import GLib
from gi.repository import WebKit2

from komikku.servers import headless_browser
from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import search_duckduckgo
from komikku.servers import Server
from komikku.servers import USER_AGENT


class Japscan(Server):
    id = 'japscan'
    name = 'JapScan'
    lang = 'fr'
    long_strip_genres = ['Webtoon', ]

    base_url = 'https://www.japscan.ws'
    search_url = base_url + '/manga/'
    api_search_url = base_url + '/live-search/'
    manga_url = base_url + '/manga/{0}/'
    chapter_url = base_url + '/lecture-en-ligne/{0}/{1}/'
    cover_url = base_url + '{0}'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    @classmethod
    def get_manga_initial_data_from_url(cls, url):
        return dict(slug=url.split('/')[-2])

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

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            chapters=[],
            server_id=self.id,
            synopsis=None,
        ))

        card_element = soup.find_all('div', class_='card')[0]

        # Main name: japscan handles several names for mangas (main + alternatives)
        # Name provided by search can be one of the alternatives
        # First word (Manga, Manhwa, ...) must be removed from name
        data['name'] = ' '.join(card_element.find('h1').text.strip().split()[1:])
        if data.get('cover') is None:
            data['cover'] = self.cover_url.format(card_element.find('img').get('src'))

        # Details
        if not card_element.find_all('div', class_='d-flex'):
            # mobile version
            elements = card_element.find_all('div', class_='row')[0].find_all('p')
        else:
            # desktop version
            elements = card_element.find_all('div', class_='d-flex')[0].find_all('p', class_='mb-2')

        for element in elements:
            label = element.span.text
            element.span.extract()
            value = element.text.strip()

            if label.startswith(('Auteur', 'Artiste')):
                for t in value.split(','):
                    t = t.strip()
                    if t not in data['authors']:
                        data['authors'].append(t)
            elif label.startswith('Genre'):
                data['genres'] = [genre.strip() for genre in value.split(',')]
            elif label.startswith('Statut'):
                # Possible values: ongoing, complete
                data['status'] = 'ongoing' if value == 'En Cours' else 'complete'

        # Synopsis
        synopsis_element = card_element.find('p', class_='list-group-item-primary')
        if synopsis_element:
            data['synopsis'] = synopsis_element.text.strip()

        # Chapters
        elements = soup.find('div', id='chapters_list').find_all('div', class_='chapters_list')
        for element in reversed(elements):
            if element.a.span:
                span = element.a.span.extract()
                # JapScan sometimes uploads some "spoiler preview" chapters, containing 2 or 3 untranslated pictures taken from a raw.
                # Sometimes they also upload full RAWs/US versions and replace them with a translation as soon as available.
                # Those have a span.badge "SPOILER", "RAW" or "VUS". We exclude these from the chapters list.
                if span.text.strip() in ('RAW', 'SPOILER', 'VUS', ):
                    continue

            slug = element.a.get('href').split('/')[3]

            data['chapters'].append(dict(
                slug=slug,
                title=element.a.text.strip(),
                date=convert_date_string(element.span.text.strip(), format='%d %b %Y'),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url, decode=True):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages and scrambled are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r is None:
            return None

        mime_type = get_buffer_mime_type(r.content)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        data = dict(
            pages=[],
        )

        soup = BeautifulSoup(r.text, 'html.parser')

        for option_element in soup.find('select', id='pages').find_all('option'):
            data['pages'].append(dict(
                url=option_element.get('value'),
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        error = None
        image_buffer = None

        def load_page(url):
            if not headless_browser.open(url):
                return True

            headless_browser.connect_signal('load-changed', on_load_changed)
            headless_browser.connect_signal('load-failed', on_load_failed)
            headless_browser.connect_signal('notify::title', on_title_changed)

        def on_load_changed(_webview, event):
            if event != WebKit2.LoadEvent.FINISHED:
                return

            # Clean page and return image size in webview title
            js = """
                const checkExist = setInterval(() => {
                    if (document.getElementsByTagName('CNV-VV').length) {
                        clearInterval(checkExist);
                        var e = document.body,
                            a = e.children;
                        for (e.appendChild(document.getElementsByTagName('CNV-VV')[0]);
                            'CNV-VV' != a[0].tagName;) e.removeChild(a[0]);
                        for (var t of [].slice.call(a[0].all_canvas)) t.style.maxWidth = '100%';
                        document.title = JSON.stringify({width: a[0].all_canvas[0].width, height: a[0].all_canvas[0].height});
                    }
                }, 100);
            """
            headless_browser.webview.run_javascript(js, None, None)

        def on_load_failed(_webview, _event, _uri, gerror):
            nonlocal error

            error = f'Failed to load page image: {page_url}'

            headless_browser.close()

        def on_title_changed(_webview, title):
            try:
                size = json.loads(headless_browser.webview.props.title)
            except Exception:
                return

            # Resize webview to image size
            headless_browser.webview.set_size_request(size['width'], size['height'])

            def do_snapshot():
                headless_browser.webview.get_snapshot(
                    WebKit2.SnapshotRegion.FULL_DOCUMENT, WebKit2.SnapshotOptions.NONE, None, on_snapshot_finished)

            def on_snapshot_finished(_webview, result):
                nonlocal image_buffer

                # Get image data
                surface = headless_browser.webview.get_snapshot_finish(result)
                if surface:
                    io_buffer = BytesIO()
                    surface.write_to_png(io_buffer)
                    image_buffer = io_buffer.getbuffer()
                else:
                    error = f'Failed to do page image snapshot: {page_url}'

                headless_browser.close()

            GLib.timeout_add(100, do_snapshot)

        page_url = self.base_url + page['url']
        image_name = page_url.split('/')[-1].replace('html', 'png')
        GLib.timeout_add(100, load_page, page_url)

        while image_buffer is None and error is None:
            time.sleep(.1)

        if error:
            logger.warning(error)
            raise requests.exceptions.RequestException()

        return dict(
            buffer=image_buffer,
            mime_type='image/png',
            name=image_name,
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns TOP manga
        """
        r = self.session_get(self.base_url)
        if r is None:
            return None

        mime_type = get_buffer_mime_type(r.content)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for li_element in soup.find('div', id='top_mangas_all_time').find_all('li'):
            a_element = li_element.find_all('a')[0]
            results.append(dict(
                name=a_element.text.strip(),
                slug=a_element.get('href').split('/')[-2],
            ))

        return results

    def search(self, term):
        r = self.session_post(self.api_search_url, data=dict(search=term), headers={
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Origin': self.base_url,
        })
        if r is None:
            return None

        if r.status_code == 200:
            try:
                data = r.json()

                results = []
                for item in data:
                    results.append(dict(
                        slug=item['url'].split('/')[-2],
                        name=item['name'],
                    ))

                return results
            except Exception:
                pass

        # Use DuckDuckGo Lite as fallback
        results = []
        for ddg_result in search_duckduckgo(self.search_url, term):
            # Remove first word in name (Manga, Manhua, Manhwa...)
            name = ' '.join(ddg_result['name'].split()[1:])
            # Keep only words before "|" character
            name = name.split('|')[0].strip()

            results.append(dict(
                name=name,
                slug=ddg_result['url'].split('/')[-2],
            ))

        return results
