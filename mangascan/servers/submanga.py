from bs4 import BeautifulSoup
import requests

from mangascan.servers import Server

server_id = 'submanga'
server_name = 'Submanga'
server_country = 'es'

base_url = 'https://submanga.online'
search_url = base_url + '/search'
manga_url = base_url + '/manga/{0}'
cover_url = base_url + '/uploads/manga/{0}/cover/cover_250x350.jpg'
chapter_url = base_url + '/manga/{0}/{1}'
scan_url = base_url + '/uploads/manga/{0}/chapters/{1}/{2}'


class Submanga(Server):
    def __init__(self):
        pass

    @property
    def id(self):
        return server_id

    @property
    def name(self):
        return server_name

    def get_manga_data(self, data):
        """
        Returns manga data by scraping manga HTML page content
        """
        r = requests.get(manga_url.format(data['id']))
        # print(r.text)

        soup = BeautifulSoup(r.text, 'html.parser')

        data.update(dict(
            author=None,
            type=None,
            status=None,
            synopsis=None,
            server_id=self.id,
            chapters=dict(),
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
                data['type'] = ', '.join([t.strip() for t in value.split(',')])
            elif label.startswith('Estado'):
                data['status'] = value
            elif label.startswith('Resumen'):
                data['synopsis'] = value

        # Chapters
        elements = soup.find('div', class_='capitulos-list').find('table').find_all('tr')
        for element in elements:
            tds = element.find_all('td')

            td_link = tds[0]
            id = td_link.a.get('href').split('/')[-1]

            td_date = tds[1]
            td_date.i.extract()
            td_date.span.extract()

            data['chapters'][id] = dict(
                id=id,
                date=td_date.text.strip(),
                title=td_link.a.text.strip(),
            )

        return data

    def get_manga_chapter_data(self, manga_id, chapter_id):
        """
        Returns manga chapter data by scraping chapter HTML page content
        """
        url = chapter_url.format(manga_id, chapter_id)
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

    def get_manga_chapter_page_image(self, manga_id, chapter_id, page):
        """
        Returns chapter page scan (image) content
        """
        url = scan_url.format(manga_id, chapter_id, page)
        r = requests.get(url)

        return r.content if r.status_code == 200 else None

    def get_manga_cover_image(self, manga_id):
        """
        Returns manga cover (image) content
        """
        r = requests.get(cover_url.format(manga_id))

        return r.content

    def search(self, term):
        r = requests.get(search_url, params=dict(query=term))

        # Returned data for each manga:
        # value: name of the manga
        # data: id of the manga
        results = r.json()['suggestions']

        for result in results:
            result['id'] = result.pop('data')
            result['name'] = result.pop('value')

        return results
