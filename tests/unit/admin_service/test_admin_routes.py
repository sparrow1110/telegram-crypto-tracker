import pytest
from unittest.mock import patch
from admin_service.app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_admin():
    with patch('admin_service.app.admin') as mock:
        yield mock


def test_is_admin_success(client, mock_admin):
    mock_admin.is_admin.return_value = True

    response = client.get('/v1/admins/123/status')
    assert response.status_code == 200
    assert response.json == {
        "data": {"is_admin": True}
    }
    mock_admin.is_admin.assert_called_once_with(123)


def test_is_admin_not_admin(client, mock_admin):
    mock_admin.is_admin.return_value = False

    response = client.get('/v1/admins/456/status')
    assert response.status_code == 200
    assert response.json == {
        "data": {"is_admin": False}
    }


def test_get_stats_success(client, mock_admin):
    test_stats = "📊 *Статистика бота*"
    mock_admin.get_bot_stats.return_value = test_stats

    response = client.get('/v1/stats')
    assert response.status_code == 200
    assert response.json == {
        "data": {"stats": test_stats}
    }


def test_get_popular_cryptos(client, mock_admin):
    test_data = "🔝 *Популярные криптовалюты*"
    mock_admin.get_popular_cryptos.return_value = test_data

    response = client.get('/v1/stats/popular-cryptos')
    assert response.status_code == 200
    assert response.json == {
        "data": {"popular": test_data}
    }


def test_block_user_success(client, mock_admin):
    mock_admin.block_user.return_value = True

    response = client.post('/v1/users/123/block')
    assert response.status_code == 200
    assert response.json == {
        "data": {
            "user_id": 123,
            "is_blocked": True,
            "action": "admin_blocked"
        }
    }


def test_block_user_not_found(client, mock_admin):
    mock_admin.block_user.return_value = False

    response = client.post('/v1/users/999/block')
    assert response.status_code == 404
    assert "errors" in response.json


def test_unblock_user_success(client, mock_admin):
    mock_admin.unblock_user.return_value = True

    response = client.post('/v1/users/123/unblock')
    assert response.status_code == 200
    assert response.json == {
        "data": {
            "user_id": 123,
            "is_blocked": False,
            "action": "admin_unblocked"
        }
    }


def test_not_found_handler(client):
    response = client.get('/nonexistent-route')
    assert response.status_code == 404
    assert "errors" in response.json
