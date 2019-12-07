import pytest


@pytest.fixture
def hatigarmscans_server():
    from komikku.servers.hatigarmscans import Hatigarmscans

    return Hatigarmscans()


def test_search_hatigarmscans(hatigarmscans_server):
    response = hatigarmscans_server.search('tales of demons')
    print('Hatigarmscans: search', response)
    assert response is not None


def test_get_manga_data_hatigarmscans(hatigarmscans_server):
    response = hatigarmscans_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
    print('Hatigarmscans: get manga data', response)
    assert response is not None


def test_get_manga_chapter_data_hatigarmscans(hatigarmscans_server):
    response = hatigarmscans_server.get_manga_chapter_data('tales-of-demons-and-gods', '1', None)
    print('Hatigarmscans: get manga chapter data', response)
    assert response is not None


def test_get_manga_chapter_page_image_hatigarmscans(hatigarmscans_server):
    response = hatigarmscans_server.get_manga_chapter_page_image('tales-of-demons-and-gods', None, '1', dict(image='01.jpg'))
    print('Hatigarmscans: get manga chapter page image', response)
    assert response is not None
