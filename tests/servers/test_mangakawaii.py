import logging
import pytest
from pytest_steps import test_steps

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mangakawaii_server():
    from komikku.servers.mangakawaii import Mangakawaii

    return Mangakawaii()


@test_steps('get_most_popular', 'search', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_mangakawaii(mangakawaii_server):
    # Get most popular
    print('Get most popular')
    try:
        response = mangakawaii_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Search
    print('Search')
    try:
        response = mangakawaii_server.search('tales of demons and gods')
        slug = response[0]['slug']
    except Exception as e:
        slug = None
        log_error_traceback(e)

    assert slug is not None
    yield

    # Get manga data
    print('Get manga data')
    try:
        response = mangakawaii_server.get_manga_data(dict(slug=slug))
        chapter_slug = response['chapters'][0]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print("Get chapter data")
    try:
        response = mangakawaii_server.get_manga_chapter_data(slug, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = mangakawaii_server.get_manga_chapter_page_image(slug, None, chapter_slug, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield
