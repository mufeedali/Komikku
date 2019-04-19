import datetime
from gettext import gettext as _
import importlib
import json
import os
from pathlib import Path
import sqlite3
import shutil

user_app_dir_path = os.path.join(str(Path.home()), 'MangaScan')
db_path = os.path.join(user_app_dir_path, 'mangascan.db')


def adapt_json(data):
    return (json.dumps(data, sort_keys=True)).encode()


def convert_json(blob):
    return json.loads(blob.decode())


sqlite3.register_adapter(dict, adapt_json)
sqlite3.register_adapter(list, adapt_json)
sqlite3.register_adapter(tuple, adapt_json)
sqlite3.register_converter('json', convert_json)


def create_db_connection():
    con = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    if con is None:
        print("Error: Can not create the database connection.")
        return None

    con.row_factory = sqlite3.Row
    return con


def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Exception as e:
        print(e)


def init_db():
    if not os.path.exists(user_app_dir_path):
        os.mkdir(user_app_dir_path)

    sql_create_mangas_table = """CREATE TABLE IF NOT EXISTS mangas (
        id integer PRIMARY KEY,
        slug text NOT NULL,
        server_id text NOT NULL,
        name text NOT NULL,
        author text,
        genres json,
        synopsis text,
        status text,
        cover_path text,
        sort text,
        last_read timestamp,
        last_update timestamp,
        UNIQUE (slug, server_id)
    );"""

    sql_create_chapters_table = """CREATE TABLE IF NOT EXISTS chapters (
        id integer PRIMARY KEY,
        slug text NOT NULL,
        manga_id integer REFERENCES mangas(id) ON DELETE CASCADE,
        title text NOT NULL,
        pages json,
        date text,
        rank integer,
        downloaded integer,
        last_page_read_index integer,
        UNIQUE (slug, manga_id)
    );"""

    db_conn = create_db_connection()
    if db_conn is not None:
        create_table(db_conn, sql_create_mangas_table)
        create_table(db_conn, sql_create_chapters_table)

        db_conn.close()


def update_row(table, id, data):
    db_conn = create_db_connection()
    with db_conn:
        db_conn.execute(
            'UPDATE {0} SET {1} WHERE id = ?'.format(table, ', '.join([k + ' = ?' for k in data.keys()])),
            tuple(data.values()) + (id,)
        )
    db_conn.close()


class Manga(object):
    chapters_ = None
    server = None

    STATUSES = dict(
        complete=_('Complete'),
        ongoing=_('Ongoing')
    )

    def __init__(self, id=None, server=None):
        if server:
            self.server = server

        if id is not None:
            db_conn = create_db_connection()
            row = db_conn.execute('SELECT * FROM mangas WHERE id = ?', (id,)).fetchone()
            for key in row.keys():
                setattr(self, key, row[key])

            if server is None:
                server_module = importlib.import_module('.' + self.server_id, package="mangascan.servers")
                self.server = getattr(server_module, self.server_id.capitalize())()

    @classmethod
    def new(cls, data, server=None):
        m = cls(server=server)
        m._save(data.copy())

        return m

    @property
    def chapters(self):
        if self.chapters_ is None:
            db_conn = create_db_connection()
            rows = db_conn.execute('SELECT id FROM chapters WHERE manga_id = ? ORDER BY rank DESC', (self.id,)).fetchall()
            db_conn.close()

            self.chapters_ = []
            for row in rows:
                self.chapters_.append(Chapter(row['id']))

        return self.chapters_

    @property
    def cover_fs_path(self):
        path = os.path.join(self.resources_path, 'cover.jpg')
        if os.path.exists(path):
            return path
        else:
            return None

    @property
    def resources_path(self):
        return os.path.join(str(Path.home()), 'MangaScan', self.server_id, self.name)

    def delete(self):
        db_conn = create_db_connection()
        # Enable integrity constraint
        db_conn.execute('PRAGMA foreign_keys = ON')

        with db_conn:
            db_conn.execute('DELETE FROM mangas WHERE id = ?', (self.id, ))

            if os.path.exists(self.resources_path):
                shutil.rmtree(self.resources_path)

        db_conn.close()

    def _save(self, data):
        # Fill data with internal data or not yet scraped values
        data.update(dict(
            last_read=datetime.datetime.now(),
            last_update=None,
        ))

        chapters = data.pop('chapters')

        for key in data.keys():
            setattr(self, key, data[key])

        db_conn = create_db_connection()
        with db_conn:
            cursor = db_conn.execute(
                'INSERT INTO mangas (slug, server_id, name, author, genres, synopsis, status, last_read) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (self.slug, self.server_id, self.name, self.author, self.genres, self.synopsis, self.status, self.last_read)
            )
            self.id = cursor.lastrowid
        db_conn.close()

        self.chapters_ = []
        for rank, chapter_data in enumerate(chapters):
            chapter = Chapter.new(chapter_data, rank, self.id)
            self.chapters_ = [chapter, ] + self.chapters_

        if not os.path.exists(self.resources_path):
            os.makedirs(self.resources_path)

        # Save cover image file
        cover_fs_path = os.path.join(self.resources_path, 'cover.jpg')
        if not os.path.exists(cover_fs_path):
            cover_data = self.server.get_manga_cover_image(self.cover_path)
            if cover_data is not None:
                with open(cover_fs_path, 'wb') as fp:
                    fp.write(cover_data)

    def update(self, data=None):
        """
        Updates manga

        :param data: dictionary of fields to update

        If data is None, fetches and saves data available in manga's HTML page on server
        """
        if data is None:
            data = self.server.get_manga_data(dict(slug=self.slug, name=self.name))
            chapters_data = data.pop('chapters')

            # Update chapters
            db_conn = create_db_connection()

            updated = False
            for rank, chapter_data in enumerate(chapters_data):
                row = db_conn.execute(
                    'SELECT * FROM chapters WHERE manga_id = ? AND slug = ?', (self.id, chapter_data['slug'])
                ).fetchone()
                if row:
                    # Update chapter
                    chapter = Chapter(row['id'])
                    chapter_data['rank'] = rank
                    chapter.update(chapter_data)
                else:
                    # Add new chapter
                    Chapter.new(chapter_data, rank, self.id)
                    updated = True

            if updated:
                data['last_update'] = datetime.datetime.now()

            self.chapters_ = None

            db_conn.close()

        for key in data.keys():
            setattr(self, key, data[key])

        update_row('mangas', self.id, data)


