import dateparser
import datetime
from importlib import resources
import io
import magic
from operator import itemgetter
import os
from PIL import Image
from requests.exceptions import ConnectionError
import struct

SESSIONS = dict()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/60"
USER_AGENT_MOBILE = 'Mozilla/5.0 (Linux; U; Android 4.1.1; en-gb; Build/KLP) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Safari/534.30'

LANGUAGES = dict(
    de='Deutsch',
    en='English',
    es='Español',
    fr='Français',
    id='Indonesia',
    it='Italiano',
    pt='Português',
    ru='русский',
    th='ภาษาไทย',
)


class Server:
    id = NotImplemented
    name = NotImplemented
    lang = NotImplemented

    base_url = None

    @property
    def session(self):
        return SESSIONS.get(self.id)

    @session.setter
    def session(self, value):
        SESSIONS[self.id] = value

    def get_manga_cover_image(self, url):
        """
        Returns manga cover (image) content
        """
        if url is None:
            return None

        try:
            r = self.session.get(url, headers={'referer': self.base_url})
        except (ConnectionError, RuntimeError):
            return None

        if r.status_code != 200:
            return None

        buffer = r.content
        mime_type = magic.from_buffer(buffer[:128], mime=True)

        if not mime_type.startswith('image'):
            return None

        if mime_type == 'image/webp':
            buffer = convert_webp_buffer(buffer)

        return buffer


def convert_date_string(date, format=None):
    if format is not None:
        try:
            d = datetime.datetime.strptime(date, format)
        except Exception:
            d = dateparser.parse(date)
    else:
        d = dateparser.parse(date)

    return d.date()


# https://github.com/italomaia/mangarock.py/blob/master/mangarock/mri_to_webp.py
def convert_mri_data_to_webp_buffer(data):
    size_list = [0] * 4
    size = len(data)
    header_size = size + 7

    # little endian byte representation
    # zeros to the right don't change the value
    for i, byte in enumerate(struct.pack("<I", header_size)):
        size_list[i] = byte

    buffer = [
        82,  # R
        73,  # I
        70,  # F
        70,  # F
        size_list[0],
        size_list[1],
        size_list[2],
        size_list[3],
        87,  # W
        69,  # E
        66,  # B
        80,  # P
        86,  # V
        80,  # P
        56,  # 8
    ]

    for bit in data:
        buffer.append(101 ^ bit)

    return bytes(buffer)


def convert_webp_buffer(webp_buffer, format='JPEG'):
    image = Image.open(io.BytesIO(webp_buffer))

    buffer = io.BytesIO()
    image.save(buffer, format)

    return buffer.getvalue()


def get_servers_list():
    servers_list = []

    for server in resources.contents(package='komikku.servers'):
        # Ignore __ files
        if server.startswith('__'):
            continue

        # Get servers properties: id, name, lang
        # For reasons of speed, we don't want import modules
        info = dict()
        with resources.open_text('komikku.servers', server) as fid:
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


# https://github.com/Harkame/JapScanDownloader
def unscramble_image(scrambled_image, image_full_path):
    input_image = Image.open(scrambled_image)
    temp = Image.new('RGB', input_image.size)
    output_image = Image.new('RGB', input_image.size)

    for x in range(0, input_image.width, 200):
        col1 = input_image.crop((x, 0, x + 100, input_image.height))

        if x + 200 <= input_image.width:
            col2 = input_image.crop((x + 100, 0, x + 200, input_image.height))
            temp.paste(col1, (x + 100, 0))
            temp.paste(col2, (x, 0))
        else:
            col2 = input_image.crop((x + 100, 0, input_image.width, input_image.height))
            temp.paste(col1, (x, 0))
            temp.paste(col2, (x + 100, 0))

    for y in range(0, temp.height, 200):
        row1 = temp.crop((0, y, temp.width, y + 100))

        if y + 200 <= temp.height:
            row2 = temp.crop((0, y + 100, temp.width, y + 200))
            output_image.paste(row1, (0, y + 100))
            output_image.paste(row2, (0, y))
        else:
            row2 = temp.crop((0, y + 100, temp.width, temp.height))
            output_image.paste(row1, (0, y))
            output_image.paste(row2, (0, y + 100))

    os.remove(scrambled_image)

    output_image.save(image_full_path)
