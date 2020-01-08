import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def japscan_server():
    from komikku.servers.japscan import Japscan

    return Japscan()


def test_search_japscan(japscan_server):
    try:
        response = japscan_server.search('tales of demons and gods')
        print('JapScan: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_japscan(japscan_server):
    try:
        response = japscan_server.get_most_populars()
        print('JapScan: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_japscan(japscan_server):
    try:
        response = japscan_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
        print('JapScan: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_japscan(japscan_server):
    try:
        response = japscan_server.get_manga_chapter_data('tales-of-demons-and-gods', '1', None)
        print('JapScan: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_japscan(japscan_server):
    try:
        response = japscan_server.get_manga_chapter_page_image(None, 'Tales Of Demons And Gods', '1', dict(image='01.jpg'))
        print('JapScan: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
