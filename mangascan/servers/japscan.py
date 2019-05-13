from bs4 import BeautifulSoup
import magic
import cloudscraper

server_id = 'japscan'
server_name = 'JapScan'
server_lang = 'fr'

scraper = None


class Japscan():
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.japscan.to'
    search_url = base_url + '/search/'
    manga_url = base_url + '/manga/{0}/'
    chapter_url = base_url + '/lecture-en-ligne/{0}/{1}/'
    image_url = 'https://c.japscan.to/lel/{0}/{1}/{2}'
    cover_url = base_url + '{0}'

    def __init__(self):
        global scraper

        if scraper is None:
            scraper = cloudscraper.create_scraper()

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Inital data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        r = scraper.get(self.manga_url.format(initial_data['slug']))
        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            author=None,
            genres=[],
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
            elif label.startswith('Genre'):
                data['genres'] = [genre.strip() for genre in value.split(',')]
            elif label.startswith('Statut'):
                # Possible values: ongoing, complete
                data['status'] = 'ongoing' if value == 'En Cours' else 'complete'

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

        Currently, only pages are expected.
        """
        url = self.chapter_url.format(manga_slug, chapter_slug)
        r = scraper.get(url)
        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        pages_options = soup.find('select', id='pages').find_all('option')

        data = dict(
            pages=[],
        )
        for option in pages_options:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url directly
                image=option.get('data-img').split('/')[-1],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        # This server use a specific manga slug for url images (capitalized kebab-case)
        manga_slug = '-'.join(w.capitalize() if w not in ('s',) else w for w in manga_slug.split('-'))
        chapter_slug = chapter_slug.capitalize()

        url = self.image_url.format(manga_slug, chapter_slug, page['image'])
        imagename = url.split('/')[-1]
        r = scraper.get(url)
        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (imagename, r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_cover_image(self, cover_path):
        """
        Returns manga cover (image) content
        """
        r = scraper.get(self.cover_url.format(cover_path))
        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return r.content if r.status_code == 200 and mime_type.startswith('image') else None

    def search(self, term):
        scraper.get(self.base_url)

        r = scraper.post(self.search_url, data=dict(search=term))

        if r.status_code == 200:
            if r.content == b'':
                # No results
                return []

            try:
                results = r.json(strict=False)

                # Returned data for each manga:
                # name:  name of the manga
                # image: path of cover image
                # url:   path of manga page
                for result in results:
                    # Extract slug from url
                    result['slug'] = result.pop('url').split('/')[2]
                    result['cover_path'] = result.pop('image')

                return results
            except Exception:
                return None
        else:
            return None
