import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def manganelo_server():
    from komikku.servers.manganelo import Manganelo

    return Manganelo()


def test_search_manganelo(manganelo_server):
    try:
        response = manganelo_server.search('tales of demons')
        print('Manganelo: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_manganelo(manganelo_server):
    try:
        response = manganelo_server.get_most_populars()
        print('Manganelo: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_manganelo(manganelo_server):
    try:
        response = manganelo_server.get_manga_data(dict(slug='hyer5231574354229'))
        print('Manganelo: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_manganelo(manganelo_server):
    try:
        response = manganelo_server.get_manga_chapter_data('hyer5231574354229', 'chapter_1', None)
        print('Manganelo: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_manganelo(manganelo_server):
    try:
        response = manganelo_server.get_manga_chapter_page_image(None, None, None, dict(image='https://s5.mkklcdnv5.com/mangakakalot/t1/tales_of_demons_and_gods/chapter_1_rebirth/15.jpg'))
        print('Manganelo: get manga chapter page image')
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None
