import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def centraldemangas_server():
    from komikku.servers.centraldemangas import Centraldemangas

    return Centraldemangas()


def test_search_centraldemangas(centraldemangas_server):
    try:
        response = centraldemangas_server.search('tales of demons and gods')
        print('Central de mangas: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_centraldemangas(centraldemangas_server):
    try:
        response = centraldemangas_server.get_most_populars()
        print('Central de mangas: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_centraldemangas(centraldemangas_server):
    try:
        response = centraldemangas_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
        print('Central de mangas: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_centraldemangas(centraldemangas_server):
    try:
        response = centraldemangas_server.get_manga_chapter_data('tales-of-demons-and-gods', None, '001')
        print('Central de mangas: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_centraldemangas(centraldemangas_server):
    try:
        response = centraldemangas_server.get_manga_chapter_page_image(
            'tales-of-demons-and-gods', None, '001',
            dict(image='http://mangas2016.centraldemangas.com.br/tales_of_demons_and_gods/tales_of_demons_and_gods001-02.jpg'))
        print('Central de mangas: get manga chapter page image')
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None
