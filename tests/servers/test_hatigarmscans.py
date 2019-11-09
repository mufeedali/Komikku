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
