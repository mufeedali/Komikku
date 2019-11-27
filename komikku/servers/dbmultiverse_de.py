# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.dbmultiverse import Dbmultiverse

server_id = 'dbmultiverse_de'
server_name = 'Dragon Ball Multiverse'
server_lang = 'de'


class Dbmultiverse_de(Dbmultiverse):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://www.dragonball-multiverse.com'
    manga_url = base_url + '/de/chapters.html'
    page_url = base_url + '/de/page-{0}.html'

    synopsis = "Dragon Ball Multiverse ist ein kostenloser Online-Comic, gezeichnet von Fans, u. a. Gogeta Jr, Asura und Salagir. Es knüpft direkt an DBZ an als eine Art Fortsetzung. Veröffentlichung dreimal pro Woche: Mittwoch, Freitag und Sonntag um 20.00 MEZ."
