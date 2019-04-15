# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests

server_id = 'hatigarmscans'
server_name = 'Hatigarm Scans'
server_lang = 'en'

base_url = 'https://www.hatigarmscans.net'
search_url = base_url + '/search'
manga_url = base_url + '/manga/{0}'
cover_url = base_url + '/uploads/manga/{0}/cover/cover_250x350.jpg'
chapter_url = base_url + '/manga/{0}/{1}'
scan_url = base_url + '/uploads/manga/{0}/chapters/{1}/{2}'


class Hatigarmscans():
    def __init__(self):
        pass

    @property
    def id(self):
        return server_id

    @property
    def name(self):
        return server_name

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Inital data should contain manga's slug and name (provided by search)
        """
        assert 'slug' in initial_data and 'name' in initial_data, 'Missing slug and/or name in initial data'

        r = requests.get(manga_url.format(initial_data['slug']))
        # print(r.text)

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            author=None,
            types=None,
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
        ))

        # Details
        elements = soup.find('dl', class_='dl-horizontal').findChildren(recursive=False)
        for element in elements:
            if element.name not in ('dt', 'dd'):
                continue

            if element.name == 'dt':
                label = element.text
                continue

            value = element.text.strip()

            if label.startswith('Author'):
                data['author'] = ', '.join([t.strip() for t in value.split(',')])
            elif label.startswith('Categories'):
                data['types'] = ', '.join([t.strip() for t in value.split(',')])
            elif label.startswith('Status'):
                # possible values: ongoing, complete, None
                data['status'] = value.lower()

        data['synopsis'] = soup.find('div', class_='well').p.text.strip()

        # Chapters
        elements = soup.find('ul', class_='chapters').find_all('li', recursive=False)
        for element in reversed(elements):
            h5 = element.h5
            if not h5:
                continue

            slug = h5.a.get('href').split('/')[-1]
            title = '{0}: {1}'.format(h5.a.text.strip(), h5.em.text.strip())
            date = element.div.div

            data['chapters'].append(dict(
                slug=slug,
                date=date.text.strip(),
                title=title
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages (list of images filenames) are expected.
        """
        url = chapter_url.format(manga_slug, chapter_slug)
        r = requests.get(url)

        soup = BeautifulSoup(r.text, 'html.parser')
        # print(r.text)

        pages_imgs = soup.find('div', id='all').find_all('img')

        data = dict(
            pages=[],
        )
        for img in pages_imgs:
            data['pages'].append(img.get('data-src').strip().split('/')[-1])

        return data

    def get_manga_chapter_page_image(self, manga_slug, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        url = scan_url.format(manga_slug, chapter_slug, page)
        r = requests.get(url)

        return r.content if r.status_code == 200 else None

    def get_manga_cover_image(self, manga_slug):
        """
        Returns manga cover (image) content
        """
        r = requests.get(cover_url.format(manga_slug))

        return r.content if r.status_code == 200 else None

    def search(self, term):
        r = requests.get(search_url, params=dict(query=term))

        # Returned data for each manga:
        # value: name of the manga
        # data: slug of the manga
        results = r.json()['suggestions']

        for result in results:
            result['slug'] = result.pop('data')
            result['name'] = result.pop('value')

        return results
