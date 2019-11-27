# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.dbmultiverse import Dbmultiverse

server_id = 'dbmultiverse_ru'
server_name = 'Dragon Ball Multiverse'
server_lang = 'ru'


class Dbmultiverse_ru(Dbmultiverse):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.dragonball-multiverse.com'
    manga_url = base_url + '/ru_RU/chapters.html'
    page_url = base_url + '/ru_RU/page-{0}.html'

    synopsis = "Dragon Ball Multiverse (DBM) это бесплатный онлайн комикс (манга), сделана двумя фанатами, Gogeta Jr и Salagir. Это продолжение DBZ."
