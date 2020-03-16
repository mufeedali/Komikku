import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def scantrad_server():
    from komikku.servers.scantrad import Scantrad

    return Scantrad()


def test_search_scantrad(scantrad_server):
    try:
        response = scantrad_server.search('burn the witch')
        print('Scantrad: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_scantrad(scantrad_server):
    try:
        response = scantrad_server.get_manga_data(dict(slug='burn-the-witch'))
        print('Scantrad: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_scantrad(scantrad_server):
    try:
        response = scantrad_server.get_manga_chapter_data('burn-the-witch', None, '1', None)
        print('Scantrad: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_scantrad(scantrad_server):
    try:
        response = scantrad_server.get_manga_chapter_page_image(None, None, None, dict(image='lel/20939.png'))
        print('Scantrad: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
