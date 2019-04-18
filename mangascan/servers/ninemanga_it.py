# -*- coding: utf-8 -*-

from collections import OrderedDict

from mangascan.servers.ninemanga import Ninemanga

server_id = 'ninemanga_it'
server_name = 'Nine Manga'
server_lang = 'it'

session = None
headers = OrderedDict(
    [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0'),
        ('Accept-Language', 'en-US,en;q=0.5'),
    ]
)


class Ninemanga_it(Ninemanga):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'http://it.ninemanga.com'
    search_url = base_url + '/search/ajax/'
    manga_url = base_url + '/manga/{0}.html'
    chapter_url = base_url + '/chapter/{0}/{1}'
    page_url = chapter_url
    cover_url = 'https://na3.taadd.com{0}'

    def __init__(self):
        Ninemanga.__init__(self)
