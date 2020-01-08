import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def scanonepiece_server():
    from komikku.servers.scanonepiece import Scanonepiece

    return Scanonepiece()


def test_search_scanonepiece(scanonepiece_server):
    try:
        response = scanonepiece_server.search('tales of demons')
        print('Scanonepiece: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_scanonepiece(scanonepiece_server):
    try:
        response = scanonepiece_server.get_most_populars()
        print('Scanonepiece: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_scanonepiece(scanonepiece_server):
    try:
        response = scanonepiece_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
        print('Scanonepiece: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_scanonepiece(scanonepiece_server):
    try:
        response = scanonepiece_server.get_manga_chapter_data('tales-of-demons-and-gods', 'chapitre-1', None)
        print('Scanonepiece: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_scanonepiece(scanonepiece_server):
    try:
        response = scanonepiece_server.get_manga_chapter_page_image('tales-of-demons-and-gods', None, 'chapitre-1', dict(image='01.jpg'))
        print('Scanonepiece: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
