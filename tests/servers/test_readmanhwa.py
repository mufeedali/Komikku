import logging
import pytest
from pytest_steps import test_steps

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def readmanhwa_server():
    from komikku.servers.readmanhwa import Readmanhwa

    return Readmanhwa()


@test_steps('get_most_populars', 'search', 'get_manga_chapters_slug')
def test_readmanhwa(readmanhwa_server):
    # Get Most Popular
    print('Get most popular')
    try:
        response = readmanhwa_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None
    yield

    # Search
    print('Search')
    try:
        response = readmanhwa_server.search('Solo leveling')
        slug = response[0]['slug']
    except Exception as e:
        slug = None
        log_error_traceback(e)
    assert slug is not None
    yield

    # Get Manga chapters by slug
    print('Get manga chapters slug')
    try:
        response = readmanhwa_server.get_manga_chapters_slug(slug)
        chapter_slug = response[0]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)
    assert chapter_slug is not None
    yield
    