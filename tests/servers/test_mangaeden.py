import pytest


@pytest.fixture
def mangaeden_server():
    from komikku.servers.mangaeden import Mangaeden

    return Mangaeden()


def test_search_mangaeden(mangaeden_server):
    response = mangaeden_server.search('tales of demons')
    print('Mangaeden: search', response)
    assert response is not None


def test_get_manga_data_mangaeden(mangaeden_server):
    response = mangaeden_server.get_manga_data(dict(slug='tales-of-demons-and-gods'))
    print('Mangaeden: get manga data', response)
    assert response is not None
