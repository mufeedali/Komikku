# -*- coding: utf-8 -*-

# Copyright (C) 2021 Mariusz Kurek
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Mariusz Kurek <mariuszkurek@pm.me>

from komikku.servers.multi.guya import Guya


class Dankefurslesen(Guya):
    id = 'dankefurslesen'
    name = 'Danke fürs Lesen'
    lang = 'en'
    base_url = 'https://danke.moe'
    manga_url = base_url + '/read/manga/{0}/'
    api_manga_url = base_url + '/api/series/{0}'
    api_page_url = base_url + '/media/manga/{0}/chapters/{1}/{2}'
