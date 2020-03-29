import logging
import pytest
from pytest_steps import test_steps

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def webtoon_server():
    from komikku.servers.webtoon import Webtoon

    return Webtoon()


@test_steps('get_most_popular', 'search', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_webtoon(webtoon_server):
    # Get most popular
    print('Get most popular')
    try:
        response = webtoon_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Search
    print('Search')
    try:
        response = webtoon_server.search('caster')
        manga_data = response[0]
    except Exception as e:
        manga_data = None
        log_error_traceback(e)

    assert manga_data and manga_data.get('url') is not None
    yield

    # Get manga data
    print('Get manga data')
    try:
        response = webtoon_server.get_manga_data(manga_data)
        chapter_url = response['chapters'][0]['url']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_url is not None
    yield

    # Get chapter data
    print("Get chapter data")
    try:
        response = webtoon_server.get_manga_chapter_data(None, None, None, chapter_url)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = webtoon_server.get_manga_chapter_page_image(None, None, None, page)
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)

    assert response[1] is not None
    yield
