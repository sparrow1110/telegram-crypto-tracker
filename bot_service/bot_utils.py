import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from aiogram import types
from aiogram.utils.markdown import escape_md

logger = logging.getLogger(__name__)


@lru_cache(maxsize=10)
def create_admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('📣 Рассылка сообщений'),
        types.KeyboardButton('📊 Статистика бота'),
        types.KeyboardButton('🚫 Заблокировать пользователя'),
        types.KeyboardButton('✅ Разблокировать пользователя'),
        types.KeyboardButton('🔝 Популярные криптовалюты'),
        types.KeyboardButton('🔙 Выход из админ-панели'),
    ]
    keyboard.add(*buttons)
    return keyboard


@lru_cache(maxsize=10)
def create_main_keyboard(user_id=None):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('💰 Все криптовалюты'),
        types.KeyboardButton('🔝 Топ-5 криптовалют'),
        types.KeyboardButton('🔍 Поиск криптовалюты'),
        types.KeyboardButton('⭐ Избранное'),
        types.KeyboardButton('❓ Помощь'),
    ]
    if user_id and str(user_id) in os.getenv('ADMIN_IDS', '').split(','):
        buttons.append(types.KeyboardButton('👨‍💻 Админ панель'))
    keyboard.add(*buttons)
    return keyboard


@lru_cache(maxsize=10)
def create_popular_coins_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('Bitcoin (BTC)'),
        types.KeyboardButton('Ethereum (ETH)'),
        types.KeyboardButton('Tether (USDT)'),
        types.KeyboardButton('Binance Coin (BNB)'),
        types.KeyboardButton('Solana (SOL)'),
        types.KeyboardButton('Ripple (XRP)'),
        types.KeyboardButton('Cardano (ADA)'),
        types.KeyboardButton('Dogecoin (DOGE)'),
        types.KeyboardButton('🔙 Завершить поиск'),
    ]
    keyboard.add(*buttons)
    return keyboard


@lru_cache(maxsize=10)
def create_search_control_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🔍 Продолжить поиск'),
        types.KeyboardButton('🔙 Завершить поиск'),
    ]
    keyboard.add(*buttons)
    return keyboard


def create_pagination_keyboard(current_page: int, total_pages: int):
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    buttons = []
    if current_page > 1:
        buttons.append(types.InlineKeyboardButton("◀️", callback_data=f"page_{current_page - 1}"))

    start_page = max(1, current_page - 2)
    end_page = min(total_pages, start_page + 4)

    for page in range(start_page, end_page + 1):
        text = f"•{page}•" if page == current_page else str(page)
        buttons.append(types.InlineKeyboardButton(text, callback_data=f"page_{page}"))

    if current_page < total_pages:
        buttons.append(types.InlineKeyboardButton("▶️", callback_data=f"page_{current_page + 1}"))

    keyboard.add(*buttons)
    return keyboard


def print_coins(data, display_coins):
    result = ""
    for symbol in display_coins:
        if symbol in data:
            values = data[symbol]
            coin_name = values.get("name", symbol)
            result += f"*{escape_md(symbol)}* ({escape_md(coin_name)})\n"
            price = values.get("price_usd", 0)
            result += f"💵 ${price:,.4f}\n"

            change_1h = values.get("percent_change_1h", 0)
            emoji_1h = "⬆️+" if change_1h >= 0 else "⬇️"
            result += f"1ч: {emoji_1h}{change_1h:.2f}%  "

            change_24h = values.get("percent_change_24h", 0)
            emoji_24h = "⬆️+" if change_24h >= 0 else "⬇️"
            result += f"24ч: {emoji_24h}{change_24h:.2f}%  "

            change_7d = values.get("percent_change_7d", 0)
            emoji_7d = "⬆️+" if change_7d >= 0 else "⬇️"
            result += f"7д: {emoji_7d}{change_7d:.2f}%\n\n"
        else:
            result += f"*{escape_md(symbol)}* - нет данных\n\n"
    return result


def format_crypto_message(data, limit=10):
    if not data or "last_updated" not in data:
        return "Данные о ценах недоступны. Попробуйте позже."

    utc_time = datetime.strptime(data['last_updated'], "%Y-%m-%d %H:%M:%S")
    local_time = utc_time + timedelta(hours=3)
    local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")

    message = f"💰 *Актуальные цены криптовалют* 💰\n_(обновлено: {escape_md(local_time_str)})_\n\n"
    crypto_keys = [key for key in data.keys() if key != "last_updated"]

    try:
        sorted_coins = sorted(crypto_keys, key=lambda x: data[x].get("rank", 999))
    except Exception as e:
        logger.error(f"Error sorting coins: {e}")
        sorted_coins = crypto_keys

    coins_to_display = sorted_coins[:limit]
    message += print_coins(data, coins_to_display)
    return message


def get_coin_info_message(data, symbol):
    if not data or "last_updated" not in data:
        return "Данные о ценах недоступны. Попробуйте позже."

    symbol = symbol.upper()
    if symbol not in data:
        similar_coins = [coin for coin in data.keys() if coin.upper().startswith(symbol[0]) and coin != "last_updated"]
        if not similar_coins:
            return f"Криптовалюта {escape_md(symbol)} не найдена. Попробуйте другой символ."
        else:
            suggestions = ", ".join(similar_coins[:5])
            return f"Криптовалюта {escape_md(symbol)} не найдена. Возможно, вы имели в виду: {escape_md(suggestions)}?"

    values = data[symbol]
    coin_name = values.get("name", symbol)
    utc_time = datetime.strptime(data['last_updated'], "%Y-%m-%d %H:%M:%S")
    local_time = utc_time + timedelta(hours=3)
    local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"💰 *{escape_md(symbol)}* ({escape_md(coin_name)})\n"
    message += f"_(данные на: {escape_md(local_time_str)})_\n\n"

    price = values.get("price_usd", 0)
    message += f"*Цена:* ${price:,.6f}\n\n"
    message += "*Изменения:*\n"

    change_1h = values.get("percent_change_1h", 0)
    emoji_1h = "⬆️+" if change_1h >= 0 else "⬇️"
    message += f"За 1 час: {emoji_1h}{change_1h:.2f}%\n"

    change_24h = values.get("percent_change_24h", 0)
    emoji_24h = "⬆️+" if change_24h >= 0 else "⬇️"
    message += f"За 24 часа: {emoji_24h}{change_24h:.2f}%\n"

    change_7d = values.get("percent_change_7d", 0)
    emoji_7d = "⬆️+" if change_7d >= 0 else "⬇️"
    message += f"За 7 дней: {emoji_7d}{change_7d:.2f}%\n\n"

    market_cap = values.get("market_cap_usd", 0)
    message += f"*Рыночная капитализация:* ${market_cap:,.2f}\n"

    rank = values.get("rank", "N/A")
    message += f"*Ранг:* #{rank}\n"

    return message
