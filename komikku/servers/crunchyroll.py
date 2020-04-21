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
    manga_url = base_url + '/comics/manga/{0}/volumes'

    api_base_url = 'http://api-manga.crunchyroll.com'
    api_auth_url = api_base_url + '/cr_authenticate?auth=&session_id={}&version=0&format=json'
    api_chapter_list = api_base_url + '/list_chapter?session_id={}&chapter_id={}&auth={}'
    api_series_url = api_base_url + '/series?sort=popular'
    api_chapters_url = api_base_url + '/chapters?series_id={}'

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

    @property
    def api_auth_token(self):
        extras = getattr(self.session, '_extras', {})
        return extras.get('api_auth_token', '')

    @property
    def api_session_id(self):
        extras = getattr(self.session, '_extras', {})
        return extras.get('api_session_id', '')

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
            authors=[],
            scanlators=[],
            genres=[],
            status='ongoing',
            chapters=[],
            synopsis=resp_data['locale'][self.locale]['description'],
            server_id=self.id,
            cover=resp_data['locale'][self.locale]['thumb_url'],
            url=self.manga_url.format(resp_data['url'][1:]),
        ))

        if resp_data.get('authors'):
            data['authors'] += [t.strip() for t in resp_data['authors'].split(',')]
        if resp_data.get('artist'):
            data['authors'] += [t.strip() for t in resp_data['artist'].split(',') if t.strip() not in data['authors']]

        if resp_data.get('translator'):
            data['scanlators'] += [t.strip() for t in resp_data['translator'].split('|')]

        if resp_data.get('genres'):
            data['genres'] = resp_data['genres']

        if resp_data['locale'][self.locale].get('copyright'):
            data['synopsis'] += '\n\n' + resp_data['locale'][self.locale]['copyright']

        # Chapters
        for chapter in chapters:
            date = None
            if chapter.get('availability_start'):
                date_string = chapter['availability_start'].split(' ')[0]
                if len(date_string) == 10 and '-00' not in date_string:
                    date = convert_date_string(date_string, '%Y-%m-%d')
            if date is None and chapter.get('updated'):
                date_string = chapter['updated'].split(' ')[0]
                if len(date_string) == 10 and '-00' not in date_string:
                    date = convert_date_string(date_string, '%Y-%m-%d')

            data['chapters'].append(dict(
                slug=chapter['chapter_id'],
                title=chapter['locale'][self.locale]['name'],
                date=date,
            ))

        return data

    def get_manga_chapter_url(self, chapter_id):
        return self.api_chapter_list.format(self.api_session_id, chapter_id, self.api_auth_token)

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
        return url

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

    def init_api(self):
        """
        Retrieves API session ID and authentication token

        Both are stored in '_extras' session attribute (internal attribute not part of Requests)
        """
        r = self.session_get('https://www.crunchyroll.com/comics_read/manga?volume_id=273&chapter_num=1')
        match = re.search(r'session_id=(\w*)&amp;', r.text)
        if not match:
            return False

        self.session._extras = dict()
        self.session._extras['api_session_id'] = match.group(1)
        r = self.session_get(self.api_auth_url.format(self.session._extras['api_session_id']))
        try:
            data = r.json()

            self.session._extras['api_auth_token'] = ''.join(data['data']['auth'])
            self.session._extras['api_expires'] = data['data']['expires']
        except Exception:
            return False

        return True

    def login(self, username, password):
        """
        Log in and initializes API
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
        if not re.search(username + '(?i)', r.text) or not self.init_api():
            return False

        self.save_session()

        return True

    def search(self, term):
        term_lower = term.lower()
        return filter(lambda x: term_lower in x['name'].lower(), self.get_most_populars())
