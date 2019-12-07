import pytest


@pytest.fixture
def dbmultiverse_server():
    from komikku.servers.dbmultiverse import Dbmultiverse

    return Dbmultiverse()


def test_search_dbmultiverse(dbmultiverse_server):
    response = dbmultiverse_server.search()
    print('DB Multiverse: search', response)
    assert response is not None


def test_get_manga_data_dbmultiverse(dbmultiverse_server):
    response = dbmultiverse_server.get_manga_data(dict())
    print('DB Multiverse: get manga data', response)
    assert response is not None
