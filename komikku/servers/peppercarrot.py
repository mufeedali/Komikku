# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from bs4 import BeautifulSoup
import magic
import requests
import textwrap

from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = 'Pepper&Carrot'


class Peppercarrot(Server):
    id = 'peppercarrot'
    name = SERVER_NAME
    lang = 'en'

    base_url = 'https://www.peppercarrot.com'
    manga_url = base_url + '/{0}/'
    chapter_url = base_url + '/0_sources/episodes-v1.json'
    image_url = base_url + '/0_sources/{0}/low-res/{1}_{2}'
    cover_url = base_url + '/0_sources/0ther/artworks/low-res/2016-02-24_vertical-cover_remake_by-David-Revoy.jpg'

    synopsis = 'This is the story of the young witch Pepper and her cat Carrot in the magical world of Hereva. Pepper learns the magic of Chaosah, the magic of chaos, with his godmothers Cayenne, Thyme and Cumin. Other witches like Saffran, Coriander, Camomile and Schichimi learn magics that each have their specificities.'

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({'user-agent': USER_AGENT})

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content
        """
        r = self.session_get(self.manga_url.format(self.lang))
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        data = initial_data.copy()
        data.update(dict(
            authors=['David Revoy', ],
            scanlators=[],
            genres=[],
            status='ongoing',
            synopsis=self.synopsis,
            chapters=[],
            server_id=self.id,
            cover=self.cover_url,
        ))

        # Chapters
        for index, element in enumerate(reversed(soup.find('div', class_='homecontent').find_all('figure'))):
            if 'notranslation' in element.get('class'):
                # Skipped not translated episodes
                continue

            data['chapters'].append(dict(
                slug=index,  # Fake slug, needed to find chapters info in episodes API service
                date=None,
                title=element.a.get('title'),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data using episodes API service

        Chapter slug is updated
        """
        r = self.session_get(self.chapter_url)
        if r is None:
            return None

        chapters_data = r.json()
        try:
            chapter_data = chapters_data[int(chapter_slug)]
        except Exception:
            for chapter_data in chapters_data:
                if chapter_data['name'] == chapter_slug:
                    break

        data = dict(
            slug=chapter_data['name'],  # real slug
            pages=[],
        )

        # Title page is first page
        data['pages'].append(dict(
            slug=chapter_data['pages']['title'],
            image=None,
        ))

        for key, page_name in chapter_data['pages'].items():
            if key == 'title':
                # Skipped title, cover and credits pages
                break

            data['pages'].append(dict(
                slug=page_name,
                image=None,
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(self.image_url.format(chapter_slug, self.lang, page['slug']))
        if r is None:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (page['slug'], r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(self.lang)

    def get_most_populars(self):
        return self.search()

    def search(self, term=None):
        return [dict(
            slug='',
            name='Pepper&Carrot',
        )]


class Peppercarrot_de(Peppercarrot):
    id = 'peppercarrot_de'
    name = SERVER_NAME
    lang = 'de'

    synopsis = 'Dies ist die Geschichte der jungen Hexe Pepper und ihrer Katze Carrot in der magischen Welt von Hereva. Pepper lernt mit seinen Patinnen Cayenne, Thymian und Kreuzkümmel die Magie von Chaosah, die Magie des Chaos. Andere Hexen wie Saffran, Koriander, Kamille und Schichimi lernen Magie, die jeweils ihre Besonderheiten haben.'


class Peppercarrot_es(Peppercarrot):
    id = 'peppercarrot_es'
    name = SERVER_NAME
    lang = 'es'

    synopsis = 'Esta es la historia de la joven bruja Pepper y su gato Zanahoria en el mundo mágico de Hereva. Pepper aprende la magia de Chaosah, la magia del caos, con sus madrinas Cayenne, Thyme y Cumin. Otras brujas como Saffran, Cilantro, Manzanilla y Schichimi aprenden magias que tienen sus especificidades.'


class Peppercarrot_fr(Peppercarrot):
    id = 'peppercarrot_fr'
    name = SERVER_NAME
    lang = 'fr'

    synopsis = "C'est l'histoire de la jeune sorcière Pepper et de son chat Carrot dans le monde magique d'Hereva. Pepper apprend la magie de Chaosah, la magie du chaos, avec ses marraines Cayenne, Thym et Cumin. D'autres sorcières comme Saffran, Coriander, Camomile et Schichimi apprennent des magies qui ont chacune leurs spécificités."


class Peppercarrot_id(Peppercarrot):
    id = 'peppercarrot_id'
    name = SERVER_NAME
    lang = 'id'

    synopsis = 'Ini adalah kisah penyihir muda Pepper dan kucingnya Wortel di dunia magis Hereva. Pepper mempelajari keajaiban Chaosah, keajaiban kekacauan, dengan ibu baptisnya Cayenne, Thyme dan Cumin. Penyihir lain seperti Saffran, Ketumbar, Camomile, dan Schichimi mempelajari sihir yang masing-masing memiliki kekhasan masing-masing.'


class Peppercarrot_it(Peppercarrot):
    id = 'peppercarrot_it'
    name = SERVER_NAME
    lang = 'it'

    synopsis = 'Questa è la storia della giovane strega Pepper e del suo gatto Carota nel magico mondo di Hereva. Pepper impara la magia di Chaosah, la magia del caos, con le sue madrine Cayenne, Timo e Cumino. Altre streghe come Saffran, Coriandolo, Camomilla e Schichimi imparano magie che hanno ciascuna le loro specificità.'


class Peppercarrot_pt(Peppercarrot):
    id = 'peppercarrot_pt'
    name = SERVER_NAME
    lang = 'pt'

    synopsis = 'Esta é a história da jovem bruxa Pepper e seu gato Cenoura no mundo mágico de Hereva. Pepper aprende a magia de Chaosah, a magia do caos, com suas madrinhas Cayenne, Tomilho e Cominho. Outras bruxas como Saffran, Coentro, Camomila e Schichimi aprendem magias que cada uma tem suas especificidades.'


class Peppercarrot_ru(Peppercarrot):
    id = 'peppercarrot_ru'
    name = SERVER_NAME
    lang = 'ru'

    synopsis = 'Это история молодой ведьмы Пеппер и ее кота Морковки в волшебном мире Херева. Пеппер изучает магию Хаоса, магию хаоса вместе со своими крестными матерями Кайеной, Тимьяном и Кумином. Другие ведьмы, такие как Саффран, Кориандр, Ромашка и Счими, изучают магию, каждая из которых имеет свои особенности.'
