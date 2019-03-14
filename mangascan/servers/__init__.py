import glob
import importlib
import inspect
import json
import os
from pathlib import Path


def get_servers_list():
    sl = []
    current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    current_module_name = os.path.splitext(os.path.basename(current_dir))[0]

    for file in glob.glob(current_dir + "/*.py"):
        name = os.path.splitext(os.path.basename(file))[0]

        # Ignore __ files
        if name.startswith("__"):
            continue

        module = importlib.import_module("." + name, package="mangascan." + current_module_name)

        info = dict()
        for member in dir(module):
            attr = getattr(module, member)

            if member == 'server_id':
                info['id'] = attr
            elif member == 'server_name':
                info['name'] = attr
            elif member == 'server_country':
                info['country'] = attr
            elif inspect.isclass(attr) and attr.__module__.startswith('mangascan.servers') and member != 'Server':
                info['class'] = attr

        sl.append(info)

    return sl


class Server():
    def get_manga_cover(self):
        raise NotImplementedError()

    def get_manga_data(self):
        raise NotImplementedError()

    def save_manga_data_and_cover(self, data):
        resources_path = os.path.join(str(Path.home()), 'MangaScan', data['id'])

        if not os.path.exists(resources_path):
            os.makedirs(resources_path)

        with open(os.path.join(resources_path, 'data.json'), 'w') as fp:
            json.dump(data, fp)

        cover_data = self.get_manga_cover_image(data['id'])
        with open(os.path.join(resources_path, 'cover.jpg'), 'wb') as fp:
            fp.write(cover_data)

    def search(self):
        raise NotImplementedError
