import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def jaiminisbox_server():
    from komikku.servers.jaiminisbox import Jaiminisbox

    return Jaiminisbox()


def test_search_jaiminisbox(jaiminisbox_server):
    try:
        response = jaiminisbox_server.search('solo leveling')
        print('Jaimini\'s Box: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_jaiminisbox(jaiminisbox_server):
    try:
        response = jaiminisbox_server.get_most_populars()
        print('Jaimini\'s Box: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_jaiminisbox(jaiminisbox_server):
    try:
        response = jaiminisbox_server.get_manga_data(dict(slug='solo-leveling'))
        print('Jaimini\'s Box: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_jaiminisbox(jaiminisbox_server):
    try:
        response = jaiminisbox_server.get_manga_chapter_data('solo-leveling', '0/0', None)
        print('Jaimini\'s Box: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_jaiminisbox(jaiminisbox_server):
    try:
        response = jaiminisbox_server.get_manga_chapter_page_image(
            None, None, None,
            dict(
                image='https://i2.wp.com/jaiminisbox.com/reader/content/comics/solo-leveling_5c5b0f9edeb41/0-0_5d046cc814344/001.png?quality=100&strip=all'
            ))
        print('Jaimini\'s Box: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
