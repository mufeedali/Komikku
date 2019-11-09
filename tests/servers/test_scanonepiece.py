import pytest


@pytest.fixture
def scanonepiece_server():
    from komikku.servers.scanonepiece import Scanonepiece

    return Scanonepiece()


def test_search_scanonepiece(scanonepiece_server):
    response = scanonepiece_server.search('tales of demons')
    print('Scanonepiece: search', response)
    assert response is not None


def test_get_manga_data_scanonepiece(scanonepiece_server):
    response = scanonepiece_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
    print('Scanonepiece: get manga data', response)
    assert response is not None
