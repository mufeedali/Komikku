# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import functools
import logging
import requests
import time

from gi.repository import GLib
from gi.repository import WebKit2

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import headless_browser
from komikku.servers import Server
from komikku.servers import USER_AGENT

logger = logging.getLogger('komikku.servers.mangafreak')

SERVER_NAME = 'MangaFreak'


def bypass_cloudflare(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        server = args[0]
        if server.session:
            return func(*args, **kwargs)

        cf_reload_count = -1
        done = False
        error = None

        def load_page():
            settings = dict(
                auto_load_images=False,
            )
            if not headless_browser.open(server.base_url, user_agent=USER_AGENT, settings=settings):
                return True

            headless_browser.connect_signal('load-changed', on_load_changed)
            headless_browser.connect_signal('load-failed', on_load_failed)
            headless_browser.connect_signal('notify::title', on_title_changed)

        def on_load_changed(webview, event):
            nonlocal cf_reload_count
            nonlocal error

            if event != WebKit2.LoadEvent.FINISHED:
                return

            cf_reload_count += 1
            if cf_reload_count > 20:
                error = 'Max Cloudflare reload exceeded'
                headless_browser.close()
                return

            # Detect end of Cloudflare challenge via JavaScript
            js = """
                const checkCF = setInterval(() => {
                    if (!document.getElementById('cf-content')) {
                        clearInterval(checkCF);
                        document.title = 'ready';
                    }
                }, 100);
            """
            headless_browser.webview.run_javascript(js, None, None)

        def on_load_failed(_webview, _event, _uri, gerror):
            nonlocal error

            error = f'Failed to load homepage: {server.base_url}'

            headless_browser.close()

        def on_title_changed(webview, title):
            if headless_browser.webview.props.title != 'ready':
                return

            cookie_manager = headless_browser.web_context.get_cookie_manager()
            cookie_manager.get_cookies(server.base_url, None, on_get_cookies_finish, None)

        def on_get_cookies_finish(cookie_manager, result, user_data):
            nonlocal done

            server.session = requests.Session()
            server.session.headers.update({'user-agent': USER_AGENT})

            for cookie in cookie_manager.get_cookies_finish(result):
                rcookie = requests.cookies.create_cookie(
                    name=cookie.name,
                    value=cookie.value,
                    domain=cookie.domain,
                    path=cookie.path,
                    expires=cookie.expires.to_time_t() if cookie.expires else None,
                )
                server.session.cookies.set_cookie(rcookie)

            done = True
            headless_browser.close()

        GLib.timeout_add(100, load_page)

        while not done and error is None:
            time.sleep(.1)

        if error:
            logger.warning(error)
            raise requests.exceptions.RequestException()

        return func(*args, **kwargs)

    return wrapper


class Mangafreak(Server):
    id = 'mangafreak'
    name = SERVER_NAME
    lang = 'en'

    base_url = 'https://w11.mangafreak.net'
    search_url = base_url + '/Search/{0}'
    most_populars_url = base_url
    manga_url = base_url + '/Manga/{0}'
    chapter_url = base_url + '/{0}'
    image_url = 'https://images.mangafreak.net/mangas/{0}'

    def __init__(self):
        self.session = None

    @bypass_cloudflare
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
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        details_container_element = soup.find('div', class_='manga_series_data')

        # Name & cover
        data['name'] = details_container_element.h5.text.strip()
        data['cover'] = soup.find('div', class_='manga_series_image').img.get('src')

        # Details
        details_elements = details_container_element.find_all('div')

        status = details_elements[1].text.strip()
        if status == 'COMPLETED':
            data['status'] = 'complete'
        elif status == 'ON-GOING':
            data['status'] = 'ongoing'

        author = details_elements[2].text.strip()
        if author:
            data['authors'].append(author)
        author = details_elements[3].text.strip()
        if author:
            data['authors'].append(author)

        for a_element in details_elements[5].find_all('a'):
            data['genres'].append(a_element.text.strip())

        # Synopsis
        data['synopsis'] = soup.find('div', class_='manga_series_description').p.text.strip()

        # Chapters
        for tr_element in soup.find('div', class_='manga_series_list').find_all('tr')[1:]:
            tds_elements = tr_element.find_all('td')

            slug = tds_elements[0].a.get('href').split('/')[-1]
            title = tds_elements[0].a.text.strip()
            date = tds_elements[1].text.strip()

            data['chapters'].append(dict(
                slug=slug,
                title=title,
                date=convert_date_string(date, format='%Y/%m/%d'),
            ))

        return data

    @bypass_cloudflare
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(chapter_slug))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = dict(
            pages=[],
        )
        for div_element in soup.find('div', class_='slideshow-container').find_all('div', class_='mySlides'):
            data['pages'].append(dict(
                slug='/'.join(div_element.img.get('src').split('/')[-3:]),
                image=None,
            ))

        return data

    @bypass_cloudflare
    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            self.image_url.format(page['slug']),
            headers={
                'referer': self.chapter_url.format(chapter_slug)
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
            name=page['slug'].split('/')[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    @bypass_cloudflare
    def get_most_populars(self):
        """
        Returns featured manga list
        """
        r = self.session_get(self.most_populars_url)
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for element in soup.find('div', class_='featured_list').find_all('div', class_='featured_item_info'):
            results.append(dict(
                name=element.a.text.strip(),
                slug=element.a.get('href').split('/')[-1],
            ))

        return results

    @bypass_cloudflare
    def search(self, term):
        r = self.session_get(self.search_url.format(term))
        if r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for item in soup.find_all('div', class_='manga_search_item'):
            a_element = item.find('h3').a

            results.append(dict(
                slug=a_element.get('href').strip().split('/')[-1],
                name=a_element.text.strip(),
            ))

        return results
