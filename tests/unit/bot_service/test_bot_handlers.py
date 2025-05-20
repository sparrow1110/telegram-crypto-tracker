import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telebot import types
from bot_service.app import bot


@pytest.fixture
def mock_message():
    message = MagicMock()
    message.from_user = types.User(
        id=123,
        is_bot=False,
        username='testuser',
        first_name='Test',
        last_name='User'
    )
    message.chat = types.Chat(id=123, type='private')
    message.text = '/start'
    return message


@pytest.mark.asyncio
async def test_send_welcome(mock_message):
    """Test /start command handler"""
    # Создаем асинхронные моки
    mock_register = AsyncMock()
    mock_log = AsyncMock()
    mock_send = AsyncMock()

    with (
        patch('bot_service.app.register_user', new=mock_register),
        patch('bot_service.app.log_command', new=mock_log),
        patch('bot_service.app.bot.send_message', new=mock_send)
    ):
        # Имитируем вызов обработчика
        handler = bot.message_handlers[0]['function']
        await handler(mock_message)

        # Проверяем вызовы
        mock_register.assert_awaited_once_with(mock_message)
        mock_log.assert_awaited_once_with(mock_message.from_user.id, '/start')
        mock_send.assert_awaited_once()

        # Проверяем аргументы send_message
        args, kwargs = mock_send.call_args
        assert 'Привет! Я бот для отслеживания цен криптовалют' in args[1]


@pytest.mark.asyncio
async def test_send_help(mock_message):
    """Test /help command handler"""
    mock_register = AsyncMock()
    mock_log = AsyncMock()
    mock_send = AsyncMock()

    with (
        patch('bot_service.app.register_user', new=mock_register),
        patch('bot_service.app.log_command', new=mock_log),
        patch('bot_service.app.bot.send_message', new=mock_send)
    ):
        mock_message.text = '/help'
        handler = bot.message_handlers[1]['function']
        await handler(mock_message)

        mock_register.assert_awaited_once_with(mock_message)
        mock_log.assert_awaited_once_with(mock_message.from_user.id, '/help')
        mock_send.assert_awaited_once()

        args, kwargs = mock_send.call_args
        assert 'Помощь по использованию бота' in args[1]
