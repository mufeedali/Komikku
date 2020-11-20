import logging
import pytest
from pytest_steps import test_steps

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def kireicake_server():
    from komikku.servers.jaiminisbox import Kireicake

    return Kireicake()


@pytest.fixture
def lupiteam_server():
    from komikku.servers.jaiminisbox import Lupiteam

    return Lupiteam()


@pytest.fixture
def tuttoanimemanga_server():
    from komikku.servers.jaiminisbox import Tuttoanimemanga

    return Tuttoanimemanga()


@test_steps('get_most_popular', 'search', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_kireicake(kireicake_server):
    # Get most popular
    print('Get most popular')
    try:
        response = kireicake_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Search
    print('Search')
    try:
        response = kireicake_server.search('Dai Dark')
        slug = response[0]['slug']
    except Exception as e:
        slug = None
        log_error_traceback(e)

    assert slug is not None
    yield

    # Get manga data
    print('Get manga data')
    try:
        response = kireicake_server.get_manga_data(dict(slug=slug))
        chapter_slug = response['chapters'][0]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print("Get chapter data")
    try:
        response = kireicake_server.get_manga_chapter_data(slug, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = kireicake_server.get_manga_chapter_page_image(None, None, None, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield


@test_steps('get_most_popular', 'search', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_lupiteam(lupiteam_server):
    # Get most popular
    print('Get most popular')
    try:
        response = lupiteam_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Search
    print('Search')
    try:
        response = lupiteam_server.search('one piece')
        slug = response[0]['slug']
    except Exception as e:
        slug = None
        log_error_traceback(e)

    assert slug is not None
    yield

    # Get manga data
    print('Get manga data')
    try:
        response = lupiteam_server.get_manga_data(dict(slug=slug))
        chapter_slug = response['chapters'][1]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print("Get chapter data")
    try:
        response = lupiteam_server.get_manga_chapter_data(slug, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = lupiteam_server.get_manga_chapter_page_image(None, None, None, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield


@test_steps('get_most_popular', 'search', 'get_manga_data', 'get_chapter_data', 'get_page_image')
def test_tuttoanimemanga(tuttoanimemanga_server):
    # Get most popular
    print('Get most popular')
    try:
        response = tuttoanimemanga_server.get_most_populars()
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield

    # Search
    print('Search')
    try:
        response = tuttoanimemanga_server.search('One piece')
        slug = response[0]['slug']
    except Exception as e:
        slug = None
        log_error_traceback(e)

    assert slug is not None
    yield

    # Get manga data
    print('Get manga data')
    try:
        response = tuttoanimemanga_server.get_manga_data(dict(slug=slug))
        chapter_slug = response['chapters'][0]['slug']
    except Exception as e:
        chapter_slug = None
        log_error_traceback(e)

    assert chapter_slug is not None
    yield

    # Get chapter data
    print("Get chapter data")
    try:
        response = tuttoanimemanga_server.get_manga_chapter_data(slug, None, chapter_slug, None)
        page = response['pages'][0]
    except Exception as e:
        page = None
        log_error_traceback(e)

    assert page is not None
    yield

    # Get page image
    print('Get page image')
    try:
        response = tuttoanimemanga_server.get_manga_chapter_page_image(None, None, None, page)
    except Exception as e:
        response = None
        log_error_traceback(e)

    assert response is not None
    yield
