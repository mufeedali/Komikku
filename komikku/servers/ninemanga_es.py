from komikku.servers.ninemanga import Ninemanga

server_id = 'ninemanga_es'
server_name = 'Nine Manga'
server_lang = 'es'


class Ninemanga_es(Ninemanga):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'http://es.ninemanga.com'
    search_url = base_url + '/search/ajax/'
    manga_url = base_url + '/manga/{0}.html'
    chapter_url = base_url + '/chapter/{0}/{1}'
    page_url = chapter_url
    cover_url = 'http://a4.ninemanga.com{0}'
