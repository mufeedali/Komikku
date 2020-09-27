import logging
import pytest
from pytest_steps import test_steps

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def dynasty_server():
    from komikku.servers.dynasty import Dynasty
    return Dynasty()


@pytest.fixture
def test_dynasty_common():
    def helper(dynasty_server, term, **settings):
        print('Search')
        try:
            response = dynasty_server.search(term, **settings)
            slug = response[0]['slug']
        except Exception as e:
            slug = None
            log_error_traceback(e)

        assert slug is not None
        yield

        print('Get manga url')
        try:
            response = dynasty_server.get_manga_url(slug, None)
            url = response
        except Exception as e:
            url = None
            log_error_traceback(e)

        assert url is not None
        yield

        # Get manga data
        print('Get manga data')
        try:
            response = dynasty_server.get_manga_data(dict(slug=slug))
            chapter_slug = response['chapters'][0]['slug']
        except Exception as e:
            chapter_slug = None
            log_error_traceback(e)

        assert chapter_slug is not None
        yield

        # Get chapter data
        print("Get chapter data")
        try:
            response = dynasty_server.get_manga_chapter_data(slug, None, chapter_slug, None)
            page = response['pages'][0]
        except Exception as e:
            page = None
            log_error_traceback(e)

        assert page is not None
        yield

        # Get page image
        print('Get page image')
        try:
            response = dynasty_server.get_manga_chapter_page_image(None, None, None, page)
        except Exception as e:
            response = None
            log_error_traceback(e)

        assert response is not None
        yield
    return helper


@test_steps('search', 'get_manga_url', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_dynasty_anthologies(dynasty_server, test_dynasty_common):
    for step in test_dynasty_common(dynasty_server, 'eclair', classes=['Anthology']):
        yield step


@test_steps('search', 'get_manga_url', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_dynasty_doujins(dynasty_server, test_dynasty_common):
    for step in test_dynasty_common(dynasty_server, 'nanoha', classes=['Doujin']):
        yield step


@test_steps('search', 'get_manga_url', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_dynasty_issues(dynasty_server, test_dynasty_common):
    for step in test_dynasty_common(dynasty_server, 'yuri hime', classes=['Issue']):
        yield step


@test_steps('search', 'get_manga_url', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_dynasty_series(dynasty_server, test_dynasty_common):
    for step in test_dynasty_common(dynasty_server, 'room for two', classes=['Series']):
        yield step


@test_steps('search', 'get_manga_url', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_broken_cover(dynasty_server, test_dynasty_common):
    for step in test_dynasty_common(dynasty_server, 'she becomes a tree', classes=['Series']):
        yield step
