# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.genkan import Genkan


class Hunlightscans(Genkan):
    id = 'hunlightscans'
    name = 'Hunlight Scans'
    lang = 'en'

    base_url = 'https://hunlight-scans.info'
    search_url = base_url + '/comics?query={0}'
    most_populars_url = base_url + '/home'
    manga_url = base_url + '/comics/{0}'
    chapter_url = base_url + '/comics/{0}/{1}'
    image_url = base_url + '{0}'
