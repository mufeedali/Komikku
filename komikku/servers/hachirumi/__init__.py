# -*- coding: utf-8 -*-

# Copyright (C) 2021 Mariusz Kurek
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Mariusz Kurek <mariuszkurek@pm.me>

from komikku.servers.multi.guya import Guya


class Hachirumi(Guya):
    id = 'hachirumi'
    name = 'Hachirumi'
    lang = 'en'
    is_nsfw = True
    base_url = 'https://hachirumi.com'
    manga_url = base_url + '/read/manga/{0}/'
    api_manga_url = base_url + '/api/series/{0}'
    api_page_url = base_url + '/media/manga/{0}/chapters/{1}/{2}'
