import importlib
import json
import os
from pathlib import Path
import shutil


class Manga():
    data = None
    server = None

    def __init__(self, id):
        self.id = id

        data_path = os.path.join(self.resources_path, 'data.json')

        with open(data_path) as fp:
            self.data = json.load(fp)

        server_module = importlib.import_module('.' + self.data['server_id'], package="mangascan.servers")

        self.server = getattr(server_module, self.data['server_id'].capitalize())()

    @property
    def resources_path(self):
        return os.path.join(str(Path.home()), 'MangaScan', self.id)

    def delete(self):
        shutil.rmtree(self.resources_path)

    def get_chapter_page(self, chapter_id, page_index):
        chapter_path = os.path.join(self.resources_path, chapter_id)

        if not os.path.exists(chapter_path):
            os.mkdir(chapter_path)

        page = self.data['chapters'][chapter_id]['pages'][page_index]
        page_path = os.path.join(chapter_path, page)
        if os.path.exists(page_path):
            return page_path

        data = self.server.get_manga_chapter_page_image(self.id, chapter_id, page)

        if data:
            with open(page_path, 'wb') as fp:
                fp.write(data)

            return page_path
        else:
            return None

    def update_chapter_data(self, chapter_id):
        if self.data['chapters'][chapter_id].get('pages'):
            return

        chapter_data = self.server.get_manga_chapter_data(self.id, chapter_id)
        print(chapter_data)
        self.data['chapters'][chapter_id].update(chapter_data)

        with open(os.path.join(self.resources_path, 'data.json'), 'w') as fp:
            json.dump(self.data, fp)
