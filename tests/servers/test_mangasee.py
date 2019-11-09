import pytest


@pytest.fixture
def mangasee_server():
    from komikku.servers.mangasee import Mangasee

    return Mangasee()


def test_search_mangasee(mangasee_server):
    response = mangasee_server.search('tales of demons')
    print('Mangasee: search', response)
    assert response is not None


def test_get_manga_data_mangasee(mangasee_server):
    response = mangasee_server.get_manga_data(dict(slug='Tales-Of-Demons-And-Gods'))
    print('Mangasee: get manga data', response)
    assert response is not None
