import logging
import os
import asyncio
from datetime import datetime, timedelta
from functools import wraps, lru_cache
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.markdown import escape_md

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# URL сервисов
USER_SERVICE_URL = f"{os.getenv('USER_SERVICE_URL', 'http://user_service:5001')}/v1"
ADMIN_SERVICE_URL = f"{os.getenv('ADMIN_SERVICE_URL', 'http://admin_service:5002')}/v1"
CRYPTO_SERVICE_URL = f"{os.getenv('CRYPTO_SERVICE_URL', 'http://crypto_service:5003')}/v1"


# Состояния FSM
class BotStates(StatesGroup):
    SEARCHING_CRYPTO = State()
    BROADCAST_MODE = State()
    BLOCK_MODE = State()
    UNBLOCK_MODE = State()


# Декоратор проверки блокировки
def check_user_blocked():
    def decorator(handler):
        @wraps(handler)
        async def wrapped(message: types.Message, *args, **kwargs):
            user_id = message.from_user.id
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/block-status") as response:
                        response.raise_for_status()
                        if (await response.json())['data'].get('is_blocked', False):
                            await message.answer("Вы заблокированы администратором.")
                            return
                        return await handler(message, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error checking block status: {e}")
                return await handler(message, *args, **kwargs)

        return wrapped

    return decorator


async def register_user(message: types.Message):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{USER_SERVICE_URL}/users",
                json={
                    'user_id': message.from_user.id,
                    'username': message.from_user.username,
                    'first_name': message.from_user.first_name,
                    'last_name': message.from_user.last_name,
                },
            )
        logger.info(f"User {message.from_user.id} registered")
    except Exception as e:
        logger.error(f"Error registering user: {e}")


async def log_command(user_id: int, command: str):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(f"{USER_SERVICE_URL}/command-logs", json={'user_id': user_id, 'command': command})
    except Exception as e:
        logger.error(f"Error logging command: {e}")


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
        types.KeyboardButton('🔙 Назад'),
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


