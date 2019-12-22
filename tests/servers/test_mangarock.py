import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mangarock_server():
    from komikku.servers.mangarock import Mangarock

    return Mangarock()


def test_search_mangarock(mangarock_server):
    try:
        response = mangarock_server.search('tales of demons')
        print('Mangarock: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_mangarock(mangarock_server):
    try:
        response = mangarock_server.get_most_populars()
        print('Mangarock: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_mangarock(mangarock_server):
    try:
        response = mangarock_server.get_manga_data(dict(slug='mrs-serie-240647'))
        print('Mangarock: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_mangarock(mangarock_server):
    try:
        response = mangarock_server.get_manga_chapter_data(None, 'mrs-chapter-240648', None)
        print('Mangarock: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_mangarock(mangarock_server):
    try:
        response = mangarock_server.get_manga_chapter_page_image(None, None, None, dict(image='https://f01.mrcdn.info/file/mrfiles/i/4/o/1/o.k2eogSxp.mri'))
        print('Mangarock: get manga chapter page image')
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None
