import pytest


@pytest.fixture
def scantrad_server():
    from komikku.servers.scantrad import Scantrad

    return Scantrad()


def test_search_scantrad(scantrad_server):
    response = scantrad_server.search('black clover')
    print('Scantrad: search', response)
    assert response is not None


def test_get_manga_data_scantrad(scantrad_server):
    response = scantrad_server.get_manga_data(dict(slug='black-clover'))
    print('Scantrad: get manga data', response)
    assert response is not None
