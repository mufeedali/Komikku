import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def xkcd_server():
    from komikku.servers.xkcd import Xkcd

    return Xkcd()


def test_search_xkcd(xkcd_server):
    try:
        response = xkcd_server.search()
        print('xkcd: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_xkcd(xkcd_server):
    try:
        response = xkcd_server.get_manga_data(dict())
        print('xkcd: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_xkcd(xkcd_server):
    try:
        response = xkcd_server.get_manga_chapter_data(None, None, '1', None)
        print('xkcd: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_xkcd(xkcd_server):
    try:
        response = xkcd_server.get_manga_chapter_page_image(None, None, None, dict(image='barrel_cropped_(1).jpg'))
        print('xkcd: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
