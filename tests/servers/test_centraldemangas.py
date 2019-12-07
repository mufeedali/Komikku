import pytest


@pytest.fixture
def centraldemangas_server():
    from komikku.servers.centraldemangas import Centraldemangas

    return Centraldemangas()


def test_search_centraldemangas(centraldemangas_server):
    response = centraldemangas_server.search('tales of demons and gods')
    print('Central de mangas: search', response)
    assert response is not None


def test_get_manga_data_centraldemangas(centraldemangas_server):
    response = centraldemangas_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
    print('Central de mangas: get manga data', response)
    assert response is not None
