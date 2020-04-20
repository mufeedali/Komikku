from bs4 import BeautifulSoup
import re

from komikku.servers import convert_date_string
from komikku.servers import get_buffer_mime_type
from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = 'Crunchyroll'


class Crunchyroll(Server):
    id = 'crunchyroll'
    name = SERVER_NAME
    lang = 'en'
    locale = 'enUS'
    has_login = True

    base_url = 'https://www.crunchyroll.com'
    login_url = base_url + '/login'
    manga_url = base_url + '/comics/manga/{0}'

    api_base_url = 'http://api-manga.crunchyroll.com'
    api_chapter_list = api_base_url + '/list_chapter?session_id={}&chapter_id={}&auth={}'
    api_series_url = api_base_url + '/series?sort=popular'
    api_chapters_url = api_base_url + '/chapters?series_id={}'
    cr_auth_url = api_base_url + '/cr_authenticate?auth=&session_id={}&version=0&format=json'

    session_id = None
    cr_auth = None
    possible_page_url_keys = ['encrypted_mobile_image_url', 'encrypted_composed_image_url']
    page_url_key = possible_page_url_keys[0]

    headers = {
        'User-Agent': USER_AGENT,
        'Origin': 'https://www.crunchyroll.com',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en,en-US;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
    }

    def __init__(self, login=None, password=None):
        self.init(login, password)

        if self.logged_in:
            self.init_session_token()

    @staticmethod
    def decode_image(buffer):
        # Don't know why 66 is special
        return bytes(b ^ 66 for b in buffer)

    def get_manga_data(self, initial_data):
        """
        Returns manga data
        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'
        r = self.session_get(self.api_chapters_url.format(initial_data['slug']))

        json_data = r.json()
        resp_data = json_data['series']
        chapters = json_data['chapters']

        data = initial_data.copy()
        data.update(dict(
            authors=[resp_data.get('authors', '')],
            scanlators=[resp_data.get('translator', '')],
            genres=resp_data.get('genres', []),
            status=None,
            chapters=[],
            synopsis=resp_data['locale'][self.locale]['description'],
            server_id=self.id,
            cover=resp_data['locale'][self.locale]['thumb_url'],
        ))

        data['status'] = 'ongoing'

        # Chapters
        for chapter in chapters:
            data['chapters'].append(dict(
                slug=chapter['chapter_id'],
                title=chapter['number'],
            ))
            try:
                data['chapters'][-1]['date'] = convert_date_string(chapter['availability_start'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass

        return data

    def get_manga_chapter_url(self, chapter_id):
        return self.api_chapter_list.format(self.session_id, chapter_id, self.cr_auth)

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga chapter data

        Currently, only pages are expected.
        """
        r = self.session_get(self.get_manga_chapter_url(chapter_slug))

        try:
            resp_data = r.json()
            if resp_data is None or resp_data.get('error', False):
                # We aren't logged in
                return None

            pages = resp_data['pages']
            pages.sort(key=lambda x: int(x['number']))
        except Exception:
            return None

        data = dict(
            pages=[],
        )

        for page in pages:
            data['pages'].append(dict(
                slug=page['page_id'],  # used later to forge image name
                image=page['locale'][self.locale][self.page_url_key],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])
        if r.status_code != 200:
            return None

        buffer = self.decode_image(r.content)

        mime_type = get_buffer_mime_type(buffer)
        if not mime_type.startswith('image'):
            return None

        return dict(
            buffer=buffer,
            mime_type=mime_type,
            name='{0}.{1}'.format(page['slug'], mime_type.split('/')[1]),
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns full list of manga sorted by rank
        """
        r = self.session_get(self.api_series_url)

        try:
            result = []

            resp_data = r.json()
            resp_data.sort(key=lambda x: not x['featured'])

            for item in resp_data:
                if 'locale' not in item:
                    continue

                result.append({
                    'slug': item['series_id'],
                    'name': item['locale'][self.locale]['name'],
                })
        except Exception:
            return None

        return result

    def init_session_token(self):
        """
        Initialize session ID and get auth token
        """
        r = self.session_get('https://www.crunchyroll.com/comics_read/manga?volume_id=273&chapter_num=1')
        match = re.search(r'session_id=(\w*)&amp;', r.text)
        if not match:
            return False

        self.session_id = match.group(1)
        if not self.cr_auth:
            r = self.session_get(self.cr_auth_url.format(self.session_id))
            try:
                data = r.json()
                self.cr_auth = ''.join(data['data']['auth'])
            except Exception:
                return False

        return True

    def login(self, username, password):
        """
        Log in, setup session and get auth token
        """
        if not username or not password:
            return False

        r = self.session_get(self.login_url, headers={'referer': self.login_url})

        soup = BeautifulSoup(r.content, 'lxml')

        self.session_post(
            self.login_url,
            data={
                'login_form[name]': username,
                'login_form[password]': password,
                'login_form[_token]': soup.findAll('input', {u'type': u'hidden'})[1].get('value'),
                'login_form[redirect_url]': '/',
            }
        )

        r = self.session_get(self.base_url)
        if not re.search(username + '(?i)', r.text) or not self.init_session_token():
            return False

        self.save_session()

        return True

    def search(self, term):
        term_lower = term.lower()
        return filter(lambda x: term_lower in x['name'].lower(), self.get_most_populars())
