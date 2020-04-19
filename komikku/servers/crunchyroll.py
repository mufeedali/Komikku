from bs4 import BeautifulSoup
from datetime import datetime
import re

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
        'Origin': 'https://www.crunchyroll.com/',
    }

    def __init__(self, login=None, password=None):
        self.init(login, password)
        if self.logged_in:
            self.init_session_token()

    def get_manga_data(self, initial_data):
        """
        Returns manga data
        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'
        r = self.session_get(self.api_chapters_url.format(initial_data['slug']))

        json_data = r.json()
        resp_data = json_data["series"]
        chapters = json_data["chapters"]

        data = initial_data.copy()
        data.update(dict(
            authors=[resp_data.get("authors", "")],
            scanlators=[resp_data.get("translator", "")],
            genres=resp_data.get("genres", ""),
            status=None,
            chapters=[],
            synopsis=resp_data["locale"][self.locale]["description"],
            server_id=self.id,
            cover=resp_data["locale"][self.locale]["thumb_url"],
        ))

        data['status'] = 'ongoing'

        # Chapters
        for chapter in chapters:
            data['chapters'].append(dict(
                slug=chapter['chapter_id'],
                title=chapter['number'],
            ))
            try:
                data['chapters'][-1]['date'] = datetime.strptime(chapter['availability_start'], '%Y-%m-%d %H:%M:%S').date()
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
        resp_data = r.json()
        if resp_data is None or resp_data.get('error', False):
            return None  # we aren't logged in
        pages = resp_data["pages"]
        pages.sort(key=lambda x: int(x["number"]))

        data = dict(
            pages=[],
            scrambled=0,
        )

        for page in pages:
            data['pages'].append(dict(
                slug=page['page_id'],  # not necessary, we know image URL already
                image=page['locale'][self.locale][self.page_url_key],
            ))

        return data

    @staticmethod
    def decode_image(buffer):
        # Don't know why 66 is special
        return bytes(b ^ 66 for b in buffer)

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(page['image'])

        return (page["slug"], self.decode_image(r.content))

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

        resp_data = r.json()
        result = []
        resp_data.sort(key=lambda x: not x['featured'])
        for item in resp_data:
            if 'locale' in item:
                result.append({
                    'slug': item['series_id'],
                    'name': item['locale'][self.locale]['name'],
                    'synopsis': item['locale'][self.locale]['description']
                })
        return result

    def search(self, term):
        term_lower = term.lower()
        return filter(lambda x: term_lower in x['name'].lower(), self.get_most_populars())

    def login(self, username, password):
        """
        Setup Crunchyroll session and get the auth token
        """
        if not username or not password:
            return False

        page = BeautifulSoup(self.session_get(self.login_url).text, 'lxml')
        hidden = page.findAll('input', {u'type': u'hidden'})[1].get('value')
        login_data = {
            'formname': 'login_form',
            'fail_url': self.login_url,
            'login_form[name]': username,
            'login_form[password]': password,
            'login_form[_token]': hidden,
            'login_form[redirect_url]': '/'
        }
        self.session_post(self.login_url, data=login_data)

        html = self.session_get(self.base_url).text
        if not re.search(username + '(?i)', html) or not self.init_session_token():
            return False

        self.save_session()
        return True

    def init_session_token(self):
        """
        Initialize session_id
        """
        match = re.search(r'sessionId: "(\w*)"', self.session_get('https://www.crunchyroll.com/manga/the-seven-deadly-sins/read/1').text)
        if match:
            self.session_id = match.group(1)
            if not self.cr_auth:
                data = self.session_get(self.cr_auth_url.format(self.session_id)).json()
                self.cr_auth = ''.join(data['data']['auth'])
            return True
        return False
