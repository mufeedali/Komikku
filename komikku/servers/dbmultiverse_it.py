# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.dbmultiverse import Dbmultiverse

server_id = 'dbmultiverse_it'
server_name = 'Dragon Ball Multiverse'
server_lang = 'it'


class Dbmultiverse_it(Dbmultiverse):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.dragonball-multiverse.com'
    manga_url = base_url + '/it/chapters.html'
    page_url = base_url + '/it/page-{0}.html'

    synopsis = "Dragon Ball Multiverse (abbreviato in DBM) è un Fumetto gratuito pubblicato online e rappresenta un possibile seguito di DBZ. I creatori sono due fan: Gogeta Jr e Salagir."
