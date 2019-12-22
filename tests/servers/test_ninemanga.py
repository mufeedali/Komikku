import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def ninemanga_server():
    from komikku.servers.ninemanga import Ninemanga

    return Ninemanga()


def test_search_ninemanga(ninemanga_server):
    try:
        response = ninemanga_server.search('tales of demons')
        print('Ninemanga: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_ninemanga(ninemanga_server):
    try:
        response = ninemanga_server.get_most_populars()
        print('Ninemanga: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_ninemanga(ninemanga_server):
    try:
        response = ninemanga_server.get_manga_data(dict(slug='Tales of Demons and Gods'))
        print('Ninemanga: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_ninemanga(ninemanga_server):
    try:
        response = ninemanga_server.get_manga_chapter_data('Tales of Demons and Gods', '1467410', None)
        print('Ninemanga: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_ninemanga(ninemanga_server):
    try:
        response = ninemanga_server.get_manga_chapter_page_image('Tales of Demons and Gods', None, None, dict(slug='1467410-1.html'))
        print('Ninemanga: get manga chapter page image')
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None
