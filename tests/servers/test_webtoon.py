import pytest


@pytest.fixture
def webtoon_server():
    from komikku.servers.webtoon import Webtoon

    return Webtoon()


def test_search_webtoon(webtoon_server):
    response = webtoon_server.search('caster')
    print('Webtoon: search', response)
    assert response is not None


def test_get_manga_data_webtoon(webtoon_server):
    response = webtoon_server.get_manga_data(dict(url='/episodeList?titleNo=1461'))
    print('Webtoon: get manga data', response)
    assert response is not None
