import pytest
import os
from admin_service.app import app
from dotenv import load_dotenv
from unittest.mock import patch, Mock

# Загрузка .env для тестов
load_dotenv()


# Фикстура для Flask test client
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# Фикстура для mock requests.get
@pytest.fixture
def mock_get():
    with patch('admin_service.admin_panel.requests.get') as mock:
        yield mock


# Фикстура для mock requests.post
@pytest.fixture
def mock_post():
    with patch('admin_service.admin_panel.requests.post') as mock:
        yield mock


# Тест для /v1/admins/<user_id>/status с правильным токеном
def test_is_admin_success(client, mock_get):
    # Настройка mock для проверки админа
    mock_response = Mock()
    mock_response.json.return_value = {'data': {'is_admin': True}}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    headers = {'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}'}
    response = client.get('/v1/admins/123/status', headers=headers)
    assert response.status_code == 200
    assert 'data' in response.json
    assert response.json['data']['is_admin'] is True


# Тест для /v1/admins/<user_id>/status с неверным токеном
def test_is_admin_invalid_token(client):
    headers = {'Authorization': 'Bearer invalid-token'}
    response = client.get('/v1/admins/123/status', headers=headers)
    assert response.status_code == 401
    assert 'errors' in response.json


# Тест для /v1/admins/<user_id>/status без токена
def test_is_admin_no_token(client):
    response = client.get('/v1/admins/123/status')
    assert response.status_code == 401
    assert 'errors' in response.json


# Тест для /v1/stats с правами админа
def test_get_stats_success(client, mock_get):
    # Настройка mock для проверки админа
    mock_response_admin = Mock()
    mock_response_admin.json.return_value = {'data': {'is_admin': True}}
    mock_response_admin.raise_for_status.return_value = None

    # Настройка mock для получения статистики
    mock_response_stats = Mock()
    mock_response_stats.json.return_value = {
        'data': {
            'user_count': 100,
            'active_users_24h': 50,
            'active_users_7d': 80,
            'blocked_count': 5,
            'favorites_count': 200,
            'popular_commands': [('/start', 50), ('/help', 30)],
        }
    }
    mock_response_stats.raise_for_status.return_value = None
    mock_get.side_effect = [mock_response_admin, mock_response_stats]

    headers = {
        'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
        'Content-Type': 'application/json',
    }
    response = client.get('/v1/stats', headers=headers, json={'requester_id': 123})
    assert response.status_code == 200
    assert 'data' in response.json
    assert 'stats' in response.json['data']


# Тест для /v1/users/<user_id>/block с правами админа
def test_block_user_success(client, mock_get, mock_post):
    # Настройка mock для проверки админа
    mock_response_admin = Mock()
    mock_response_admin.json.return_value = {'data': {'is_admin': True}}
    mock_response_admin.raise_for_status.return_value = None
    mock_get.return_value = mock_response_admin

    # Настройка mock для блокировки пользователя
    mock_response_block = Mock()
    mock_response_block.json.return_value = {'data': {'is_blocked': True}}
    mock_response_block.raise_for_status.return_value = None
    mock_post.return_value = mock_response_block

    headers = {
        'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
        'Content-Type': 'application/json',
    }
    response = client.post('/v1/users/123/block', headers=headers, json={'requester_id': 123})
    assert response.status_code == 200
    assert 'data' in response.json
    assert response.json['data']['is_blocked'] is True


# Тест для несуществующего маршрута
def test_not_found_handler(client):
    response = client.get('/nonexistent-route')
    assert response.status_code == 404
    assert 'errors' in response.json
