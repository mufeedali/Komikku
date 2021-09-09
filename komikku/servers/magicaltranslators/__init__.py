# -*- coding: utf-8 -*-

# Copyright (C) 2021 Mariusz Kurek
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Mariusz Kurek <mariuszkurek@pm.me>

from komikku.servers.multi.guya import Guya


class Magicaltranslators(Guya):
    id = 'magicaltranslators'
    name = 'Magical Translators'
    lang = 'en'
    base_url = 'https://mahoushoujobu.com'
    manga_url = base_url + '/read/manga/{0}/'
    api_manga_url = base_url + '/api/series/{0}'
    api_page_url = base_url + '/media/manga/{0}/chapters/{1}/{2}'


class Magicaltranslators_pl(Magicaltranslators):
    id = 'magicaltranslators_pl'
    lang = 'pl'
