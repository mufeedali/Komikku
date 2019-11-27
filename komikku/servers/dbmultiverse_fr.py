# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.dbmultiverse import Dbmultiverse

server_id = 'dbmultiverse_fr'
server_name = 'Dragon Ball Multiverse'
server_lang = 'fr'


class Dbmultiverse_fr(Dbmultiverse):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.dragonball-multiverse.com'
    manga_url = base_url + '/fr/chapters.html'
    page_url = base_url + '/fr/page-{0}.html'

    synopsis = "Dragon Ball Multiverse (DBM) est une BD en ligne gratuite, faite par toute une équipe de fans. C'est notre suite personnelle à DBZ."
