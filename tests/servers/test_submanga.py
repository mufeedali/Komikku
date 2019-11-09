import pytest


@pytest.fixture
def submanga_server():
    from komikku.servers.submanga import Submanga

    return Submanga()


def test_search_submanga(submanga_server):
    response = submanga_server.search('tales of demons')
    print('Submanga: search', response)
    assert response is not None


def test_get_manga_data_submanga(submanga_server):
    response = submanga_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
    print('Submanga: get manga data', response)
    assert response is not None
