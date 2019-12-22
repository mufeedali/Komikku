import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def peppercarrot_server():
    from komikku.servers.peppercarrot import Peppercarrot

    return Peppercarrot()


def test_search_peppercarrot(peppercarrot_server):
    try:
        response = peppercarrot_server.search()
        print('Pepper&Carrot: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_peppercarrot(peppercarrot_server):
    try:
        response = peppercarrot_server.get_manga_data(dict())
        print('Pepper&Carrot: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_peppercarrot(peppercarrot_server):
    try:
        response = peppercarrot_server.get_manga_chapter_data(None, 'ep01_Potion-of-Flight', None)
        print('Pepper&Carrot: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_peppercarrot(peppercarrot_server):
    try:
        response = peppercarrot_server.get_manga_chapter_page_image(
            None, None, 'ep01_Potion-of-Flight', dict(slug='Pepper-and-Carrot_by-David-Revoy_E01.jpg'))
        print('Pepper&Carrot: get manga chapter page image')
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None
