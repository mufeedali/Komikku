# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.dbmultiverse import Dbmultiverse

server_id = 'dbmultiverse_es'
server_name = 'Dragon Ball Multiverse'
server_lang = 'es'


class Dbmultiverse_es(Dbmultiverse):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.dragonball-multiverse.com'
    manga_url = base_url + '/es/chapters.html'
    page_url = base_url + '/es/page-{0}.html'

    synopsis = "Dragon Ball Multiverse (DBM) es un cómic online gratuito, realizado por un gran equipo de fans. Es nuestra propia continuación de DBZ."
