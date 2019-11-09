import pytest


@pytest.fixture
def mangarock_server():
    from komikku.servers.mangarock import Mangarock

    return Mangarock()


def test_search_mangarock(mangarock_server):
    response = mangarock_server.search('tales of demons')
    print('Mangarock: search', response)
    assert response is not None


def test_get_manga_data_mangarock(mangarock_server):
    response = mangarock_server.get_manga_data(dict(slug='mrs-serie-240647'))
    print('Mangarock: get manga data', response)
    assert response is not None
