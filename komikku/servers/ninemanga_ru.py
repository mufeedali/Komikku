from komikku.servers.ninemanga import Ninemanga

server_id = 'ninemanga_ru'
server_name = 'Nine Manga'
server_lang = 'ru'


class Ninemanga_ru(Ninemanga):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'http://ru.ninemanga.com'
    search_url = base_url + '/search/ajax/'
    popular_url = base_url + '/list/Hot-Book/'
    manga_url = base_url + '/manga/{0}.html?waring=1'
    chapter_url = base_url + '/chapter/{0}/{1}'
    page_url = chapter_url
    cover_url = 'https://na3.taadd.com{0}'
