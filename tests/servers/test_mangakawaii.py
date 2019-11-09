import pytest


@pytest.fixture
def mangakawaii_server():
    from komikku.servers.mangakawaii import Mangakawaii

    return Mangakawaii()


def test_search_mangakawaii(mangakawaii_server):
    response = mangakawaii_server.search('tales of demons')
    print('Mangakawaii: search', response)
    assert response is not None


def test_get_manga_data_mangakawaii(mangakawaii_server):
    response = mangakawaii_server.get_manga_data(dict(slug='yaoshenji'))
    print('Mangakawaii: get manga data', response)
    assert response is not None
