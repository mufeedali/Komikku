# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from komikku.servers.peppercarrot import Peppercarrot

server_id = 'peppercarrot_fr'
server_name = 'Pepper&Carrot'
server_lang = 'fr'


class Peppercarrot_fr(Peppercarrot):
    id = server_id
    name = server_name
    lang = server_lang

    synopsis = "C'est l'histoire de la jeune sorcière Pepper et de son chat Carrot dans le monde magique d'Hereva. Pepper apprend la magie de Chaosah, la magie du chaos, avec ses marraines Cayenne, Thym et Cumin. D'autres sorcières comme Saffran, Coriander, Camomile et Schichimi apprennent des magies qui ont chacune leurs spécificités."
