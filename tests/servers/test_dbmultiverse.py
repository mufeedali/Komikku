import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def dbmultiverse_server():
    from komikku.servers.dbmultiverse import Dbmultiverse

    return Dbmultiverse()


def test_search_dbmultiverse(dbmultiverse_server):
    try:
        response = dbmultiverse_server.search()
        print('DB Multiverse: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_dbmultiverse(dbmultiverse_server):
    try:
        response = dbmultiverse_server.get_manga_data(dict())
        print('DB Multiverse: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_dbmultiverse(dbmultiverse_server):
    try:
        response = dbmultiverse_server.get_manga_chapter_data(None, None, '1', None)
        print('DB Multiverse: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_dbmultiverse(dbmultiverse_server):
    try:
        response = dbmultiverse_server.get_manga_chapter_page_image(None, None, None, dict(slug='0'))
        print('DB Multiverse: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
