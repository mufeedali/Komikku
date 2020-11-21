import logging
import pytest
from pytest_steps import test_steps

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def readcomiconline_server():
    from komikku.servers.readcomiconline import Readcomiconline

    return Readcomiconline()


@test_steps('get_most_populars', 'search', 'get_manga_data', 'get_manga_chapter_data', 'get_manga_chapter_page_image')
def test_readcomiconline(readcomiconline_server):
    # Get Most Popular
    print('Get most populars')
    try:
        response = readcomiconline_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None
    yield

    # Search
    print('Search')
    try:
        response = readcomiconline_server.search('superman (2016)')
        slug = response[0]['slug']
    except Exception as e:
        slug = None
        log_error_traceback(e)
    assert slug is not None
    yield

    # Get comic data
    print('Get comic data')
    try:
        response = readcomiconline_server.get_manga_data(dict(slug=slug))
        chapter_slug = response['chapters'][1]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print("Get chapter data")
    try:
        response = readcomiconline_server.get_manga_chapter_data(slug, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = readcomiconline_server.get_manga_chapter_page_image(None, None, None, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield
