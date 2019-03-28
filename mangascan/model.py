import importlib
import os
from pathlib import Path
import sqlite3
import shutil

user_app_dir_path = os.path.join(str(Path.home()), 'MangaScan')
db_path = os.path.join(user_app_dir_path, 'mangascan.db')


def adapt_stringlist(l):
    return ','.join(l)


def convert_stringlist(s):
    # s is a byte string
    return s.decode().split(',')


sqlite3.register_adapter(list, adapt_stringlist)
sqlite3.register_converter('stringlist', convert_stringlist)


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
        types text,
        synopsis text,
        status text,
        last_read timestamp,
        last_update timestamp,
        UNIQUE (slug, server_id)
    );"""

    sql_create_chapters_table = """CREATE TABLE IF NOT EXISTS chapters (
        id integer PRIMARY KEY,
        slug text NOT NULL,
        manga_id integer REFERENCES mangas(id) ON DELETE CASCADE,
        title text NOT NULL,
        pages stringlist,
        date text,
        rank integer,
        last_page_read_index integer,
        UNIQUE (slug, manga_id)
    );"""

    db_conn = create_db_connection()
    if db_conn is not None:
        create_table(db_conn, sql_create_mangas_table)
        create_table(db_conn, sql_create_chapters_table)

        db_conn.close()


class Manga(object):
    server = None

    def __init__(self, id=None, server=None):
        if server:
            self.server = server

        if id is not None:
            db_conn = create_db_connection()
            row = db_conn.execute('SELECT * FROM mangas WHERE id = ?', (id,)).fetchone()
            for key in row.keys():
                setattr(self, key, row[key])

            rows = db_conn.execute('SELECT id FROM chapters WHERE manga_id = ? ORDER BY rank DESC', (id,)).fetchall()
            db_conn.close()

            self.chapters = []
            for row in rows:
                chapter = Chapter(row['id'])
                chapter.manga = self
                self.chapters.append(chapter)

            if server is None:
                server_module = importlib.import_module('.' + self.server_id, package="mangascan.servers")
                self.server = getattr(server_module, self.server_id.capitalize())()

    @classmethod
    def new(cls, data, server=None):
        m = cls(server=server)
        m._save(data.copy())

        return m

    @property
    def cover_path(self):
        path = os.path.join(self.resources_path, 'cover.jpg')
        if os.path.exists(path):
            return path
        else:
            return None

    @property
    def resources_path(self):
        return os.path.join(str(Path.home()), 'MangaScan', self.server_id, self.slug)

    def delete(self):
        db_conn = create_db_connection()
        # Enable integrity constraint
        db_conn.execute('PRAGMA foreign_keys = ON')

        with db_conn:
            db_conn.execute('DELETE FROM mangas WHERE id = ?', (self.id, ))

            shutil.rmtree(self.resources_path)

        db_conn.close()

    def _save(self, data):
        # Fill data with internal data or not yet scraped values
        data.update(dict(
            last_read=None,
            last_update=None,
        ))

        chapters = data.pop('chapters')

        for key in data.keys():
            setattr(self, key, data[key])

        db_conn = create_db_connection()
        with db_conn:
            cursor = db_conn.execute(
                'INSERT INTO mangas (slug, server_id, name, author, types, synopsis, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (self.slug, self.server_id, self.name, self.author, self.types, self.synopsis, self.status)
            )
            self.id = cursor.lastrowid
        db_conn.close()

        self.chapters = []
        for rank, chapter_data in enumerate(chapters):
            chapter = Chapter.new(chapter_data, rank, self.id)
            chapter.manga = self
            self.chapters.append(chapter)

        if not os.path.exists(self.resources_path):
            os.makedirs(self.resources_path)

        # Save cover image file
        cover_path = os.path.join(self.resources_path, 'cover.jpg')
        if not os.path.exists(cover_path):
            cover_data = self.server.get_manga_cover_image(self.slug)
            with open(cover_path, 'wb') as fp:
                fp.write(cover_data)

    def update(self, data):
        """
        Updates manga

        :param data: dictionary of fields to update
        """
        for key in data.keys():
            setattr(self, key, data[key])

        db_conn = create_db_connection()
        with db_conn:
            db_conn.execute(
                'UPDATE mangas SET {0} WHERE id = ?'.format(', '.join([k + ' = ?' for k in data.keys()])),
                tuple(data.values()) + (self.id,)
            )
        db_conn.close()


class Chapter(object):
    def __init__(self, id=None, manga=None):
        if id:
            db_conn = create_db_connection()
            row = db_conn.execute('SELECT * FROM chapters WHERE id = ?', (id,)).fetchone()
            db_conn.close()

            for key in row.keys():
                setattr(self, key, row[key])

            if manga:
                self.manga = manga

    @classmethod
    def new(cls, data, rank, manga_id):
        c = cls()
        c._save(data.copy(), rank, manga_id)

        return c

    def purge(self):
        chapter_path = os.path.join(self.manga.resources_path, self.slug)
        shutil.rmtree(chapter_path)

        self.update(dict(
            pages=None,
            last_page_read_index=0,
        ))

    def get_page(self, page_index):
        chapter_path = os.path.join(self.manga.resources_path, self.slug)

        if not os.path.exists(chapter_path):
            os.mkdir(chapter_path)

        page = self.pages[page_index]
        page_path = os.path.join(chapter_path, page)
        if os.path.exists(page_path):
            return page_path

        data = self.manga.server.get_manga_chapter_page_image(self.manga.slug, self.slug, page)

        if data:
            with open(page_path, 'wb') as fp:
                fp.write(data)

            return page_path
        else:
            return None

    def _save(self, data, rank, manga_id):
        # Fill data with internal data or not yet scraped values
        data.update(dict(
            pages=None,  # later scraped value
            last_page_read_index=0,
            rank=rank,
        ))

        self.manga_id = manga_id

        for key in data.keys():
            setattr(self, key, data[key])

        db_conn = create_db_connection()
        with db_conn:
            cursor = db_conn.execute(
                'INSERT INTO chapters (slug, manga_id, title, pages, date, rank, last_page_read_index) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (self.slug, self.manga_id, self.title, None, self.date, rank, 0)
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

        db_conn = create_db_connection()
        with db_conn:
            db_conn.execute(
                'UPDATE chapters SET {0} WHERE id = ?'.format(', '.join([k + ' = ?' for k in data.keys()])),
                tuple(data.values()) + (self.id,)
            )
        db_conn.close()
