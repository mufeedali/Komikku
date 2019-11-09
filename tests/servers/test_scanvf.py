import pytest


@pytest.fixture
def scanvf_server():
    from komikku.servers.scanvf import Scanvf

    return Scanvf()


def test_search_scanvf(scanvf_server):
    response = scanvf_server.search('tales of demons')
    print('Scanvf: search', response)
    assert response is not None


def test_get_manga_data_scanvf(scanvf_server):
    response = scanvf_server.get_manga_data(dict(slug='mangas-tales-of-demons-and-gods'))
    print('Scanvf: get manga data', response)
    assert response is not None
