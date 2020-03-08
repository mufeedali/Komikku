# -*- coding: utf-8 -*-

# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import cloudscraper
import json
import magic

from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT

# All theses servers use Genkan CMS


class Genkan(Server):
    def __init__(self):
        if self.session is None:
            self.session = cloudscraper.create_scraper()
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

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[self.name, ],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = soup.find_all('h5')[0].text.strip()
        data['cover'] = self.image_url.format(soup.find('div', class_='media-comic-card').a.get('style').split('(')[-1][:-1])

        # Details
        data['synopsis'] = soup.find('div', class_='col-lg-9').contents[2].strip()

        # Chapters
        elements = soup.find('div', class_='list list-row row').find_all('div', class_='list-item')
        for element in reversed(elements):
            a_elements = element.find_all('a')

            slug = '/'.join(a_elements[0].get('href').split('/')[-2:])
            title = '#{0} - {1}'.format(element.span.text.strip(), a_elements[0].text.strip())
            date = a_elements[1].text.strip()

            data['chapters'].append(dict(
                slug=slug,
                date=convert_date_string(date),
                title=title,
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        r = self.session_get(self.chapter_url.format(manga_slug, chapter_slug))
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = dict(
            pages=[],
        )
        for script_element in soup.find_all('script'):
            if script_element.string is None or not script_element.string.startswith('window.disqusName'):
                continue

            for line in script_element.string.split(';'):
                line = line.strip()
                if not line.startswith('window.chapterPages'):
                    continue

                images = json.loads(line.split('=')[1].strip())
                for image in images:
                    data['pages'].append(dict(
                        slug=None,
                        image=image,
                    ))
                break
            break

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(self.image_url.format(page['image']))
        if r is None:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)
        image_name = page['image'].split('/')[-1]

        return (image_name, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def search(self, term):
        r = self.session_get(self.search_url.format(term))
        if r is None:
            return None

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')

            results = []
            for a_element in soup.find_all('a', class_='list-title ajax'):
                results.append(dict(
                    slug=a_element.get('href').split('/')[-1],
                    name=a_element.text.strip(),
                ))

            return results
        else:
            return None


class GenkanInitial(Genkan):
    """
    The initial version of the CMS doesn't provide search
    """

    def search(self, term):
        r = self.session_get(self.search_url)
        if r is None:
            return None

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')

            results = []
            for a_element in soup.find_all('a', class_='list-title ajax'):
                name = a_element.text.strip()
                if term.lower() not in name.lower():
                    continue

                results.append(dict(
                    slug=a_element.get('href').split('/')[-1],
                    name=name,
                ))

            return results
        else:
            return None


class Edelgardescans(Genkan):
    id = 'edelgardescans:genkan'
    name = 'Edelgarde Scans'
    lang = 'en'

    base_url = 'https://edelgardescans.com'
    search_url = base_url + '/comics?query={0}'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Hatigarmscans(GenkanInitial):
    id = 'hatigarmscans:genkan'
    name = 'Hatigarm Scans'
    lang = 'en'

    base_url = 'https://hatigarmscanz.net'
    search_url = base_url + '/comics'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Hunlightscans(Genkan):
    id = 'hunlightscans:genkan'
    name = 'Hunlight Scans'
    lang = 'en'

    base_url = 'https://hunlight-scans.info'
    search_url = base_url + '/comics?query={0}'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Leviatanscans(Genkan):
    id = 'leviatanscans:genkan'
    name = 'Leviatan Scans'
    lang = 'en'

    base_url = 'https://leviatanscans.com'
    search_url = base_url + '/comics?query={0}'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Leviatanscans_es(GenkanInitial):
    id = 'leviatanscans_es:genkan'
    name = 'Leviatan Scans'
    lang = 'es'

    # Search is broken -> inherit from GenkanInitial instead of Genkan class

    base_url = 'https://es.leviatanscans.com'
    search_url = base_url + '/comics'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Oneshotscans(Genkan):
    id = 'oneshotscans:genkan'
    name = 'One Shot Scans'
    lang = 'en'

    base_url = 'https://oneshotscans.com'
    search_url = base_url + '/comics?query={0}'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Reaperscans(GenkanInitial):
    id = 'reaperscans:genkan'
    name = 'Reaper Scans'
    lang = 'en'

    # Use Cloudflare
    # Search is partially broken -> inherit from GenkanInitial instead of Genkan class

    base_url = 'https://reaperscans.com'
    search_url = base_url + '/comics'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Thenonamesscans(Genkan):
    id = 'thenonamesscans:genkan'
    name = 'The Nonames Scans'
    lang = 'en'

    base_url = 'https://the-nonames.com'
    search_url = base_url + '/comics?query={0}'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Zeroscans(Genkan):
    id = 'zeroscans:genkan'
    name = 'Zero Scans'
    lang = 'en'

    base_url = 'https://zeroscans.com'
    search_url = base_url + '/comics?query={0}'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'
