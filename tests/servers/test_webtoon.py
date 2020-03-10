import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def webtoon_server():
    from komikku.servers.webtoon import Webtoon

    return Webtoon()


def test_search_webtoon(webtoon_server):
    try:
        response = webtoon_server.search('caster')
        print('Webtoon: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_webtoon(webtoon_server):
    try:
        response = webtoon_server.get_most_populars()
        print('Webtoon: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_webtoon(webtoon_server):
    try:
        response = webtoon_server.get_manga_data(dict(url='/episodeList?titleNo=1461'))
        print('Webtoon: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_webtoon(webtoon_server):
    try:
        response = webtoon_server.get_manga_chapter_data(None, None, None, '/en/action/caster/chapter-1/viewer?title_no=1461&episode_no=1')
        print('Webtoon: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_webtoon(webtoon_server):
    try:
        response = webtoon_server.get_manga_chapter_page_image(None, None, None, dict(image='https://webtoon-phinf.pstatic.net/20181004_75/1538611782712ED47V_JPEG/1538611782675146117.jpg?type=q90'))
        print('Webtoon: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
