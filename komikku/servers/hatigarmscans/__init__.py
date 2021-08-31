# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

# BEWARE: Old Hatigarmscans is disabled
# Dead since 02/2020
# The site has changed its address and is now available in the genkan server

from komikku.servers.multi.genkan import GenkanInitial
from komikku.servers.multi.my_manga_reader_cms import MyMangaReaderCMS


class Hatigarmscans(GenkanInitial):
    id = 'hatigarmscans'
    name = 'Hatigarm Scans'
    lang = 'en'

    base_url = 'https://hatigarmscanz.net'
    search_url = base_url + '/comics'
    most_populars_url = base_url + '/home'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'


class Hatigarmscans__old(MyMangaReaderCMS):
    id = 'hatigarmscans__old'
    name = 'Hatigarm Scans'
    lang = 'en'
    status = 'disabled'

    base_url = 'https://www.hatigarmscans.net'
    search_url = base_url + '/search'
    most_populars_url = base_url + '/filterList?page=1&sortBy=views&asc=false'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'
    image_url = base_url + '/uploads/manga/{0}/chapters/{1}/{2}'
    cover_url = base_url + '/uploads/manga/{0}/cover/cover_250x350.jpg'
