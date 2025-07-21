import pytest
import os
from unittest.mock import Mock, patch
from admin_service.admin_panel import AdminPanel
from dotenv import load_dotenv

# Загружаем .env для тестов
load_dotenv()


# Фикстура для AdminPanel с mock-токеном
@pytest.fixture
def admin_panel():
    return AdminPanel(
        user_service_url='http://user-service',
        crypto_service_url='http://crypto-service',
        api_token=os.getenv('API_TOKEN', 'your-secret-api-token'),
    )


# Тест для метода is_admin
def test_is_admin(admin_panel):
    os.environ['ADMIN_IDS'] = '123,456'
    assert admin_panel.is_admin(123) is True
    assert admin_panel.is_admin(456) is True
    assert admin_panel.is_admin(789) is False


# Тест для метода get_bot_stats с mock-запросом
@patch('admin_service.admin_panel.requests.get')
def test_get_bot_stats(mock_get, admin_panel):
    mock_response = Mock()
    mock_response.json.return_value = {
        'data': {
            'user_count': 100,
            'active_users_24h': 50,
            'active_users_7d': 80,
            'blocked_count': 5,
            'favorites_count': 200,
            'popular_commands': [('/start', 50), ('/help', 30)],
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    stats = admin_panel.get_bot_stats(123)
    assert '📊 *Статистика бота*' in stats
    assert 'Всего пользователей: 100' in stats


# Тест для метода block_user с mock-запросом
@patch('admin_service.admin_panel.requests.post')
def test_block_user(mock_post, admin_panel):
    mock_response = Mock()
    mock_response.json.return_value = {'data': {'is_blocked': True}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = admin_panel.block_user(123, 456)
    assert result is True


# Тест для метода unblock_user с mock-запросом
@patch('admin_service.admin_panel.requests.post')
def test_unblock_user(mock_post, admin_panel):
    mock_response = Mock()
    mock_response.json.return_value = {'data': {'is_blocked': False}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = admin_panel.unblock_user(123, 456)
    assert result is True
