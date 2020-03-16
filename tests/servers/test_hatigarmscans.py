import logging
import pytest

from komikku.utils import log_error_traceback

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def hatigarmscans_server():
    from komikku.servers.genkan import Hatigarmscans

    return Hatigarmscans()


def test_search_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.search('tales of demons')
        print('Hatigarm Scans: search', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_most_populars_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.get_most_populars()
        print('Hatigarm Scans: get most populars', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_data_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.get_manga_data(dict(slug='574092-tales-of-demons-and-gods'))
        print('Hatigarm Scans: get manga data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_data_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.get_manga_chapter_data('574092-tales-of-demons-and-gods', None, '1/265', None)
        print('Hatigarm Scans: get manga chapter data', response)
    except Exception as e:
        response = None
        log_error_traceback(e)
    assert response is not None


def test_get_manga_chapter_page_image_hatigarmscans(hatigarmscans_server):
    try:
        response = hatigarmscans_server.get_manga_chapter_page_image(None, None, None, dict(image='/storage/comics/F479B21DC6887FCD280C10B83A758AD552210E34CDE508A5/volumes/DE11A9FE8D9FCE29E100B7EAE43F9749B5197C74C612E908/chapters/C5E596CAF80D435B27D05A7DB4173BF436F8DBE8F430EA5C/00_1_1.jpg'))
        print('Hatigarm Scans: get manga chapter page image')
    except Exception as e:
        response = (None, None)
        log_error_traceback(e)
    assert response is not (None, None)
