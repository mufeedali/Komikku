from bs4 import BeautifulSoup
import cfscrape

server_id = 'japscan'
server_name = 'JapScan'
server_country = 'fr'

base_url = 'https://www.japscan.to'
search_url = base_url + '/search/'
manga_url = base_url + '/manga/{0}/'
cover_url = base_url + '/imgs/mangas/{0}.jpg'
chapter_url = base_url + '/lecture-en-ligne/{0}/{1}/'
scan_url = 'https://c.japscan.to/lel/{0}/{1}/{2}'

session = None


class Japscan():
    __server_name__ = server_name

    def __init__(self):
        global session
        session = cfscrape.create_scraper()

    @property
    def id(self):
        return server_id

    @property
    def name(self):
        return self.__server_name__

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Inital data should contain manga's slug and name (provided by search)
        """
        assert 'slug' in initial_data and 'name' in initial_data, 'Missing slug and/or name in initial data'

        r = session.get(manga_url.format(initial_data['slug']))
        # print(r.text)

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            author=None,
            types=None,
            status=None,
            chapters=[],
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
                data['types'] = value
            elif label.startswith('Statut'):
                data['status'] = value

        # Synopsis
        data['synopsis'] = card_element.find('p', class_='list-group-item-primary').text.strip()

        # Chapters
        elements = soup.find('div', id='chapters_list').find_all('div', class_='chapters_list')
        for element in reversed(elements):
            slug = element.a.get('href').split('/')[3]
            if element.a.span:
                element.a.span.extract()

            data['chapters'].append(dict(
                slug=slug,
                date=element.span.text.strip(),
                title=element.a.text.strip(),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages (list of images filenames) are expected.
        """
        url = chapter_url.format(manga_slug, chapter_slug)
        r = session.get(url)

        soup = BeautifulSoup(r.text, 'html.parser')
        # print(r.text)

        pages_options = soup.find('select', id='pages').find_all('option')

        data = dict(
            pages=[],
        )
        for option in pages_options:
            data['pages'].append(option.get('data-img'))

        return data

    def get_manga_chapter_page_image(self, manga_slug, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        manga_slug = '-'.join(w.capitalize() for w in manga_slug.split('-'))
        chapter_slug = chapter_slug.capitalize()

        url = scan_url.format(manga_slug, chapter_slug, page)
        r = session.get(url)

        return r.content if r.status_code == 200 else None

    def get_manga_cover_image(self, manga_slug):
        """
        Returns manga cover (image) content
        """
        manga_slug = '-'.join(w.capitalize() for w in manga_slug.split('-'))
        r = session.get(cover_url.format(manga_slug))

        return r.content

    def search(self, term):
        r = session.post(search_url, data=dict(search=term))

        # Returned data for each manga:
        # name:  name of the manga
        # image: relative path of cover image
        # url:   relative path of manga page
        results = r.json()

        for result in results:
            # Extract slug from url
            result['slug'] = result.pop('url').split('/')[2]
            result.pop('image')

        return results
