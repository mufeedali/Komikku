# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.foolslide import FoOlSlide


class Lupiteam(FoOlSlide):
    id = 'lupiteam'
    name = 'Lupi Team'
    lang = 'it'

    base_url = 'https://lupiteam.net/reader'
    search_url = base_url + '/search'
    mangas_url = base_url + '/directory'
    manga_url = base_url + '/series/{0}'
    chapter_url = base_url + '/read/{0}/it/{1}/page/1'
