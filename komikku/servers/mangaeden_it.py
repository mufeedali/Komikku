# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.mangaeden import Mangaeden

server_id = 'mangaeden_it'
server_name = 'Manga Eden'
server_lang = 'it'


class Mangaeden_it(Mangaeden):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'http://www.mangaeden.com'
    search_url = base_url + '/ajax/search-manga/'
    manga_url = base_url + '/it/it-manga/{0}/'
    chapter_url = base_url + '/it/it-manga/{0}/{1}/1/'
