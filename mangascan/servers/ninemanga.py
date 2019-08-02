# -*- coding: utf-8 -*-

from collections import OrderedDict
from bs4 import BeautifulSoup
import magic
import requests
from requests.exceptions import ConnectionError

server_id = 'ninemanga'
server_name = 'Nine Manga'
server_lang = 'en'

sessions = dict()
headers = OrderedDict(
    [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0'),
        ('Accept-Language', 'en-US,en;q=0.5'),
    ]
)


class Ninemanga():
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'http://www.ninemanga.com'
    search_url = base_url + '/search/ajax/'
    manga_url = base_url + '/manga/{0}.html'
    chapter_url = base_url + '/chapter/{0}/{1}'
    page_url = chapter_url
    cover_url = 'https://ta1.taadd.com{0}'

    def __init__(self):
        global sessions

        if self.id not in sessions:
            session = requests.Session()
            session.headers = headers
            sessions[self.id] = session

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Inital data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Slug is missing in initial data'

        try:
            r = sessions[self.id].get(self.manga_url.format(initial_data['slug']))
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            author=None,
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        # Details
        elements = soup.find('ul', class_='message').find_all('li')
        for element in elements:
            label = element.b.text

            if label.startswith('Author'):
                value = element.a.text.strip()
                data['author'] = value
            elif label.startswith('Genre'):
                for a_element in element.find_all('a'):
                    data['genres'].append(a_element.text)
            elif label.startswith('Status'):
                status_element = element.find_all('a')[0]
                # Allowed values: ongoing, complete, None
                value = status_element.text.strip().lower()
                if value in ('ongoing', 'en cours', 'laufende', 'en curso', 'in corso', 'em tradução'):
                    data['status'] = 'ongoing'
                elif value in ('complete', 'complété', 'abgeschlossen', 'completado', 'completato', 'completo'):
                    data['status'] = 'complete'

        # Synopsis
        synopsis_element = soup.find('p', itemprop='description')
        if synopsis_element:
            synopsis_element.b.extract()
            data['synopsis'] = synopsis_element.text.strip()

        # Chapters
        elements = soup.find('div', class_='chapterbox').find_all('li')
        for element in reversed(elements):
            slug = element.a.get('href').split('/')[-1].replace('.html', '')
            data['chapters'].append(dict(
                slug=slug,
                title=element.a.text.strip(),
                date=element.span.text.strip(),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        url = self.chapter_url.format(manga_slug, chapter_slug)

        try:
            r = sessions[self.id].get(url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')
        options_elements = soup.find('select', id='page').find_all('option')

        data = dict(
            pages=[],
        )
        for option_element in options_elements:
            data['pages'].append(dict(
                slug=option_element.get('value').split('/')[-1],
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        # Scrap HTML page to get image url
        url = self.page_url.format(manga_slug, page['slug'])

        try:
            r = sessions[self.id].get(url)
        except ConnectionError:
            return (None, None)

        soup = BeautifulSoup(r.text, 'html.parser')
        url = soup.find('img', id='manga_pic_1').get('src')
        imagename = url.split('/')[-1]

        # Get scan image
        r = sessions[self.id].get(url)
        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (imagename, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_cover_image(self, cover_path):
        """
        Returns manga cover (image) content
        """
        try:
            r = sessions[self.id].get(self.cover_url.format(cover_path))
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return r.content if r.status_code == 200 and mime_type.startswith('image') else None

    def search(self, term):
        try:
            r = sessions[self.id].get(self.search_url, params=dict(term=term))
        except ConnectionError:
            return None

        if r.status_code == 200:
            try:
                # Returned data for each manga:
                # 0: cover path
                # 1: name of the manga
                # 2: slug of the manga
                # 3: UNUSED
                # 4: UNUSED
                data = r.json(strict=False)

                results = []
                for item in data:
                    results.append(dict(
                        slug=item[2],
                        name=item[1],
                        cover=item[0],
                    ))

                return results
            except Exception:
                return None
        else:
            return None
