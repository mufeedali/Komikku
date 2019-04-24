from bs4 import BeautifulSoup
import requests

server_id = 'scanvf'
server_name = 'Scanvf'
server_lang = 'fr'

session = None


class Scanvf():
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://scanvf.com'
    search_url = base_url + '/search.php'
    manga_url = base_url + '/{0}'
    chapter_url = base_url + '/{0}'
    page_url = base_url + '/{0}/{1}'
    image_url = base_url + '/{0}'
    cover_url = base_url + '/{0}'

    def __init__(self):
        global session

        if session is None:
            session = requests.Session()

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Inital data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        r = session.get(self.manga_url.format(initial_data['slug']))

        soup = BeautifulSoup(r.text, 'lxml')

        data = initial_data.copy()
        data.update(dict(
            author=None,
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover_path='photos/{}.png'.format(data['slug'].replace('mangas-', '')),
        ))

        # Details
        elements = soup.find_all('div', class_='col-md-9')[0].find_all('p')
        for element in elements:
            label = element.span.extract().text.strip()
            value = element.text[3:].strip()

            if label.startswith('Auteur'):
                data['author'] = value
            elif label.startswith('Statu'):
                # possible values: ongoing, complete
                data['status'] = 'ongoing' if value == 'en cours' else 'complete'
            elif label.startswith('synopsis'):
                data['synopsis'] = value

        # Chapters
        elements = soup.find_all('div', class_='list-group')[0].find_all('a', recursive=False)
        for element in reversed(elements):
            element.i.extract()

            slug = element.get('href').split('/')[-1]
            title = element.text.strip().replace('Scan ', '')

            data['chapters'].append(dict(
                slug=slug,
                title=title,
                date=None,
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages are expected.
        """
        url = self.chapter_url.format(chapter_slug)
        r = session.get(url)

        soup = BeautifulSoup(r.text, 'lxml')

        options_elements = soup.find_all('select')[2].find_all('option')

        data = dict(
            pages=[],
        )
        for option_element in options_elements:
            data['pages'].append(dict(
                slug=option_element.get('value').strip().split('/')[-1],
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        # Scrap HTML page to get image path
        url = self.page_url.format(chapter_slug, page['slug'])
        r = session.get(url)

        soup = BeautifulSoup(r.text, 'lxml')
        path = soup.find('img', class_='img-fluid').get('src')
        imagename = url.split('/')[-1]

        # Get scan image
        r = session.get(self.image_url.format(path))

        return (imagename, r.content) if r.status_code == 200 else (None, None)

    def get_manga_cover_image(self, cover_path):
        """
        Returns manga cover (image) content
        """
        r = session.get(self.cover_url.format(cover_path))

        return r.content if r.status_code == 200 else None

    def search(self, term):
        r = session.get(self.search_url, params=dict(key=term, send='Recherche'))

        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        a_elements = soup.find('div', class_='col-lg-8').find_all('a')
        for a_element in a_elements:
            results.append(dict(
                slug=a_element.get('href'),
                name=a_element.text,
            ))

        return results