async def broadcast_message(message_text: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{USER_SERVICE_URL}/users/unblocked") as response:
                response.raise_for_status()
                users = (await response.json())['data'].get('users', [])

        sent_count = 0
        failed_count = 0

        for user_id in users:
            try:
                await bot.send_message(user_id, message_text, parse_mode='Markdown')
                sent_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

        return sent_count, failed_count
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        return 0, 0


@dp.message_handler(commands=['start'])
@check_user_blocked()
async def send_welcome(message: types.Message):
    await register_user(message)
    await log_command(message.from_user.id, '/start')
    keyboard = create_main_keyboard(message.from_user.id)
    await message.answer(
        "👋 Привет! Я бот для отслеживания цен криптовалют.\n\n"
        "Используйте кнопки ниже для навигации или следующие команды:\n"
        "/prices - получить актуальные цены популярных криптовалют\n"
        "/favorites - показать ваши избранные криптовалюты\n"
        "/help - справка по всем командам",
        reply_markup=keyboard,
        parse_mode='Markdown',
    )


@dp.message_handler(commands=['help'])
@check_user_blocked()
async def send_help(message: types.Message):
    await register_user(message)
    await log_command(message.from_user.id, '/help')
    help_text = (
        "🤖 *Помощь по использованию бота:*\n\n"
        "*Основные команды:*\n"
        "💰 Все криптовалюты - показать список популярных криптовалют\n"
        "🔝 Топ-5 криптовалют - показать только топ-5 монет\n"
        "🔍 Поиск криптовалюты - найти конкретную монету\n"
        "⭐ Избранное - показать ваши избранные криптовалюты\n"
        "❓ Помощь - показать это сообщение\n\n"
        "*Дополнительно:*\n"
        "• Для навигации по страницам используйте кнопки пагинации\n"
        "• Бот обновляет информацию каждые 5 минут\n"
        "• Для поиска конкретной монеты выберите 'Поиск криптовалюты' и введите символ (например, BTC)"
    )
    await message.answer(help_text, parse_mode='Markdown')


@dp.message_handler(commands=['prices'])
@check_user_blocked()
async def send_prices(message: types.Message):
    await register_user(message)
    await log_command(message.from_user.id, '/prices')
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as response:
                response.raise_for_status()
                data = (await response.json())['data']
                formatted_message = format_crypto_message(data)
                crypto_keys = [key for key in data.keys() if key != "last_updated"]
                total_pages = (len(crypto_keys) // 10) + (1 if len(crypto_keys) % 10 > 0 else 0)
                pagination_keyboard = create_pagination_keyboard(1, total_pages)
                await message.answer(formatted_message, parse_mode='Markdown', reply_markup=pagination_keyboard)
    except Exception as e:
        logger.error(f"Error getting prices: {e}")
        await message.answer("Ошибка при получении данных о ценах. Попробуйте позже.")


@dp.message_handler(commands=['favorites'])
@check_user_blocked()
async def send_favorites(message: types.Message):
    await register_user(message)
    await log_command(message.from_user.id, '/favorites')
    user_id = message.from_user.id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos") as response:
                response.raise_for_status()
                favorites = (await response.json())['data'].get('favorites', [])
                if not favorites:
                    await message.answer(
                        "У вас пока нет избранных криптовалют. Чтобы добавить криптовалюту в ⭐ Избранное, "
                        "необходимо перейти в раздел 🔍 Поиск криптовалюты и выбрать нужную криптовалюту."
                    )
                    return
            async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as response:
                response.raise_for_status()
                crypto_data = (await response.json())['data']
                result = "⭐ *Ваши избранные криптовалюты* ⭐\n\n"
                result += print_coins(crypto_data, favorites)
                await message.answer(result, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        await message.answer("Ошибка при получении избранного. Попробуйте позже.")


@dp.message_handler(commands=['admin'])
@check_user_blocked()
async def admin_panel(message: types.Message):
    await register_user(message)
    user_id = message.from_user.id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ADMIN_SERVICE_URL}/admins/{user_id}/status") as response:
                response.raise_for_status()
                if not (await response.json())['data'].get('is_admin', False):
                    await message.answer("У вас нет доступа к админ-панели.")
                    return
        keyboard = create_admin_keyboard()
        await message.answer(
            "👨‍💻 *Админ-панель криптобота* 👨‍💻\n\nВыберите действие из меню ниже:",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        await message.answer("Произошла ошибка при проверке статуса админа. Попробуйте позже.")


@dp.message_handler(
    lambda message: message.text
    in [
        '💰 Все криптовалюты',
        '🔝 Топ-5 криптовалют',
        '🔍 Поиск криптовалюты',
        '❓ Помощь',
        '🔙 Назад',
        '⭐ Избранное',
        '👨‍💻 Админ панель',
    ]
)
@check_user_blocked()
async def handle_text_messages(message: types.Message, state: FSMContext):
    text = message.text
    if text == '💰 Все криптовалюты':
        await send_prices(message)
    elif text == '🔝 Топ-5 криптовалют':
        await register_user(message)
        await log_command(message.from_user.id, '/top5')
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as response:
                    response.raise_for_status()
                    data = (await response.json())['data']
                    formatted_message = format_crypto_message(data, limit=5)
                    await message.answer(formatted_message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error getting top5: {e}")
            await message.answer("Ошибка при получении данных. Попробуйте позже.")
    elif text == '🔍 Поиск криптовалюты':
        await register_user(message)
        await log_command(message.from_user.id, '/search')
        await state.set_state(BotStates.SEARCHING_CRYPTO)
        keyboard = create_popular_coins_keyboard()
        await message.answer(
            "Выберите криптовалюту из списка или введите её символ (например, BTC):", reply_markup=keyboard
        )
    elif text == '❓ Помощь':
        await send_help(message)
    elif text == '🔙 Назад':
        await register_user(message)
        await state.set_state(None)
        keyboard = create_main_keyboard(message.from_user.id)
        await message.answer("Выберите действие:", reply_markup=keyboard)
    elif text == '⭐ Избранное':
        await send_favorites(message)
    elif text == '👨‍💻 Админ панель':
        await admin_panel(message)


@dp.message_handler(state=BotStates.SEARCHING_CRYPTO)
@check_user_blocked()
async def process_search_crypto(message: types.Message, state: FSMContext):
    text = message.text
    if '(' in text and ')' in text:
        symbol = text.split('(')[1].split(')')[0]
    else:
        symbol = text
    await show_coin_info(message, symbol)
    await state.set_state(None)


async def show_coin_info(message: types.Message, symbol: str):
    await register_user(message)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as response:
                response.raise_for_status()
                crypto_data = (await response.json())['data']
                message_text = get_coin_info_message(crypto_data, symbol)
                if 'error' not in crypto_data:
                    async with session.get(
                        f"{USER_SERVICE_URL}/users/{message.from_user.id}/favorite-cryptos"
                    ) as fav_response:
                        fav_response.raise_for_status()
                        favorites = (await fav_response.json())['data'].get('favorites', [])
                        is_favorite = symbol.upper() in [fav.upper() for fav in favorites]
                        keyboard = types.InlineKeyboardMarkup()
                        keyboard.add(
                            types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}"),
                            types.InlineKeyboardButton(
                                "❌ Удалить из избранного" if is_favorite else "⭐ Добавить в избранное",
                                callback_data=f"unfav_{symbol}" if is_favorite else f"fav_{symbol}",
                            ),
                        )
                        await message.answer(message_text, parse_mode='Markdown', reply_markup=keyboard)
                else:
                    await message.answer(message_text)
    except Exception as e:
        logger.error(f"Error showing coin info: {e}")
        await message.answer("Ошибка при получении данных о криптовалюте. Попробуйте позже.")


@dp.message_handler(
    lambda message: message.text
    in [
        '📣 Рассылка сообщений',
        '🚫 Заблокировать пользователя',
        '✅ Разблокировать пользователя',
        '📊 Статистика бота',
        '🔝 Популярные криптовалюты',
        '🔙 Выход из админ-панели',
    ]
)
@check_user_blocked()
async def handle_admin_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await register_user(message)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ADMIN_SERVICE_URL}/admins/{user_id}/status") as response:
                response.raise_for_status()
                if not (await response.json())['data'].get('is_admin', False):
                    return
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        await message.answer("Произошла ошибка при проверке статуса админа. Попробуйте позже.")
        return

    text = message.text
    if text == '📣 Рассылка сообщений':
        await state.set_state(BotStates.BROADCAST_MODE)
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        keyboard.add(types.KeyboardButton('Отмена'))
        await message.answer(
            "📣 *Режим рассылки сообщений*\n\n"
            "Введите текст сообщения, которое нужно разослать всем пользователям.\n"
            "Поддерживается форматирование *Markdown*.\n\n"
            "Для отмены рассылки нажмите кнопку 'Отмена'.",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
    elif text == '🚫 Заблокировать пользователя':
        await state.set_state(BotStates.BLOCK_MODE)
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        keyboard.add(types.KeyboardButton('Отмена'))
        await message.answer(
            "🚫 *Блокировка пользователя*\n\n"
            "Введите ID пользователя, которого нужно заблокировать.\n\n"
            "Для отмены операции нажмите кнопку 'Отмена'.",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
    elif text == '✅ Разблокировать пользователя':
        await state.set_state(BotStates.UNBLOCK_MODE)
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        keyboard.add(types.KeyboardButton('Отмена'))
        await message.answer(
            "✅ *Разблокировка пользователя*\n\n"
            "Введите ID пользователя, которого нужно разблокировать.\n\n"
            "Для отмены операции нажмите кнопку 'Отмена'.",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
    elif text == '📊 Статистика бота':
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ADMIN_SERVICE_URL}/stats") as response:
                    response.raise_for_status()
                    stats = (await response.json())['data'].get('stats', '')
                    await message.answer(stats, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await message.answer("Ошибка при получении статистики. Попробуйте позже.")
    elif text == '🔝 Популярные криптовалюты':
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ADMIN_SERVICE_URL}/stats/popular-cryptos") as response:
                    response.raise_for_status()
                    popular = (await response.json())['data'].get('popular', '')
                    await message.answer(popular, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error getting popular cryptos: {e}")
            await message.answer("Ошибка при получении данных. Попробуйте позже.")
    elif text == '🔙 Выход из админ-панели':
        keyboard = create_main_keyboard(message.from_user.id)
        await message.answer("Вы вышли из режима администратора.", reply_markup=keyboard)


@dp.message_handler(state=BotStates.BROADCAST_MODE)
@check_user_blocked()
async def process_broadcast(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == 'Отмена':
        await state.set_state(None)
        keyboard = create_admin_keyboard()
        await message.answer("Рассылка отменена.", reply_markup=keyboard)
    else:
        await message.answer("⏳ Начинаю рассылку сообщения всем пользователям...")
        sent_count, failed_count = await broadcast_message(message.text)
        await state.set_state(None)
        keyboard = create_admin_keyboard()
        result_message = f"✅ Рассылка завершена!\n\n📤 Отправлено: {sent_count}\n❌ Не доставлено: {failed_count}"
        await message.answer(result_message, reply_markup=keyboard)


@dp.message_handler(state=BotStates.BLOCK_MODE)
@check_user_blocked()
async def process_block(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == 'Отмена':
        await state.set_state(None)
        keyboard = create_admin_keyboard()
        await message.answer("Операция отменена.", reply_markup=keyboard)
    else:
        try:
            target_user_id = int(message.text)
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{ADMIN_SERVICE_URL}/users/{target_user_id}/block") as response:
                    response.raise_for_status()
                    await message.answer(f"✅ Пользователь {target_user_id} заблокирован.")
        except ValueError:
            await message.answer("❌ Неверный формат ID пользователя. Введите числовой ID.")
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.set_state(None)
        keyboard = create_admin_keyboard()
        await message.answer("Вернулись в главное меню админ-панели.", reply_markup=keyboard)


@dp.message_handler(state=BotStates.UNBLOCK_MODE)
@check_user_blocked()
async def process_unblock(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == 'Отмена':
        await state.set_state(None)
        keyboard = create_admin_keyboard()
        await message.answer("Операция отменена.", reply_markup=keyboard)
    else:
        try:
            target_user_id = int(message.text)
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{ADMIN_SERVICE_URL}/users/{target_user_id}/unblock") as response:
                    response.raise_for_status()
                    await message.answer(f"✅ Пользователь {target_user_id} разблокирован.")
        except ValueError:
            await message.answer("❌ Неверный формат ID пользователя. Введите числовой ID.")
        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.set_state(None)
        keyboard = create_admin_keyboard()
        await message.answer("Вернулись в главное меню админ-панели.", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: True)
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/block-status") as response:
                response.raise_for_status()
                if (await response.json())['data'].get('is_blocked', True):
                    await callback.answer("Вы заблокированы администратором")
                    return
    except Exception as e:
        logger.error(f"Error checking block status: {e}")
        await callback.answer("Ошибка при проверке статуса. Попробуйте позже.")
        return

    if data.startswith('page_'):
        page = int(data.split('_')[1])
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as response:
                    response.raise_for_status()
                    data = (await response.json())['data']
                    crypto_keys = [key for key in data.keys() if key != "last_updated"]
                    try:
                        sorted_coins = sorted(crypto_keys, key=lambda x: data[x].get("rank", 999))
                    except Exception as e:
                        sorted_coins = crypto_keys
                        logger.error(f"Error sorting coins: {e}")
                    total_pages = (len(crypto_keys) // 10) + (1 if len(crypto_keys) % 10 > 0 else 0)
                    start_index = (page - 1) * 10
                    end_index = min(start_index + 10, len(crypto_keys))
                    message = (
                        f"💰 *Криптовалюты (страница {page} из {total_pages})* 💰\n_(обновлено:"
                        f" {escape_md(data['last_updated'])})_\n\n"
                    )
                    message += print_coins(data, sorted_coins[start_index:end_index])
                    pagination_keyboard = create_pagination_keyboard(page, total_pages)
                    await callback.message.edit_text(message, parse_mode='Markdown', reply_markup=pagination_keyboard)
        except Exception as e:
            logger.error(f"Error handling page callback: {e}")
            await callback.answer("Ошибка при загрузке данных. Попробуйте позже.")
    elif data.startswith('refresh_'):
        symbol = data.split('_')[1]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as response:
                    response.raise_for_status()
                    crypto_data = (await response.json())['data']
                    message = get_coin_info_message(crypto_data, symbol)
                    async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos") as fav_response:
                        fav_response.raise_for_status()
                        favorites = (await fav_response.json())['data'].get('favorites', [])
                        is_favorite = symbol.upper() in [fav.upper() for fav in favorites]
                        keyboard = types.InlineKeyboardMarkup()
                        keyboard.add(
                            types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}"),
                            types.InlineKeyboardButton(
                                "❌ Удалить из избранного" if is_favorite else "⭐ Добавить в избранное",
                                callback_data=f"unfav_{symbol}" if is_favorite else f"fav_{symbol}",
                            ),
                        )
                        await callback.message.edit_text(message, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error refreshing coin info: {e}")
            await callback.answer("Ошибка при обновлении данных. Попробуйте позже.")
    elif data.startswith(('fav_', 'unfav_')):
        action, symbol = data.split('_')
        try:
            async with aiohttp.ClientSession() as session:
                if action == 'fav':
                    async with session.post(
                        f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos", json={'crypto_symbol': symbol}
                    ) as response:
                        response.raise_for_status()
                        if response.status == 201:
                            await callback.answer(f"{symbol} добавлен в избранное!")
                        else:
                            await callback.answer(f"{symbol} уже в избранном")
                else:
                    async with session.delete(
                        f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos", json={'crypto_symbol': symbol}
                    ) as response:
                        response.raise_for_status()
                        if response.status == 200:
                            await callback.answer(f"{symbol} удален из избранного")
                        else:
                            await callback.answer(f"{symbol} не был в избранном")
                async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as crypto_response:
                    crypto_response.raise_for_status()
                    crypto_data = (await crypto_response.json())['data']
                async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos") as fav_response:
                    fav_response.raise_for_status()
                    favorites = (await fav_response.json())['data'].get('favorites', [])
                    is_favorite = symbol.upper() in [fav.upper() for fav in favorites]
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(
                        types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}"),
                        types.InlineKeyboardButton(
                            "❌ Удалить из избранного" if is_favorite else "⭐ Добавить в избранное",
                            callback_data=f"unfav_{symbol}" if is_favorite else f"fav_{symbol}",
                        ),
                    )
                    await callback.message.edit_text(
                        get_coin_info_message(crypto_data, symbol), parse_mode='Markdown', reply_markup=keyboard
                    )
        except Exception as e:
            logger.error(f"Error handling favorite action: {e}")
            await callback.answer("Произошла ошибка. Попробуйте позже.")
    await callback.answer()


@dp.message_handler()
@check_user_blocked()
async def handle_default(message: types.Message):
    await message.answer("Используйте кнопки меню для навигации")


async def main():
    while True:
        try:
            await dp.start_polling()
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
            await asyncio.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
