from bs4 import BeautifulSoup
import requests

server_id = 'hatigarmscans'
server_name = 'Hatigarm Scans'
server_lang = 'en'

session = None


class Hatigarmscans():
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.hatigarmscans.net'
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
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover_path='/uploads/manga/{0}/cover/cover_250x350.jpg'.format(data['slug']),
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
                data['genres'] = ', '.join([t.strip() for t in value.split(',')])
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

        Currently, only pages are expected.
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
