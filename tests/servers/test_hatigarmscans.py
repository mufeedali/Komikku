import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def hatigarmscans_server():
    from komikku.servers.hatigarmscans import Hatigarmscans

    return Hatigarmscans()


def test_search_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.search('tales of demons')
        print('Hatigarmscans: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.get_most_populars()
        print('Hatigarmscans: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
        print('Hatigarmscans: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.get_manga_chapter_data('tales-of-demons-and-gods', '1', None)
        print('Hatigarmscans: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.get_manga_chapter_page_image('tales-of-demons-and-gods', None, '1', dict(image='01.jpg'))
        print('Hatigarmscans: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
