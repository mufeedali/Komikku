from bs4 import BeautifulSoup
import requests

server_id = 'submanga'
server_name = 'Submanga'
server_country = 'es'

base_url = 'https://submanga.online'
search_url = base_url + '/search'
manga_url = base_url + '/manga/{0}'
cover_url = base_url + '/uploads/manga/{0}/cover/cover_250x350.jpg'
chapter_url = base_url + '/manga/{0}/{1}'
scan_url = base_url + '/uploads/manga/{0}/chapters/{1}/{2}'


class Submanga():
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
        elements = soup.find_all('span', class_='list-group-item')
        for element in elements:
            label = element.b.text
            element.b.extract()
            value = element.text.strip()

            if label.startswith('Autor'):
                data['author'] = value
            elif label.startswith('Categorías'):
                data['types'] = ', '.join([t.strip() for t in value.split(',')])
            elif label.startswith('Estado'):
                data['status'] = value
            elif label.startswith('Resumen'):
                data['synopsis'] = value

        # Chapters
        elements = soup.find('div', class_='capitulos-list').find('table').find_all('tr')
        for element in reversed(elements):
            tds = element.find_all('td')

            td_link = tds[0]
            slug = td_link.a.get('href').split('/')[-1]

            td_date = tds[1]
            td_date.i.extract()
            td_date.span.extract()

            data['chapters'].append(dict(
                slug=slug,
                date=td_date.text.strip(),
                title=td_link.a.text.strip(),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug):
        """
        Returns manga chapter data by scraping chapter HTML page content
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

        return r.content

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
