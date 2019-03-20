import glob
import importlib
import inspect
import os


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
