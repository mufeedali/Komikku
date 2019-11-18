import pytest


@pytest.fixture
def xkcd_server():
    from komikku.servers.xkcd import Xkcd

    return Xkcd()


def test_search_xkcd(xkcd_server):
    response = xkcd_server.search()
    print('Xkcd: search', response)
    assert response is not None


def test_get_manga_data_xkcd(xkcd_server):
    response = xkcd_server.get_manga_data(dict())
    print('Xkcd: get manga data', response)
    assert response is not None
