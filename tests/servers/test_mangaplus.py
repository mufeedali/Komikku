import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mangaplus_server():
    from komikku.servers.mangaplus import Mangaplus

    return Mangaplus()


def test_search_mangaplus(mangaplus_server):
    try:
        response = mangaplus_server.search('naruto')
        print('MANGA Plus: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_mangaplus(mangaplus_server):
    try:
        response = mangaplus_server.get_most_populars()
        print('MANGA Plus: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_mangaplus(mangaplus_server):
    try:
        response = mangaplus_server.get_manga_data(dict(slug='100018'))
        print('MANGA Plus: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_mangaplus(mangaplus_server):
    try:
        response = mangaplus_server.get_manga_chapter_data(None, '1000397', None)
        print('MANGA Plus: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_mangaplus(mangaplus_server):
    try:
        response = mangaplus_server.get_manga_chapter_page_image(
            None, None, None,
            dict(
                image='https://mangaplus.shueisha.co.jp/drm/title/100018/chapter/1000397/manga_page/high/75874.jpg?key=04643a51ae8fc8fc46227706b48c9c2d&duration=86400',
                encryption_key='231f42f83e5aa2a2be49a14e6accf71cb52b576b21e75c264c55e522971c917faec881b9460a7c15b8f85ced7c66f763832ec5be563fb73a09726839bd9f8ef9'
            ))
        print('MANGA Plus: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
