from importlib import resources
from operator import itemgetter


def get_servers_list():
    servers_list = []

    for server in resources.contents(package='mangascan.servers'):
        # Ignore __ files
        if server.startswith('__'):
            continue

        # Get servers properties: id, name, lang
        # For reasons of speed, we don't want import modules
        info = dict()
        with resources.open_text('mangascan.servers', server) as fid:
            for line in fid.readlines():
                if line.startswith('class'):
                    break

                if line.startswith('server_'):
                    prop, value = line.strip().split(' = ')
                    info[prop.strip().replace('server_', '')] = value.strip().replace("'", '')

            info['class'] = info['id'].capitalize()
            servers_list.append(info)

    servers_list = sorted(servers_list, key=itemgetter('lang', 'name'))

    return servers_list
