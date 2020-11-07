# -*- coding: utf-8 -*-

# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: ISO-morphism <me@iso-morphism.name>

import json
from collections import OrderedDict
from gettext import gettext as _
import requests

from komikku.servers import get_buffer_mime_type
from komikku.servers import convert_date_string
from komikku.servers import Server
from komikku.servers import USER_AGENT

SERVER_NAME = "Manga Hub"

headers = OrderedDict(
    [
        ("User-Agent", USER_AGENT),
        ("Accept-Language", "en-US,en;q=0.5"),
    ]
)


class Mangahub(Server):
    id = "mangahub"
    name = SERVER_NAME
    lang = "en"
    base_url = "https://mangahub.io"
    manga_url = base_url + "/manga/{0}"
    chapter_url = base_url + "/chapter/{0}/{1}"
    api_url = "https://api.mghubcdn.com/graphql"
    img_url = "https://img.mghubcdn.com/file/imghub/{0}"
    thumb_url = "https://thumb.mghubcdn.com/{0}"

    def __init__(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers = headers

    def get_manga_data(self, initial_data):
        """
        Returns manga data by hitting Mangahub's GraphQL API.

        Initial data should contain at least manga's slug (provided by search)
        """
        assert "slug" in initial_data, "Slug is missing in initial data"

        query = {
            "query": '{manga(x:m01,slug:"%s"){id,title,slug,status,image,author,artist,genres,description,updatedDate,chapters{slug,title,number,date}}}'
            % initial_data["slug"]
        }
        resp = self.session.post(self.api_url, json=query)
        if not resp.ok:
            return None
        data = initial_data.copy()
        data.update(
            dict(
                authors=[],
                scanlators=[],
                genres=[],
                status=None,
                synopsis=None,
                chapters=[],
                server_id=self.id,
                cover=None,
            )
        )
        try:
            manga = resp.json()["data"]["manga"]
            data["authors"].extend(a.strip() for a in manga["author"].split(","))
            data["authors"].extend(a.strip() for a in manga["artist"].split(","))
            data["genres"].extend(g.strip() for g in manga["genres"].split(","))
            if manga["status"] == "ongoing":
                data["status"] = "ongoing"
            elif manga["status"] == "completed":
                data["status"] = "complete"
            data["synopsis"] = manga["description"]
            data["cover"] = self.thumb_url.format(manga["image"])
            raw_chapters = sorted(manga["chapters"], key=lambda c: c["number"])
            def conv_chap(c):
                title = c["title"]
                if not title:
                    title = f"{_('Chapter')} {c['number']}"
                return {
                    "slug": _mh_chap_num_to_komikku_slug(c["number"]),
                    "title": title,
                    "date": convert_date_string(c["date"]),
                }

            data["chapters"] = [conv_chap(c) for c in raw_chapters]
            return data
        except Exception as e:
            print(f"Mangahub: Failed to get manga data: {e}")
            return None

    def get_manga_chapter_data(self, manga_slug, manga_name, chapter_slug, chapter_url):
        """
        Returns manga data by hitting Mangahub's GraphQL API.

        Currently, only pages are expected.
        """
        query = {
            "query": '{chapter(x:m01,slug:"%s",number:%s){pages}}'
            % (manga_slug, _komikku_slug_to_mh_chap_num(chapter_slug))
        }
        resp = self.session.post(self.api_url, json=query)
        if not resp.ok:
            return None
        try:
            pages = json.loads(resp.json()["data"]["chapter"]["pages"])
            # pages is {"1": ".../1.jpg", "2": ".../2.jpg"} etc.
            # Python doesn't guarantee that dictionaries iterate in insertion order
            # until 3.7. Be a little paranoid and sort.
            ps = list(pages.items())
            ps = sorted(ps, key=lambda pair: pair[0])
            return {
                "pages": [
                    {"slug": None, "image": self.img_url.format(slug)} for _, slug in ps
                ]
            }
        except Exception as e:
            print(f"Mangahub: Failed to get chapter data: {e}")
            return None

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        r = self.session_get(
            page["image"],
            headers={
                "Accept": "image/webp,image/*;q=0.8,*/*;q=0.5",
                "Referer": self.chapter_url.format(manga_slug, chapter_slug),
            },
        )
        if r is None or r.status_code != 200:
            return None

        mime_type = get_buffer_mime_type(r.content)
        if not mime_type.startswith("image"):
            return None

        return dict(
            buffer=r.content,
            mime_type=mime_type,
            name=page["image"].split("/")[-1],
        )

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def get_most_populars(self):
        """
        Returns most viewed manga list
        """
        query = {"query": "{latestPopular(x: m01){slug, title}}"}
        resp = self.session.post(self.api_url, json=query)
        if not resp.ok:
            return None
        try:
            items = resp.json()["data"]["latestPopular"]
            return [{"slug": m["slug"], "name": m["title"]} for m in items]
        except Exception as e:
            print(f"Mangahub: Failed to get chapter data: {e}")
            return None

    def search(self, term):
        query = {"query": '{search(x:m01,q:"%s",limit:10){rows{title,slug}}}' % term}
        resp = self.session.post(self.api_url, json=query)
        if not resp.ok:
            return None
        try:
            rows = resp.json()["data"]["search"]["rows"]
            return [{"name": r["title"], "slug": r["slug"]} for r in rows]
        except Exception as e:
            print(f"Mangahub: Failed to get search results: {e}")
            return None


# Mangahub's GraphQL API has a `slug` field for chapters but that is often null.
# Chapter number (a float in the api but we treat/present as string just fine)
# is required, and it seems pretty consistent that when viewing the website the actual
# url slug is `chapter-{number}`. Komikku considers chapter slug to be the key, so we store
# `chapter-{number}` as the slug, as that's likely the URL slug for the website, and remember
# to deal with `chapter-`. An alternative approach could be to stuff the number in the `url`, but
# that also feels even more dishonest. For the most part, we're just ignoring the `slug` parameter
# returned by the Mangahub API.
def _mh_chap_num_to_komikku_slug(chapter_num):
    return f"chapter-{chapter_num}"


def _komikku_slug_to_mh_chap_num(chapter_slug):
    return chapter_slug.replace("chapter-", "")
