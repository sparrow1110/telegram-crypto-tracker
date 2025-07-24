import pytest
import os
from unittest.mock import AsyncMock, Mock, patch
from admin_service.admin_panel import AdminPanel
from datetime import datetime
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
@pytest.mark.asyncio
async def test_is_admin(admin_panel):
    os.environ['ADMIN_IDS'] = '123,456'
    assert await admin_panel.is_admin(123) is True
    assert await admin_panel.is_admin(456) is True
    assert await admin_panel.is_admin(789) is False


# Тест для метода get_bot_stats с mock-запросом
@pytest.mark.asyncio
async def test_get_bot_stats(admin_panel):
    with patch('httpx.AsyncClient.get', new=AsyncMock()) as mock_get:
        mock_response = Mock(
            status_code=200,
            json=lambda: {
                'data': {
                    'user_count': 100,
                    'active_users_24h': 50,
                    'active_users_7d': 80,
                    'blocked_count': 5,
                    'favorites_count': 200,
                    'popular_commands': [('/start', 50), ('/help', 30)],
                }
            },
            raise_for_status=lambda: None,
        )
        mock_get.return_value = mock_response
        stats = await admin_panel.get_bot_stats(123)
        assert '📊 *Статистика бота*' in stats
        assert 'Всего пользователей: 100' in stats
        assert 'Активных за 24 часа: 50' in stats
        assert 'Активных за 7 дней: 80' in stats
        assert 'Заблокированных: 5' in stats
        assert 'Всего добавлено в избранное: 200' in stats
        assert '• /start: 50 раз' in stats
        assert '• /help: 30 раз' in stats


# Тест для метода get_popular_cryptos с mock-запросом
@pytest.mark.asyncio
async def test_get_popular_cryptos(admin_panel):
    with patch('httpx.AsyncClient.get', new=AsyncMock()) as mock_get:
        mock_response = Mock(
            status_code=200,
            json=lambda: {'data': {'cryptos': [('BTC', 100), ('ETH', 50)]}},
            raise_for_status=lambda: None,
        )
        mock_get.return_value = mock_response
        result = await admin_panel.get_popular_cryptos(123)
        assert '🔝 *Популярные криптовалюты*' in result
        assert '1. *BTC* - 100 пользователей' in result
        assert '2. *ETH* - 50 пользователей' in result
        assert f"🕒 *Актуально на:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" in result


# Тест для метода block_user с mock-запросом
@pytest.mark.asyncio
async def test_block_user(admin_panel):
    with patch('httpx.AsyncClient.post', new=AsyncMock()) as mock_post:
        mock_response = Mock(
            status_code=200, json=lambda: {'data': {'is_blocked': True}}, raise_for_status=lambda: None
        )
        mock_post.return_value = mock_response
        result = await admin_panel.block_user(123, 456)
        assert result is True


# Тест для метода unblock_user с mock-запросом
@pytest.mark.asyncio
async def test_unblock_user(admin_panel):
    with patch('httpx.AsyncClient.post', new=AsyncMock()) as mock_post:
        mock_response = Mock(
            status_code=200, json=lambda: {'data': {'is_blocked': False}}, raise_for_status=lambda: None
        )
        mock_post.return_value = mock_response
        result = await admin_panel.unblock_user(123, 456)
        assert result is True
