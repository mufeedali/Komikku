from importlib import resources
from operator import itemgetter

user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/60"
user_agent_mobile = 'Mozilla/5.0 (Linux; U; Android 4.1.1; en-gb; Build/KLP) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Safari/534.30'


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
