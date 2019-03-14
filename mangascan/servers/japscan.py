from bs4 import BeautifulSoup
import cfscrape

from mangascan.servers import Server

server_id = 'japscan'
server_name = 'JapScan'
server_country = 'fr'

base_url = 'https://www.japscan.to'
search_url = base_url + '/search/'
manga_url = base_url + '/manga/{0}/'
cover_url = base_url + '/imgs/mangas/{0}.jpg'
chapter_url = base_url + '/lecture-en-ligne/{0}/{1}/'
scan_url = 'https://c.japscan.to/lel/{0}/{1}/{2}'


class Japscan(Server):
    __server_name__ = server_name

    def __init__(self):
        self.session = cfscrape.create_scraper()
        # self.headers = {'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_4 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B554a Safari/9537.53'}
        # self.session.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:64.0) Gecko/20100101 Firefox/64.0'

    @property
    def id(self):
        return server_id

    @property
    def name(self):
        return self.__server_name__

    def get_manga_data(self, data):
        """
        Returns manga data by scraping manga HTML page content
        """
        r = self.session.get(manga_url.format(data['id']))
        # print(r.text)

        soup = BeautifulSoup(r.text, 'html.parser')

        data.update(dict(
            author=None,
            type=None,
            status=None,
            chapters=dict(),
            server_id=self.id,
        ))

        # Details
        card_element = soup.find_all('div', class_='card')[0]
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

            if label.startswith('Auteur'):
                data['author'] = value
            elif label.startswith('Type'):
                data['type'] = value
            elif label.startswith('Statut'):
                data['status'] = value

        # Synopsis
        data['synopsis'] = card_element.find('p', class_='list-group-item-primary').text.strip()

        # Chapters
        elements = soup.find('div', id='chapters_list').find_all('div', class_='chapters_list')
        for element in elements:
            id = element.a.get('href').split('/')[3]
            if element.a.span:
                element.a.span.extract()

            data['chapters'][id] = dict(
                id=id,
                date=element.span.text.strip(),
                title=element.a.text.strip(),
            )

        return data

    def get_manga_chapter_data(self, manga_id, chapter_id):
        """
        Returns manga chapter data by scraping chapter HTML page content
        """
        url = chapter_url.format(manga_id, chapter_id)
        r = self.session.get(url)

        soup = BeautifulSoup(r.text, 'html.parser')
        # print(r.text)

        pages_options = soup.find('select', id='pages').find_all('option')

        data = dict(
            pages=[],
        )
        for option in pages_options:
            data['pages'].append(option.get('data-img'))

        return data

    def get_manga_chapter_page_image(self, manga_id, chapter_id, page):
        """
        Returns chapter page scan (image) content
        """
        manga_id = '-'.join(w.capitalize() for w in manga_id.split('-'))
        chapter_id = chapter_id.capitalize()

        url = scan_url.format(manga_id, chapter_id, page)
        r = self.session.get(url)

        return r.content if r.status_code == 200 else None

    def get_manga_cover_image(self, manga_id):
        """
        Returns manga cover (image) content
        """
        manga_id = '-'.join(w.capitalize() for w in manga_id.split('-'))
        r = self.session.get(cover_url.format(manga_id))

        return r.content

    def search(self, term):
        r = self.session.post(search_url, data=dict(search=term))

        # Returned data for each manga:
        # name:  name of the manga
        # image: relative path of cover image
        # url:   relative path of manga page
        results = r.json()

        for result in results:
            # Extract id from url
            result['id'] = result.pop('url').split('/')[2]
            result.pop('image')

        return results