class Chapter(object):
    manga_ = None

    def __init__(self, id=None):
        if id:
            db_conn = create_db_connection()
            row = db_conn.execute('SELECT * FROM chapters WHERE id = ?', (id,)).fetchone()
            db_conn.close()

            for key in row.keys():
                setattr(self, key, row[key])

    @property
    def manga(self):
        if self.manga_ is None:
            self.manga_ = Manga(self.manga_id)

        return self.manga_

    @classmethod
    def new(cls, data, rank, manga_id):
        c = cls()
        c._save(data.copy(), rank, manga_id)

        return c

    def purge(self):
        chapter_path = os.path.join(self.manga.resources_path, self.slug)
        if os.path.exists(chapter_path):
            shutil.rmtree(chapter_path)

        self.update(dict(
            pages=None,
            last_page_read_index=None,
            downloaded=0,
        ))

    def get_page(self, page_index):
        chapter_path = os.path.join(self.manga.resources_path, self.slug)

        if not os.path.exists(chapter_path):
            os.mkdir(chapter_path)

        # self.pages[page_index]['image'] can be an image name or an image path
        imagename = self.pages[page_index]['image'].split('/')[-1] if self.pages[page_index]['image'] else None
        if imagename is not None:
            page_path = os.path.join(chapter_path, imagename)
            if os.path.exists(page_path):
                return page_path

        imagename, data = self.manga.server.get_manga_chapter_page_image(self.manga.slug, self.slug, self.pages[page_index])

        if imagename and data:
            page_path = os.path.join(chapter_path, imagename)
            with open(page_path, 'wb') as fp:
                fp.write(data)

            if self.pages[page_index]['image'] is None:
                self.pages[page_index]['image'] = imagename
                self.update(dict(pages=self.pages))

            return page_path
        else:
            return None

    def _save(self, data, rank, manga_id):
        # Fill data with internal data or not yet scraped values
        data.update(dict(
            pages=None,  # later scraped value
            last_page_read_index=None,
            rank=rank,
            downloaded=0,
        ))

        self.manga_id = manga_id

        for key in data.keys():
            setattr(self, key, data[key])

        db_conn = create_db_connection()
        with db_conn:
            cursor = db_conn.execute(
                'INSERT INTO chapters (slug, manga_id, title, date, rank, downloaded) VALUES (?, ?, ?, ?, ?, ?)',
                (self.slug, self.manga_id, self.title, self.date, rank, 0)
            )
            self.id = cursor.lastrowid
        db_conn.close()

    def update(self, data=None):
        """
        Updates chapter

        :param data: dictionary of fields to update

        If data is None, fetches and saves data available in chapter's HTML page on server
        """
        if data is None:
            if self.pages:
                return

            data = self.manga.server.get_manga_chapter_data(self.manga.slug, self.slug)

        for key in data.keys():
            setattr(self, key, data[key])

        update_row('chapters', self.id, data)
