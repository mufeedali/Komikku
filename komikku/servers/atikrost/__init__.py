# -*- coding: utf-8 -*-

# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.multi.madara import Madara


class Atikrost(Madara):
    id = 'atikrost'
    name = 'Atikrost'
    lang = 'tr'

    base_url = 'https://atikrost.com/'
