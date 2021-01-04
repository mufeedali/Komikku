import logging
import pytest
from pytest_steps import test_steps

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def scanmanga_server():
    from komikku.servers.scanmanga import Scanmanga

    return Scanmanga()


@test_steps('get_most_popular', 'search_1', 'get_manga_data_1', 'get_chapter_data_1', 'get_page_image_1')
def test_scanmanga(scanmanga_server):
    # Get most popular
    print('Get most popular')
    try:
        response = scanmanga_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Search
    print('Search')
    try:
        response = scanmanga_server.search('combat continent')
        url = response[0]['url']
        slug = response[0]['slug']
    except Exception as e:
        url = None
        slug = None
        log_error_traceback(e)

    assert url is not None and slug is not None
    yield

    # Get manga data
    print('Get manga data')
    try:
        response = scanmanga_server.get_manga_data(dict(url=url, slug=slug))
        chapter_slug = response['chapters'][0]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print('Get chapter data')
    try:
        response = scanmanga_server.get_manga_chapter_data(slug, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = scanmanga_server.get_manga_chapter_page_image(slug, None, chapter_slug, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield


@test_steps('search_2', 'get_manga_data_2', 'get_chapter_data_2', 'get_page_image_2')
def test_scanmanga_2(scanmanga_server):
    # Search
    print('Search 2')
    try:
        response = scanmanga_server.search('solo leveling')
        url = response[0]['url']
        slug = response[0]['slug']
    except Exception as e:
        url = None
        slug = None
        log_error_traceback(e)

    assert url is not None and slug is not None
    yield

    # Get manga data
    print('Get manga data 2')
    try:
        response = scanmanga_server.get_manga_data(dict(url=url, slug=slug))
        chapter_slug = response['chapters'][0]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print('Get chapter data 2')
    try:
        response = scanmanga_server.get_manga_chapter_data(slug, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image 2')
    try:
        response = scanmanga_server.get_manga_chapter_page_image(slug, None, chapter_slug, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield
