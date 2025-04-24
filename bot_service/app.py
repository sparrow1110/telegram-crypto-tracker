from telebot.async_telebot import AsyncTeleBot
from telebot import types
import aiohttp
import asyncio
import os
from dotenv import load_dotenv
import logging
from functools import wraps, lru_cache

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = AsyncTeleBot(os.getenv('TELEGRAM_TOKEN'))

# URL сервисов
USER_SERVICE_URL = f"http://localhost:{os.getenv('USER_SERVICE_PORT', '5001')}/v1"
ADMIN_SERVICE_URL = f"http://localhost:{os.getenv('ADMIN_SERVICE_PORT', '5002')}/v1"
CRYPTO_SERVICE_URL = f"http://localhost:{os.getenv('CRYPTO_SERVICE_PORT', '5003')}/v1"

# Глобальные состояния
searching_crypto = {}
broadcast_mode = {}
block_mode = {}


def check_user_blocked(func):
    @wraps(func)
    async def wrapped(message, *args, **kwargs):
        user_id = message.from_user.id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/block-status") as response:
                    response.raise_for_status()
                    if (await response.json())['data'].get('is_blocked', False):
                        await bot.send_message(message.chat.id, "Вы заблокированы администратором.")
                        return
                    return await func(message, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error checking block status: {e}")
            return await func(message, *args, **kwargs)

    return wrapped


async def register_user(message):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{USER_SERVICE_URL}/users",
                json={
                    'user_id': message.from_user.id,
                    'username': message.from_user.username,
                    'first_name': message.from_user.first_name,
                    'last_name': message.from_user.last_name
                }
            )
        logger.info(f"User {message.from_user.id} registered")
    except Exception as e:
        logger.error(f"Error registering user: {e}")


async def log_command(user_id, command):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{USER_SERVICE_URL}/command-logs",
                json={'user_id': user_id, 'command': command}
            )
    except Exception as e:
        logger.error(f"Error logging command: {e}")


@lru_cache(maxsize=10)
def create_admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_broadcast = types.KeyboardButton('📣 Рассылка сообщений')
    btn_block_user = types.KeyboardButton('🚫 Заблокировать пользователя')
    btn_unblock_user = types.KeyboardButton('✅ Разблокировать пользователя')
    btn_stats = types.KeyboardButton('📊 Статистика бота')
    btn_popular = types.KeyboardButton('🔝 Популярные криптовалюты')
    btn_exit = types.KeyboardButton('🔙 Выход из админ-панели')
    keyboard.add(btn_broadcast, btn_stats)
    keyboard.add(btn_block_user, btn_unblock_user)
    keyboard.add(btn_popular, btn_exit)
    return keyboard


@lru_cache(maxsize=10)
def create_main_keyboard(user_id=None):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_prices = types.KeyboardButton('💰 Все криптовалюты')
    btn_top5 = types.KeyboardButton('🔝 Топ-5 криптовалют')
    btn_search = types.KeyboardButton('🔍 Поиск криптовалюты')
    btn_favorites = types.KeyboardButton('⭐ Избранное')
    btn_help = types.KeyboardButton('❓ Помощь')
    keyboard.add(btn_prices, btn_top5)
    keyboard.add(btn_search, btn_favorites)
    keyboard.add(btn_help)

    if user_id and str(user_id) in os.getenv('ADMIN_IDS', '').split(','):
        btn_admin = types.KeyboardButton('👨‍💻 Админ панель')
        keyboard.add(btn_admin)
    return keyboard


@lru_cache(maxsize=10)
def create_popular_coins_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    btn_btc = types.KeyboardButton('Bitcoin (BTC)')
    btn_eth = types.KeyboardButton('Ethereum (ETH)')
    btn_usdt = types.KeyboardButton('Tether (USDT)')
    btn_bnb = types.KeyboardButton('Binance Coin (BNB)')
    btn_sol = types.KeyboardButton('Solana (SOL)')
    btn_xrp = types.KeyboardButton('Ripple (XRP)')
    btn_ada = types.KeyboardButton('Cardano (ADA)')
    btn_doge = types.KeyboardButton('Dogecoin (DOGE)')
    btn_back = types.KeyboardButton('🔙 Назад')
    keyboard.add(btn_btc, btn_eth, btn_usdt)
    keyboard.add(btn_bnb, btn_sol, btn_xrp)
    keyboard.add(btn_ada, btn_doge)
    keyboard.add(btn_back)
    return keyboard


def create_pagination_keyboard(current_page, total_pages):
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
            result += f"*{symbol}* ({coin_name})\n"
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
            result += f"*{symbol}* - нет данных\n\n"
    return result


def format_crypto_message(data, limit=10):
    if not data or "last_updated" not in data:
        return "Данные о ценах недоступны. Попробуйте позже."

    message = f"💰 *Актуальные цены криптовалют* 💰\n_(обновлено: {data['last_updated']})_\n\n"
    crypto_keys = [key for key in data.keys() if key != "last_updated"]

    try:
        sorted_coins = sorted(crypto_keys, key=lambda x: data[x].get("rank", 999))
    except:
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
            return f"Криптовалюта {symbol} не найдена. Попробуйте другой символ."
        else:
            suggestions = ", ".join(similar_coins[:5])
            return f"Криптовалюта {symbol} не найдена. Возможно, вы имели в виду: {suggestions}?"

    values = data[symbol]
    coin_name = values.get("name", symbol)
    message = f"💰 *{symbol}* ({coin_name})\n"
    message += f"_(данные на: {data['last_updated']})_\n\n"

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


async def broadcast_message(message_text):
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


@bot.message_handler(commands=['start'])
@check_user_blocked
async def send_welcome(message):
    await register_user(message)
    await log_command(message.from_user.id, '/start')

    keyboard = create_main_keyboard(message.from_user.id)
    await bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для отслеживания цен криптовалют.\n\n"
        "Используйте кнопки ниже для навигации или следующие команды:\n"
        "/prices - получить актуальные цены популярных криптовалют\n"
        "/favorites - показать ваши избранные криптовалюты\n"
        "/help - справка по всем командам",
        reply_markup=keyboard
    )


@bot.message_handler(commands=['help'])
@check_user_blocked
async def send_help(message):
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
    await bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


@bot.message_handler(commands=['prices'])
@check_user_blocked
async def send_prices(message):
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

                await bot.send_message(
                    message.chat.id,
                    formatted_message,
                    parse_mode='Markdown',
                    reply_markup=pagination_keyboard
                )
    except Exception as e:
        logger.error(f"Error getting prices: {e}")
        await bot.send_message(message.chat.id, "Ошибка при получении данных о ценах. Попробуйте позже.")


@bot.message_handler(commands=['favorites'])
@check_user_blocked
async def send_favorites(message):
    await register_user(message)
    await log_command(message.from_user.id, '/favorites')
    user_id = message.from_user.id

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos") as response:
                response.raise_for_status()
                favorites = (await response.json())['data'].get('favorites', [])

                if not favorites:
                    await bot.send_message(
                        message.chat.id,
                        "У вас пока нет избранных криптовалют. Чтобы добавить криптовалюту в ⭐ Избранное, "
                        "необходимо перейти в раздел 🔍 Поиск криптовалюты и выбрать нужную криптовалюту."
                    )
                    return

            async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as response:
                response.raise_for_status()
                crypto_data = (await response.json())['data']

                result = f"⭐ *Ваши избранные криптовалюты* ⭐\n\n"
                result += print_coins(crypto_data, favorites)
                await bot.send_message(message.chat.id, result, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        await bot.send_message(message.chat.id, "Ошибка при получении избранного. Попробуйте позже.")


@bot.message_handler(commands=['admin'])
@check_user_blocked
async def admin_panel(message):
    await register_user(message)
    user_id = message.from_user.id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ADMIN_SERVICE_URL}/admins/{user_id}/status") as response:
                response.raise_for_status()
                if not (await response.json())['data'].get('is_admin', False):
                    await bot.send_message(message.chat.id, "У вас нет доступа к админ-панели.")
                    return

        keyboard = create_admin_keyboard()
        await bot.send_message(
            message.chat.id,
            "👨‍💻 *Админ-панель криптобота* 👨‍💻\n\n"
            "Выберите действие из меню ниже:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        await bot.send_message(message.chat.id, "Произошла ошибка при проверке статуса админа. Попробуйте позже.")


@bot.message_handler(func=lambda message: True)
@check_user_blocked
async def handle_text_messages(message):
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
                    await bot.send_message(message.chat.id, formatted_message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error getting top5: {e}")
            await bot.send_message(message.chat.id, "Ошибка при получении данных. Попробуйте позже.")

    elif text == '🔍 Поиск криптовалюты':
        await register_user(message)
        await log_command(message.from_user.id, '/search')
        searching_crypto[message.from_user.id] = True
        keyboard = create_popular_coins_keyboard()
        await bot.send_message(
            message.chat.id,
            "Выберите криптовалюту из списка или введите её символ (например, BTC):",
            reply_markup=keyboard
        )

    elif text == '❓ Помощь':
        await send_help(message)

    elif text == '🔙 Назад':
        await register_user(message)
        searching_crypto.pop(message.from_user.id, None)
        keyboard = create_main_keyboard(message.from_user.id)
        await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)

    elif text == '⭐ Избранное':
        await send_favorites(message)

    elif text == '👨‍💻 Админ панель':
        await admin_panel(message)

    elif searching_crypto.get(message.from_user.id, False):
        if '(' in text and ')' in text:
            symbol = text.split('(')[1].split(')')[0]
            await show_coin_info(message, symbol)
        else:
            await show_coin_info(message, text)

    elif await handle_admin_message(message):
        return

    else:
        await bot.send_message(message.chat.id, "Используйте кнопки меню для навигации")


async def show_coin_info(message, symbol):
    await register_user(message)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as response:
                response.raise_for_status()
                crypto_data = (await response.json())['data']

                message_text = get_coin_info_message(crypto_data, symbol)

                if 'error' not in crypto_data:
                    async with session.get(
                            f"{USER_SERVICE_URL}/users/{message.from_user.id}/favorite-cryptos") as fav_response:
                        fav_response.raise_for_status()
                        favorites = (await fav_response.json())['data'].get('favorites', [])

                        is_favorite = symbol.upper() in [fav.upper() for fav in favorites]
                        keyboard = types.InlineKeyboardMarkup()
                        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")

                        if is_favorite:
                            btn_favorite = types.InlineKeyboardButton("❌ Удалить из избранного",
                                                                      callback_data=f"unfav_{symbol}")
                        else:
                            btn_favorite = types.InlineKeyboardButton("⭐ Добавить в избранное",
                                                                      callback_data=f"fav_{symbol}")

                        keyboard.add(btn_refresh, btn_favorite)
                        await bot.send_message(
                            message.chat.id,
                            message_text,
                            parse_mode='Markdown',
                            reply_markup=keyboard
                        )
                else:
                    await bot.send_message(message.chat.id, message_text)

    except Exception as e:
        logger.error(f"Error showing coin info: {e}")
        await bot.send_message(message.chat.id, "Ошибка при получении данных о криптовалюте. Попробуйте позже.")


async def handle_admin_message(message):
    user_id = message.from_user.id
    await register_user(message)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ADMIN_SERVICE_URL}/admins/{user_id}/status") as response:
                response.raise_for_status()
                if not (await response.json())['data'].get('is_admin', False):
                    return False
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

    text = message.text

    if user_id in broadcast_mode and broadcast_mode[user_id]:
        if text == 'Отмена':
            broadcast_mode[user_id] = False
            keyboard = create_admin_keyboard()
            await bot.send_message(user_id, "Рассылка отменена.", reply_markup=keyboard)
        else:
            await bot.send_message(user_id, "⏳ Начинаю рассылку сообщения всем пользователям...")
            sent_count, failed_count = await broadcast_message(text)
            broadcast_mode[user_id] = False
            keyboard = create_admin_keyboard()
            result_message = f"✅ Рассылка завершена!\n\n📤 Отправлено: {sent_count}\n❌ Не доставлено: {failed_count}"
            await bot.send_message(user_id, result_message, reply_markup=keyboard)
        return True

    if user_id in block_mode and block_mode[user_id]:
        if text == 'Отмена':
            block_mode[user_id] = False
            keyboard = create_admin_keyboard()
            await bot.send_message(user_id, "Операция отменена.", reply_markup=keyboard)
        else:
            try:
                target_user_id = int(text)
                action = block_mode[user_id]

                async with aiohttp.ClientSession() as session:
                    if action == "block":
                        async with session.post(f"{ADMIN_SERVICE_URL}/users/{target_user_id}/block") as response:
                            response.raise_for_status()
                            await bot.send_message(user_id, f"✅ Пользователь {target_user_id} заблокирован.")
                    elif action == "unblock":
                        async with session.post(f"{ADMIN_SERVICE_URL}/users/{target_user_id}/unblock") as response:
                            response.raise_for_status()
                            await bot.send_message(user_id, f"✅ Пользователь {target_user_id} разблокирован.")

            except ValueError:
                await bot.send_message(user_id, "❌ Неверный формат ID пользователя. Введите числовой ID.")
            except Exception as e:
                logger.error(f"Error blocking/unblocking: {e}")
                await bot.send_message(user_id, "Произошла ошибка. Попробуйте позже.")

            block_mode[user_id] = False
            keyboard = create_admin_keyboard()
            await bot.send_message(user_id, "Вернулись в главное меню админ-панели.", reply_markup=keyboard)
        return True

    if text == '📣 Рассылка сообщений':
        broadcast_mode[user_id] = True
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        btn_cancel = types.KeyboardButton('Отмена')
        keyboard.add(btn_cancel)
        await bot.send_message(
            user_id,
            "📣 *Режим рассылки сообщений*\n\n"
            "Введите текст сообщения, которое нужно разослать всем пользователям.\n"
            "Поддерживается форматирование *Markdown*.\n\n"
            "Для отмены рассылки нажмите кнопку 'Отмена'.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return True

    elif text == '🚫 Заблокировать пользователя':
        block_mode[user_id] = "block"
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        btn_cancel = types.KeyboardButton('Отмена')
        keyboard.add(btn_cancel)
        await bot.send_message(
            user_id,
            "🚫 *Блокировка пользователя*\n\n"
            "Введите ID пользователя, которого нужно заблокировать.\n\n"
            "Для отмены операции нажмите кнопку 'Отмена'.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return True

    elif text == '✅ Разблокировать пользователя':
        block_mode[user_id] = "unblock"
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        btn_cancel = types.KeyboardButton('Отмена')
        keyboard.add(btn_cancel)
        await bot.send_message(
            user_id,
            "✅ *Разблокировка пользователя*\n\n"
            "Введите ID пользователя, которого нужно разблокировать.\n\n"
            "Для отмены операции нажмите кнопку 'Отмена'.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return True

    elif text == '📊 Статистика бота':
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ADMIN_SERVICE_URL}/stats") as response:
                    response.raise_for_status()
                    stats = (await response.json())['data'].get('stats', '')
                    await bot.send_message(user_id, stats, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await bot.send_message(user_id, "Ошибка при получении статистики. Попробуйте позже.")
        return True

    elif text == '🔝 Популярные криптовалюты':
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ADMIN_SERVICE_URL}/stats/popular-cryptos") as response:
                    response.raise_for_status()
                    popular = (await response.json())['data'].get('popular', '')
                    await bot.send_message(user_id, popular, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error getting popular cryptos: {e}")
            await bot.send_message(user_id, "Ошибка при получении данных. Попробуйте позже.")
        return True

    elif text == '🔙 Выход из админ-панели':
        keyboard = create_main_keyboard(message.from_user.id)
        await bot.send_message(user_id, "Вы вышли из режима администратора.", reply_markup=keyboard)
        return True

    return False


@bot.callback_query_handler(func=lambda call: True)
async def handle_callback(call):
    data = call.data
    user_id = call.from_user.id

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/block-status") as response:
                response.raise_for_status()
                if (await response.json())['data'].get('is_blocked', True):
                    await bot.answer_callback_query(call.id, "Вы заблокированы администратором")
                    return
    except Exception as e:
        logger.error(f"Error checking block status: {e}")
        await bot.answer_callback_query(call.id, "Ошибка при проверке статуса. Попробуйте позже.")
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
                    except:
                        sorted_coins = crypto_keys

                    total_pages = (len(crypto_keys) // 10) + (1 if len(crypto_keys) % 10 > 0 else 0)
                    start_index = (page - 1) * 10
                    end_index = min(start_index + 10, len(crypto_keys))

                    message = f"💰 *Криптовалюты (страница {page} из {total_pages})* 💰\n_(обновлено: {data['last_updated']})_\n\n"
                    message += print_coins(data, sorted_coins[start_index:end_index])

                    pagination_keyboard = create_pagination_keyboard(page, total_pages)

                    await bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=message,
                        parse_mode='Markdown',
                        reply_markup=pagination_keyboard
                    )
        except Exception as e:
            logger.error(f"Error handling page callback: {e}")
            await bot.answer_callback_query(call.id, "Ошибка при загрузке данных. Попробуйте позже.")

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
                        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")

                        if is_favorite:
                            btn_favorite = types.InlineKeyboardButton("❌ Удалить из избранного",
                                                                      callback_data=f"unfav_{symbol}")
                        else:
                            btn_favorite = types.InlineKeyboardButton("⭐ Добавить в избранное",
                                                                      callback_data=f"fav_{symbol}")

                        keyboard.add(btn_refresh, btn_favorite)

                        await bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=message,
                            parse_mode='Markdown',
                            reply_markup=keyboard
                        )
        except Exception as e:
            logger.error(f"Error refreshing coin info: {e}")
            await bot.answer_callback_query(call.id, "Ошибка при обновлении данных. Попробуйте позже.")

    elif data.startswith(('fav_', 'unfav_')):
        action, symbol = data.split('_')

        try:
            async with aiohttp.ClientSession() as session:
                if action == 'fav':
                    async with session.post(
                            f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos",
                            json={'crypto_symbol': symbol}
                    ) as response:
                        response.raise_for_status()
                        if response.status == 201:
                            await bot.answer_callback_query(call.id, f"{symbol} добавлен в избранное!")
                        else:
                            await bot.answer_callback_query(call.id, f"{symbol} уже в избранном")
                else:
                    async with session.delete(
                            f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos",
                            json={'crypto_symbol': symbol}
                    ) as response:
                        response.raise_for_status()
                        if response.status == 200:
                            await bot.answer_callback_query(call.id, f"{symbol} удален из избранного")
                        else:
                            await bot.answer_callback_query(call.id, f"{symbol} не был в избранном")

                # Обновляем сообщение
                async with session.get(f"{CRYPTO_SERVICE_URL}/crypto-prices") as crypto_response:
                    crypto_response.raise_for_status()
                    crypto_data = (await crypto_response.json())['data']

                async with session.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos") as fav_response:
                    fav_response.raise_for_status()
                    favorites = (await fav_response.json())['data'].get('favorites', [])

                is_favorite = symbol.upper() in [fav.upper() for fav in favorites]
                keyboard = types.InlineKeyboardMarkup()
                btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")

                if is_favorite:
                    btn_favorite = types.InlineKeyboardButton("❌ Удалить из избранного",
                                                              callback_data=f"unfav_{symbol}")
                else:
                    btn_favorite = types.InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"fav_{symbol}")

                keyboard.add(btn_refresh, btn_favorite)

                await bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=get_coin_info_message(crypto_data, symbol),
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )

        except Exception as e:
            logger.error(f"Error handling favorite action: {e}")
            await bot.answer_callback_query(call.id, "Произошла ошибка. Попробуйте позже.")

    await bot.answer_callback_query(call.id)


async def main():
    await bot.polling(non_stop=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
