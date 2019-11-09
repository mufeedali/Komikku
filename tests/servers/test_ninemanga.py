import pytest


@pytest.fixture
def ninemanga_server():
    from komikku.servers.ninemanga import Ninemanga

    return Ninemanga()


def test_search_ninemanga(ninemanga_server):
    response = ninemanga_server.search('tales of demons')
    print('Ninemanga: search', response)
    assert response is not None


def test_get_manga_data_ninemanga(ninemanga_server):
    response = ninemanga_server.get_manga_data(dict(slug='Tales of Demons and Gods'))
    print('Ninemanga: get manga data', response)
    assert response is not None
