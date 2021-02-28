from PIL import Image
from bs4 import BeautifulSoup
import re

from komikku.servers import convert_date_string
from komikku.servers import do_login
from komikku.servers import Server

# Improved from https://github.com/manga-py/manga-py


class Vizmanga(Server):
    id = 'vizmanga'
    name = 'VizManga'
    lang = 'en'
    locale = 'enUS'
    has_login = True

    base_url = 'https://www.viz.com'
    login_url = base_url + '/manga/try_manga_login'
    refresh_login_url = base_url + '/account/refresh_login_links'
    login_url = base_url + '/account/try_login'
    api_series_url = base_url + '/shonenjump'
    api_chapters_url = base_url + '/shonenjump/chapters/{}'
    api_chapter_data_url = base_url + '/manga/get_manga_url?device_id=3&manga_id={}&page={}'
    api_chapter_url = base_url + '/shonenjump/{}-chapter-{}/chapter/{}'

    chapter_regex = re.compile(r'/shonenjump/(.*)-chapter-([\d\-]*)/chapter/(\d*)')
    page_regex = re.compile(r'var pages\s*=\s*(\d*);')

    headers = {
        'Referer': 'https://www.viz.com',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=1.0,image/webp,image/apng,*/*;q=1.0',
    }

    def __init__(self, username=None, password=None):
        if username and password:
            self.do_login(username, password)

    @do_login
    def get_manga_data(self, initial_data):
        """
        Returns manga data from API

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        self.refresh_login()
        r = self.session_get(self.api_chapters_url.format(initial_data['slug']))
        soup = BeautifulSoup(r.content, 'lxml')

        authors = []
        synopsis = ''
        manga_info = soup.find('section', {'id': 'series-intro'})
        if manga_info:
            author_element = manga_info.find('span', {'class': 'disp-bl--bm mar-b-md'})
            authors = author_element.getText().split(',') if author_element else ''
            synposis_element = manga_info.find('h4')
            synopsis = synposis_element.getText().strip() if synposis_element else ''

        ongoing = soup.find('div', {'class': 'section_future_chapter'})
        status = 'ongoing' if ongoing else 'complete'

        data = initial_data.copy()
        data.update(dict(
            authors=authors,
            scanlators=[],
            genres=[],
            status=status,
            chapters=[],
            synopsis=synopsis,
            server_id=self.id,
            cover=initial_data['url'],
            url=initial_data['url'],
        ))

        # Chapters
        chapters = soup.findAll('a', {'class': 'o_chapter-container'})
        if ongoing:
            chapters.reverse()
        slugs = set()
        for chapter in chapters:
            raw_url_maybe = chapter['data-target-url']
            match = self.chapter_regex.search(raw_url_maybe)
            series_name = match.group(1)
            chapter_number = match.group(2)
            chapter_slug = match.group(3)
            chapter_date = None
            # There could be duplicate elements with the same chapter slug; they refer to the same chapter so skip them
            if chapter_slug in slugs:
                continue
            slugs.add(chapter_slug)
            try:
                chapter_date_str = chapter.find('td', {'class': 'pad-y-0 pad-r-0 pad-r-rg--sm'}).getText()
                chapter_date = convert_date_string(chapter_date_str, '%B %d, %Y')
            except AttributeError:
                pass
            # There seems to be a title field in the metadata... it doesn't seem useful nor unique
            # eg 'My Hero Academia: Vigilantes Chapter 1.0'
            # so we'll just use the chapter number as the title
            title = chapter_number

            data['chapters'].append(dict(
                slug=chapter_slug,
                title=title,
                url=self.api_chapter_url.format(series_name, chapter_number, chapter_slug),
                date=chapter_date,
            ))

        return data

    @do_login
    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data

        Currently, only pages are expected.
        """

        if not self.refresh_login():
            return None
        match = self.page_regex.search(self.session_get(chapter_url).text)
        num_pages = int(match.group(1)) + 1

        pages = []
        for i in range(num_pages):
            url = self.api_chapter_data_url.format(chapter_slug, i)
            pages.append({'slug': None, 'image': url})
        return {'pages': pages}

    def _get_chapter_url(self, chapter_slug, i):
        url = self.api_chapter_data_url.format(chapter_slug, i)

        r = self.session_get(url)
        return r.text.strip()

    @do_login
    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
        real_img_url = r.text.strip()

        r = self.session_get(real_img_url, stream=True)
        if r.status_code != 200:
            return None

        orig = Image.open(r.raw)  # type: Image.Image
        solution = Vizmanga.solve_image(orig)

        buffer = solution
        mime_type = None

        return dict(
            buffer=buffer,
            mime_type=mime_type,
            name=real_img_url.split('/')[-1].split('?')[0],
        )

    @staticmethod
    def get_manga_url(slug, url):
        """
        Returns manga absolute URL
        """
        return url

    @do_login
    def get_most_populars(self):
        """
        Returns full list of manga sorted by rank
        """
        r = self.session_get(self.api_series_url)

        soup = BeautifulSoup(r.content, 'lxml')
        divs = soup.findAll('a', {'class': 'disp-bl pad-b-rg pos-r bg-off-black color-white hover-bg-red'})
        result = []
        for div in divs:
            slug = div['href'].split('/')[-1]
            name = div.find('div', {'class', 'pad-x-rg pad-t-rg pad-b-sm type-sm type-rg--sm type-md--lg type-center line-solid'}).getText().strip()
            cover_url = div.find('img')['data-original']
            result.append({
                'slug': slug,
                'name': name,
                'url': cover_url,
            })

        return result

    def get_token(self):
        auth_token = self.session_get(self.refresh_login_url)
        token = re.search(r'AUTH_TOKEN\s*=\s*"(.+?)"', auth_token.text)
        return token.group(1)

    def refresh_login(self):
        r = self.session_get(self.refresh_login_url)
        soup = BeautifulSoup(r.content, 'lxml')
        return bool(soup.select('.o_profile-link'))

    def login(self, username, password):
        """
        Log in and initializes API
        """
        if not username or not password:
            return False
        token = self.get_token()

        r = self.session_post(
            self.login_url,
            data={
                'login': username,
                'pass': password,
                'rem_user': 1,
                'authenticity_token': token,
            })
        self.save_session()
        return r.status_code == 200

    def search(self, term):
        term_lower = term.lower()
        return filter(lambda x: term_lower in x['name'].lower(), self.get_most_populars())

    @staticmethod
    def solve_image(orig: Image) -> Image.Image:
        new_size = (orig.size[0] - 90, orig.size[1] - 140)
        ref = Image.new(orig.mode, new_size)  # type: Image.Image
        ref.paste(orig)

        _key = 42016
        exif = orig.getexif()
        key = [int(i, 16) for i in exif[_key].split(':')]
        width, height = exif[256], exif[257]

        small_width = int(width / 10)
        small_height = int(height / 15)

        Vizmanga.paste(ref, orig, (
            0, small_height + 10,
            small_width, height - 2 * small_height,
        ), (
            0, small_height,
            small_width, height - 2 * small_height,
        ))

        Vizmanga.paste(ref, orig, (
            0, 14 * (small_height + 10),
            width, orig.height - 14 * (small_height + 10),
        ), (
            0, 14 * small_height,
            width, orig.height - 14 * (small_height + 10),
        ))

        Vizmanga.paste(ref, orig, (
            9 * (small_width + 10), small_height + 10,
            small_width + (width - 10 * small_width), height - 2 * small_height,
        ), (
            9 * small_width, small_height,
            small_width + (width - 10 * small_width), height - 2 * small_height,
        ))

        for i, j in enumerate(key):
            Vizmanga.paste(ref, orig, (
                (i % 8 + 1) * (small_width + 10), (int(i / 8) + 1) * (small_height + 10),
                small_width, small_height,
            ), (
                (j % 8 + 1) * small_width, (int(j / 8) + 1) * small_height,
                small_width, small_height,
            ))

        return ref

    @staticmethod
    def paste(ref: Image.Image, orig: Image.Image, orig_box, ref_box):
        ref.paste(orig.crop((
            int(orig_box[0]), int(orig_box[1]),
            int(orig_box[0] + orig_box[2]), int(orig_box[1] + orig_box[3]),
        )), (
            int(ref_box[0]), int(ref_box[1]),
            int(ref_box[0] + ref_box[2]), int(ref_box[1] + ref_box[3]),
        ))
