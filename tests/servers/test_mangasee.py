import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mangasee_server():
    from komikku.servers.mangasee import Mangasee

    return Mangasee()


def test_search_mangasee(mangasee_server):
    try:
        response = mangasee_server.search('tales of demons')
        print('Mangasee: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_mangasee(mangasee_server):
    try:
        response = mangasee_server.get_most_populars()
        print('Mangasee: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_mangasee(mangasee_server):
    try:
        response = mangasee_server.get_manga_data(dict(slug='Tales-Of-Demons-And-Gods'))
        print('Mangasee: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_mangasee(mangasee_server):
    try:
        response = mangasee_server.get_manga_chapter_data('Tales-Of-Demons-And-Gods', None, '1', None)
        print('Mangasee: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_mangasee(mangasee_server):
    try:
        response = mangasee_server.get_manga_chapter_page_image('Tales-Of-Demons-And-Gods', None, '1', dict(slug='1'))
        print('Mangasee: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
