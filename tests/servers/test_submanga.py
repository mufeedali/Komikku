import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def submanga_server():
    from komikku.servers.submanga import Submanga

    return Submanga()


def test_search_submanga(submanga_server):
    try:
        response = submanga_server.search('tales of demons')
        print('Submanga: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_submanga(submanga_server):
    try:
        response = submanga_server.get_most_populars()
        print('Submanga: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_submanga(submanga_server):
    try:
        response = submanga_server.get_most_populars()
        print('Submanga: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_submanga(submanga_server):
    try:
        response = submanga_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
        print('Submanga: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_submanga(submanga_server):
    try:
        response = submanga_server.get_manga_chapter_data('tales-of-demons-and-gods', '1', None)
        print('Submanga: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_submanga(submanga_server):
    try:
        response = submanga_server.get_manga_chapter_page_image('tales-of-demons-and-gods', None, '1', dict(image='01.jpg'))
        print('Submanga: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
