from importlib import resources
from operator import itemgetter
import os
from PIL import Image

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


def unscramble_image(scrambled_image, image_full_path):
    input_image = Image.open(scrambled_image)
    temp = Image.new("RGB", input_image.size)
    output_image = Image.new("RGB", input_image.size)

    for x in range(0, input_image.width, 200):
        col1 = input_image.crop((x, 0, x + 100, input_image.height))

        if (x + 200) <= input_image.width:
            col2 = input_image.crop((x + 100, 0, x + 200, input_image.height))
            temp.paste(col1, (x + 100, 0))
            temp.paste(col2, (x, 0))
        else:
            col2 = input_image.crop((x + 100, 0, input_image.width, input_image.height))
            temp.paste(col1, (x, 0))
            temp.paste(col2, (x + 100, 0))

    for y in range(0, temp.height, 200):
        row1 = temp.crop((0, y, temp.width, y + 100))

        if (y + 200) <= temp.height:
            row2 = temp.crop((0, y + 100, temp.width, y + 200))
            output_image.paste(row1, (0, y + 100))
            output_image.paste(row2, (0, y))
        else:
            row2 = temp.crop((0, y + 100, temp.width, temp.height))
            output_image.paste(row1, (0, y))
            output_image.paste(row2, (0, y + 100))

    os.remove(scrambled_image)

    output_image.save(image_full_path)
