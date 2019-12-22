import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mangaeden_server():
    from komikku.servers.mangaeden import Mangaeden

    return Mangaeden()


def test_search_mangaeden(mangaeden_server):
    try:
        response = mangaeden_server.search('tales of demons')
        print('Mangaeden: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_mangaeden(mangaeden_server):
    try:
        response = mangaeden_server.get_most_populars()
        print('Mangaeden: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_mangaeden(mangaeden_server):
    try:
        response = mangaeden_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
        print('Mangaeden: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_mangaeden(mangaeden_server):
    try:
        response = mangaeden_server.get_manga_chapter_data('tales-of-demons-and-gods', '1', None)
        print('Mangaeden: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_mangaeden(mangaeden_server):
    try:
        response = mangaeden_server.get_manga_chapter_page_image(None, None, None, dict(image='https://cdn.mangaeden.com/mangasimg/bb/bb4cdbf88e7391cfebe710b0612212ab011a2b17cf86338e39aa6b8a.jpg'))
        print('Mangaeden: get manga chapter page image')
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None
