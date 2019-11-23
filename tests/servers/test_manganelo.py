import pytest


@pytest.fixture
def manganelo_server():
    from komikku.servers.manganelo import Manganelo

    return Manganelo()


def test_search_manganelo(manganelo_server):
    response = manganelo_server.search('tales of demons')
    print('Manganelo: search', response)
    assert response is not None


def test_get_manga_data_manganelo(manganelo_server):
    response = manganelo_server.get_manga_data(dict(slug='hyer5231574354229'))
    print('Manganelo: get manga data', response)
    assert response is not None
