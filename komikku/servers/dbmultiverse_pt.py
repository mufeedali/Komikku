# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.dbmultiverse import Dbmultiverse

server_id = 'dbmultiverse_pt'
server_name = 'Dragon Ball Multiverse'
server_lang = 'pt'


class Dbmultiverse_pt(Dbmultiverse):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.dragonball-multiverse.com'
    manga_url = base_url + '/pt/chapters.html'
    page_url = base_url + '/pt/page-{0}.html'

    synopsis = "Dragon Ball Multiverse (DBM) é uma BD online grátis, feita por dois fãs Gogeta Jr e Salagir. É a sequela do DBZ."
