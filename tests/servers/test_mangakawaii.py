import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mangakawaii_server():
    from komikku.servers.mangakawaii import Mangakawaii

    return Mangakawaii()


def test_search_mangakawaii(mangakawaii_server):
    try:
        response = mangakawaii_server.search('tales of demons')
        print('Mangakawaii: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_mangakawaii(mangakawaii_server):
    try:
        response = mangakawaii_server.get_most_populars()
        print('Mangakawaii: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_mangakawaii(mangakawaii_server):
    try:
        response = mangakawaii_server.get_manga_data(dict(slug='yaoshenji'))
        print('Mangakawaii: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_mangakawaii(mangakawaii_server):
    try:
        response = mangakawaii_server.get_manga_chapter_data('yaoshenji', '251', None)
        print('Mangakawaii: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_mangakawaii(mangakawaii_server):
    try:
        response = mangakawaii_server.get_manga_chapter_page_image('yaoshenji', None, '10', dict(slug='01.jpg'))
        print('Mangakawaii: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
