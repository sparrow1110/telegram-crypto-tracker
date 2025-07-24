import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from bot_service.app import send_welcome, send_help


@pytest.fixture
def mock_message():
    message = MagicMock(spec=types.Message)
    message.from_user = types.User(id=123, is_bot=False, username='testuser', first_name='Test', last_name='User')
    message.chat = types.Chat(id=123, type='private')
    message.text = '/start'
    message.answer = AsyncMock()  # Мок для метода answer
    return message


@pytest.mark.asyncio
async def test_send_welcome(mock_message):
    """Test /start command handler"""
    with (
        patch('bot_service.app.register_user', new_callable=AsyncMock) as mock_register,
        patch('bot_service.app.log_command', new_callable=AsyncMock) as mock_log,
    ):
        # Вызываем обработчик напрямую
        await send_welcome(mock_message)

        # Проверяем вызовы
        mock_register.assert_awaited_once_with(mock_message)
        mock_log.assert_awaited_once_with(mock_message.from_user.id, '/start')
        mock_message.answer.assert_awaited_once()

        # Проверяем аргументы ответа
        args, kwargs = mock_message.answer.call_args
        assert 'Привет! Я бот для отслеживания цен криптовалют' in args[0]
        assert 'parse_mode' in kwargs
        assert kwargs['parse_mode'] == 'Markdown'


@pytest.mark.asyncio
async def test_send_help(mock_message):
    with (
        patch('bot_service.app.register_user', new_callable=AsyncMock) as mock_register,
        patch('bot_service.app.log_command', new_callable=AsyncMock) as mock_log,
    ):
        mock_message.text = '/help'

        # Вызываем обработчик напрямую
        await send_help(mock_message)

        # Проверяем вызовы
        mock_register.assert_awaited_once_with(mock_message)
        mock_log.assert_awaited_once_with(mock_message.from_user.id, '/help')
        mock_message.answer.assert_awaited_once()

        # Проверяем аргументы ответа
        args, kwargs = mock_message.answer.call_args
        assert 'Помощь по использованию бота' in args[0]
        assert 'parse_mode' in kwargs
        assert kwargs['parse_mode'] == 'Markdown'
