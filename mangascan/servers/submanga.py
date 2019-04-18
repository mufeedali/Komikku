from bs4 import BeautifulSoup
import requests

server_id = 'submanga'
server_name = 'Submanga'
server_lang = 'es'

session = None


class Submanga():
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://submanga.online'
    search_url = base_url + '/search'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'
    image_url = base_url + '/uploads/manga/{0}/chapters/{1}/{2}'
    cover_url = base_url + '{0}'

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

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            author=None,
            types=None,
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover_path='/uploads/manga/{0}/cover/cover_250x350.jpg'.format(data['slug']),
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
                data['genres'] = [t.strip() for t in value.split(',')]
            elif label.startswith('Estado'):
                # possible values: ongoing, complete, None
                data['status'] = value.lower()
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

        Currently, only pages (list of images filenames) are expected.
        """
        url = self.chapter_url.format(manga_slug, chapter_slug)
        r = session.get(url)

        soup = BeautifulSoup(r.text, 'html.parser')

        pages_imgs = soup.find('div', id='all').find_all('img')

        data = dict(
            pages=[],
        )
        for img in pages_imgs:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url directly
                image=img.get('data-src').strip().split('/')[-1],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        url = self.image_url.format(manga_slug, chapter_slug, page['image'])
        r = session.get(url)

        return (page['image'], r.content) if r.status_code == 200 else (None, None)

    def get_manga_cover_image(self, cover_path):
        """
        Returns manga cover (image) content
        """
        r = session.get(self.cover_url.format(cover_path))

        return r.content if r.status_code == 200 else None

    def search(self, term):
        r = session.get(self.search_url, params=dict(query=term))

        # Returned data for each manga:
        # value: name of the manga
        # data: slug of the manga
        results = r.json()['suggestions']

        for result in results:
            result['slug'] = result.pop('data')
            result['name'] = result.pop('value')

        return results
