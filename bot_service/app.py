import telebot
from telebot import types
import requests
import os
from dotenv import load_dotenv
import logging
from functools import wraps
from functools import lru_cache


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = telebot.TeleBot(os.getenv('TELEGRAM_TOKEN'))

# Service URLs
USER_SERVICE_URL = f"http://localhost:{os.getenv('USER_SERVICE_PORT', '5001')}/v1"
ADMIN_SERVICE_URL = f"http://localhost:{os.getenv('ADMIN_SERVICE_PORT', '5002')}/v1"
CRYPTO_SERVICE_URL = f"http://localhost:{os.getenv('CRYPTO_SERVICE_PORT', '5003')}/v1"

# Global states
searching_crypto = {}
broadcast_mode = {}
block_mode = {}


def check_user_blocked(func):
    @wraps(func)
    def wrapped(message, *args, **kwargs):
        user_id = message.from_user.id
        try:
            response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}/block-status")
            response.raise_for_status()
            if response.json()['data'].get('is_blocked', False):
                bot.send_message(message.chat.id, "Вы заблокированы администратором и не можете использовать бота.")
                return
            return func(message, *args, **kwargs)
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error checking block status: {e}")
            return func(message, *args, **kwargs)
        except Exception as e:
            logger.error(f"Unexpected error checking block status: {e}")
            return func(message, *args, **kwargs)
    return wrapped


def register_user(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    try:
        response = requests.post(
            f"{USER_SERVICE_URL}/users",
            json={
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name
            }
        )
        response.raise_for_status()
        logger.info(f"User {user_id} registered/updated")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            error_data = response.json()
            if error_data.get('errors', [{}])[0].get('code') == 'UserAlreadyExists':
                logger.info(f"User {user_id} already exists")
        else:
            logger.error(f"Error registering user {user_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error registering user {user_id}: {e}")


def log_command(user_id, command):
    try:
        response = requests.post(
            f"{USER_SERVICE_URL}/command-logs",
            json={
                'user_id': user_id,
                'command': command
            }
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error logging command: {e}")

@lru_cache(maxsize=10)
def create_admin_keyboard():
    """Создание основной клавиатуры админ-панели"""
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

    # Кнопка "Назад" (если не на первой странице)
    if current_page > 1:
        buttons.append(types.InlineKeyboardButton("◀️", callback_data=f"page_{current_page - 1}"))

    # Номера страниц
    start_page = max(1, current_page - 2)
    end_page = min(total_pages, start_page + 4)

    for page in range(start_page, end_page + 1):
        text = f"•{page}•" if page == current_page else str(page)
        buttons.append(types.InlineKeyboardButton(text, callback_data=f"page_{page}"))

    # Кнопка "Вперед" (если не на последней странице)
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

            # Изменения с эмодзи
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

    # Проверяем, есть ли символ в верхнем или нижнем регистре
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


@bot.message_handler(commands=['start'])
@check_user_blocked
def send_welcome(message):
    register_user(message)
    log_command(message.from_user.id, '/start')

    keyboard = create_main_keyboard(message.from_user.id)
    bot.send_message(
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
def send_help(message):
    register_user(message)
    log_command(message.from_user.id, '/help')

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
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


@bot.message_handler(commands=['prices'])
@check_user_blocked
def send_prices(message):
    register_user(message)
    log_command(message.from_user.id, '/prices')

    try:
        response = requests.get(f"{CRYPTO_SERVICE_URL}/crypto-prices")
        response.raise_for_status()
        data = response.json()['data']
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error getting crypto prices: {e}")
        bot.send_message(message.chat.id, "Не удалось получить данные о ценах. Попробуйте позже.")
        return
    except Exception as e:
        logger.error(f"Unexpected error getting crypto prices: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при получении данных о ценах. Попробуйте позже.")
        return

    formatted_message = format_crypto_message(data)

    crypto_keys = [key for key in data.keys() if key != "last_updated"]
    total_pages = (len(crypto_keys) // 10) + (1 if len(crypto_keys) % 10 > 0 else 0)

    pagination_keyboard = create_pagination_keyboard(1, total_pages)

    bot.send_message(
        message.chat.id,
        formatted_message,
        parse_mode='Markdown',
        reply_markup=pagination_keyboard
    )


@bot.message_handler(commands=['favorites'])
@check_user_blocked
def send_favorites(message):
    register_user(message)
    log_command(message.from_user.id, '/favorites')
    user_id = message.from_user.id

    try:
        # Получаем избранное пользователя
        response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos")
        response.raise_for_status()
        favorites = response.json()['data'].get('favorites', [])

        if not favorites:
            bot.send_message(
                message.chat.id,
                "У вас пока нет избранных криптовалют. Чтобы добавить криптовалюту в ⭐ Избранное, "
                "необходимо перейти в раздел 🔍 Поиск криптовалюты и выбрать нужную криптовалюту."
            )
            return

        # Получаем актуальные цены
        crypto_response = requests.get(f"{CRYPTO_SERVICE_URL}/crypto-prices")
        crypto_response.raise_for_status()
        crypto_data = crypto_response.json()['data']

        # Формируем сообщение
        result = f"⭐ *Ваши избранные криптовалюты* ⭐\n\n"
        result += print_coins(crypto_data, favorites)
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    except requests.exceptions.HTTPError as e:
        logger.error(f"Error getting favorites: {e}")
        bot.send_message(message.chat.id, "Ошибка при получении избранного. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте позже.")


@bot.message_handler(commands=['admin'])
@check_user_blocked
def admin_panel(message):
    user_id = message.from_user.id
    try:
        response = requests.get(f"{ADMIN_SERVICE_URL}/admins/{user_id}/status")
        response.raise_for_status()
        if not response.json()['data'].get('is_admin', False):
            bot.send_message(message.chat.id, "У вас нет доступа к админ-панели.")
            return

        keyboard = create_admin_keyboard()

        bot.send_message(
            message.chat.id,
            "👨‍💻 *Админ-панель криптобота* 👨‍💻\n\n"
            "Выберите действие из меню ниже:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error checking admin status: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при проверке статуса админа. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error checking admin status: {e}")
        bot.send_message(message.chat.id, "Произошла неожиданная ошибка. Попробуйте позже.")


@bot.message_handler(func=lambda message: True)
@check_user_blocked
def handle_text_messages(message):
    register_user(message)
    text = message.text

    if text == '💰 Все криптовалюты':
        send_prices(message)
    elif text == '🔝 Топ-5 криптовалют':
        log_command(message.from_user.id, '/top5')

        try:
            response = requests.get(f"{CRYPTO_SERVICE_URL}/crypto-prices")
            response.raise_for_status()
            data = response.json()['data']
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting crypto prices: {e}")
            bot.send_message(message.chat.id, "Не удалось получить данные о ценах. Попробуйте позже.")
            return
        except Exception as e:
            logger.error(f"Unexpected error getting crypto prices: {e}")
            bot.send_message(message.chat.id, "Произошла ошибка при получении данных о ценах. Попробуйте позже.")
            return

        formatted_message = format_crypto_message(data, limit=5)
        bot.send_message(message.chat.id, formatted_message, parse_mode='Markdown')
    elif text == '🔍 Поиск криптовалюты':
        log_command(message.from_user.id, '/search')

        searching_crypto[message.from_user.id] = True
        keyboard = create_popular_coins_keyboard()
        bot.send_message(
            message.chat.id,
            "Выберите криптовалюту из списка или введите её символ (например, BTC):",
            reply_markup=keyboard
        )
    elif text == '❓ Помощь':
        send_help(message)
    elif text == '🔙 Назад':
        searching_crypto.pop(message.from_user.id, None)
        keyboard = create_main_keyboard(message.from_user.id)
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)
    elif text == '⭐ Избранное':
        send_favorites(message)
    elif text == '👨‍💻 Админ панель':
        admin_panel(message)
    elif searching_crypto.get(message.from_user.id, False):
        if '(' in text and ')' in text:
            symbol = text.split('(')[1].split(')')[0]
            show_coin_info(message, symbol)
        else:
            show_coin_info(message, text)
    elif handle_admin_message(message):
        return
    else:
        bot.send_message(message.chat.id, "Используйте кнопки меню для навигации")

def show_coin_info(message, symbol):
    try:
        response = requests.get(f"{CRYPTO_SERVICE_URL}/crypto-prices")
        response.raise_for_status()
        crypto_data = response.json()['data']
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error getting coin info: {e}")
        bot.send_message(message.chat.id, "Не удалось получить данные о криптовалюте. Попробуйте позже.")
        return
    except Exception as e:
        logger.error(f"Unexpected error getting coin info: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при получении данных о криптовалюте. Попробуйте позже.")
        return

    message_text = get_coin_info_message(crypto_data, symbol)

    if crypto_data and 'error' not in crypto_data:
        user_id = message.from_user.id
        try:
            response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos")
            response.raise_for_status()
            favorites = response.json()['data'].get('favorites', [])
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting favorites: {e}")
            bot.send_message(message.chat.id, "Ошибка при получении избранного. Попробуйте позже.")
            return
        except Exception as e:
            logger.error(f"Unexpected error getting favorites: {e}")
            bot.send_message(message.chat.id, "Произошла ошибка при получении избранного. Попробуйте позже.")
            return

        is_favorite = symbol.upper() in [fav.upper() for fav in favorites]

        keyboard = types.InlineKeyboardMarkup()
        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")

        if is_favorite:
            btn_favorite = types.InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"unfav_{symbol}")
        else:
            btn_favorite = types.InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"fav_{symbol}")

        keyboard.add(btn_refresh, btn_favorite)

        bot.send_message(
            message.chat.id,
            message_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        bot.send_message(message.chat.id, message_text)


def handle_admin_message(message):
    user_id = message.from_user.id
    try:
        response = requests.get(f"{ADMIN_SERVICE_URL}/admins/{user_id}/status")
        response.raise_for_status()
        if not response.json()['data'].get('is_admin', False):
            return False
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error checking admin status: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при проверке статуса админа. Попробуйте позже.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking admin status: {e}")
        bot.send_message(message.chat.id, "Произошла неожиданная ошибка. Попробуйте позже.")
        return False

    text = message.text

    if user_id in broadcast_mode and broadcast_mode[user_id]:
        if text == 'Отмена':
            broadcast_mode[user_id] = False
            keyboard = create_admin_keyboard()
            bot.send_message(user_id, "Рассылка отменена.", reply_markup=keyboard)
        else:
            bot.send_message(user_id, "⏳ Начинаю рассылку сообщения всем пользователям...")
            sent_count, failed_count = broadcast_message(text)

            broadcast_mode[user_id] = False
            keyboard = create_admin_keyboard()

            result_message = f"✅ Рассылка завершена!\n\n"
            result_message += f"📤 Отправлено: {sent_count}\n"
            result_message += f"❌ Не доставлено: {failed_count}"

            bot.send_message(user_id, result_message, reply_markup=keyboard)
        return True

    # Проверка режима блокировки пользователя
    if user_id in block_mode and block_mode[user_id]:
        if text == 'Отмена':
            block_mode[user_id] = False
            keyboard = create_admin_keyboard()
            bot.send_message(user_id, "Операция отменена.", reply_markup=keyboard)
        else:
            try:
                target_user_id = int(text)
                action = block_mode[user_id]

                if action == "block":
                    response = requests.post(f"{ADMIN_SERVICE_URL}/users/{target_user_id}/block")
                    response.raise_for_status()
                    bot.send_message(user_id, f"✅ Пользователь {target_user_id} заблокирован.")
                elif action == "unblock":
                    response = requests.post(f"{ADMIN_SERVICE_URL}/users/{target_user_id}/unblock")
                    response.raise_for_status()
                    bot.send_message(user_id, f"✅ Пользователь {target_user_id} разблокирован.")

            except ValueError:
                bot.send_message(user_id, "❌ Неверный формат ID пользователя. Введите числовой ID.")
            except requests.exceptions.HTTPError as e:
                logger.error(f"Error blocking/unblocking user: {e}")
                bot.send_message(user_id, "Произошла ошибка при блокировке/разблокировке пользователя. Попробуйте позже.")
            except Exception as e:
                logger.error(f"Unexpected error blocking/unblocking user: {e}")
                bot.send_message(user_id, "Произошла неожиданная ошибка при блокировке/разблокировке пользователя. Попробуйте позже.")

            block_mode[user_id] = False
            keyboard = create_admin_keyboard()
            bot.send_message(user_id, "Вернулись в главное меню админ-панели.", reply_markup=keyboard)
        return True

    # Обработка основных команд админ-панели
    if text == '📣 Рассылка сообщений':
        broadcast_mode[user_id] = True

        # Создаем клавиатуру с кнопкой отмены
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        btn_cancel = types.KeyboardButton('Отмена')
        keyboard.add(btn_cancel)

        bot.send_message(user_id,
                              "📣 *Режим рассылки сообщений*\n\n"
                              "Введите текст сообщения, которое нужно разослать всем пользователям.\n"
                              "Поддерживается форматирование *Markdown*.\n\n"
                              "Для отмены рассылки нажмите кнопку 'Отмена'.",
                              parse_mode='Markdown',
                              reply_markup=keyboard)
        return True

    elif text == '🚫 Заблокировать пользователя':
        block_mode[user_id] = "block"

        # Создаем клавиатуру с кнопкой отмены
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        btn_cancel = types.KeyboardButton('Отмена')
        keyboard.add(btn_cancel)

        bot.send_message(user_id,
                              "🚫 *Блокировка пользователя*\n\n"
                              "Введите ID пользователя, которого нужно заблокировать.\n\n"
                              "Для отмены операции нажмите кнопку 'Отмена'.",
                              parse_mode='Markdown',
                              reply_markup=keyboard)
        return True

    elif text == '✅ Разблокировать пользователя':
        block_mode[user_id] = "unblock"

        # Создаем клавиатуру с кнопкой отмены
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        btn_cancel = types.KeyboardButton('Отмена')
        keyboard.add(btn_cancel)

        bot.send_message(user_id,
                              "✅ *Разблокировка пользователя*\n\n"
                              "Введите ID пользователя, которого нужно разблокировать.\n\n"
                              "Для отмены операции нажмите кнопку 'Отмена'.",
                              parse_mode='Markdown',
                              reply_markup=keyboard)
        return True

    elif text == '📊 Статистика бота':
        try:
            response = requests.get(f"{ADMIN_SERVICE_URL}/stats")
            response.raise_for_status()
            stats = response.json()['data'].get('stats', '')
            bot.send_message(user_id, stats, parse_mode='Markdown')
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting bot stats: {e}")
            bot.send_message(user_id, "Произошла ошибка при получении статистики бота. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Unexpected error getting bot stats: {e}")
            bot.send_message(user_id, "Произошла неожиданная ошибка при получении статистики бота. Попробуйте позже.")
        return True

    elif text == '🔝 Популярные криптовалюты':
        try:
            response = requests.get(f"{ADMIN_SERVICE_URL}/stats/popular-cryptos")
            response.raise_for_status()
            popular = response.json()['data'].get('popular', '')
            bot.send_message(user_id, popular, parse_mode='Markdown')
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting popular cryptos: {e}")
            bot.send_message(user_id, "Произошла ошибка при получении популярных криптовалют. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Unexpected error getting popular cryptos: {e}")
            bot.send_message(user_id, "Произошла неожиданная ошибка при получении популярных криптовалют. Попробуйте позже.")
        return True

    elif text == '🔙 Выход из админ-панели':
        keyboard = create_main_keyboard(message.from_user.id)
        bot.send_message(user_id, "Вы вышли из режима администратора.", reply_markup=keyboard)
        return True

    return False


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data
    user_id = call.from_user.id
    try:
        response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}/block-status")
        response.raise_for_status()
        if response.json()['data'].get('is_blocked', True):
            bot.answer_callback_query(call.id, "Вы заблокированы администратором")
            return
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error checking block status: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка при проверке статуса блокировки. Попробуйте позже.")
        return
    except Exception as e:
        logger.error(f"Unexpected error checking block status: {e}")
        bot.answer_callback_query(call.id, "Произошла неожиданная ошибка. Попробуйте позже.")
        return

    if data.startswith('page_'):
        page = int(data.split('_')[1])
        try:
            response = requests.get(f"{CRYPTO_SERVICE_URL}/crypto-prices")
            response.raise_for_status()
            data = response.json()['data']
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting crypto prices: {e}")
            bot.answer_callback_query(call.id, "Не удалось получить данные о ценах")
            return
        except Exception as e:
            logger.error(f"Unexpected error getting crypto prices: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при получении данных о ценах. Попробуйте позже.")
            return

        crypto_keys = [key for key in data.keys() if key != "last_updated"]

        # Сортируем по рангу, если доступен
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

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message,
            parse_mode='Markdown',
            reply_markup=pagination_keyboard
        )

    elif data.startswith('refresh_'):
        symbol = data.split('_')[1]
        try:
            response = requests.get(f"{CRYPTO_SERVICE_URL}/crypto-prices")
            response.raise_for_status()
            crypto_data = response.json()['data']
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error refreshing coin info: {e}")
            bot.answer_callback_query(call.id, "Не удалось обновить данные")
            return
        except Exception as e:
            logger.error(f"Unexpected error refreshing coin info: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при обновлении данных. Попробуйте позже.")
            return

        message = get_coin_info_message(crypto_data, symbol)

        try:
            response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos")
            response.raise_for_status()
            favorites = response.json()['data'].get('favorites', [])
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting favorites: {e}")
            bot.answer_callback_query(call.id, "Ошибка при получении избранного. Попробуйте позже.")
            return
        except Exception as e:
            logger.error(f"Unexpected error getting favorites: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при получении избранного. Попробуйте позже.")
            return

        is_favorite = symbol.upper() in [fav.upper() for fav in favorites]

        keyboard = types.InlineKeyboardMarkup()
        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")

        if is_favorite:
            btn_favorite = types.InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"unfav_{symbol}")
        else:
            btn_favorite = types.InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"fav_{symbol}")

        keyboard.add(btn_refresh, btn_favorite)
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except Exception as e:
            if "message is not modified" in e.result_json.get('description', ''):
                # Игнорируем исключение, если сообщение не изменилось
                print("Сообщение не изменилось, пропускаем обновление.")
            else:
                # Обработка других ошибок
                print(f"Ошибка при изменении сообщения: {e}")
    elif data.startswith(('fav_', 'unfav_')):
        action, symbol = data.split('_')

        if action == 'fav':
            try:
                response = requests.post(
                    f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos",
                    json={'crypto_symbol': symbol}
                )
                response.raise_for_status()
                if response.status_code == 201:
                    bot.answer_callback_query(call.id, f"{symbol} добавлен в избранное!")
                else:
                    bot.answer_callback_query(call.id, f"{symbol} уже в избранном")
            except requests.exceptions.HTTPError as e:
                logger.error(f"Error adding favorite: {e}")
                bot.answer_callback_query(call.id, "Ошибка при добавлении в избранное. Попробуйте позже.")
            except Exception as e:
                logger.error(f"Unexpected error adding favorite: {e}")
                bot.answer_callback_query(call.id, "Произошла ошибка при добавлении в избранное. Попробуйте позже.")
        else:
            try:
                response = requests.delete(
                    f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos/{symbol}"
                )
                response.raise_for_status()
                if response.status_code == 200:
                    bot.answer_callback_query(call.id, f"{symbol} удален из избранного")
                else:
                    bot.answer_callback_query(call.id, f"{symbol} не был в избранном")
            except requests.exceptions.HTTPError as e:
                logger.error(f"Error removing favorite: {e}")
                bot.answer_callback_query(call.id, "Ошибка при удалении из избранного. Попробуйте позже.")
            except Exception as e:
                logger.error(f"Unexpected error removing favorite: {e}")
                bot.answer_callback_query(call.id, "Произошла ошибка при удалении из избранного. Попробуйте позже.")

        # Refresh the message
        try:
            response = requests.get(f"{CRYPTO_SERVICE_URL}/crypto-prices")
            response.raise_for_status()
            crypto_data = response.json()['data']
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting crypto prices: {e}")
            bot.answer_callback_query(call.id, "Не удалось получить данные о ценах. Попробуйте позже.")
            return
        except Exception as e:
            logger.error(f"Unexpected error getting crypto prices: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при получении данных о ценах. Попробуйте позже.")
            return

        try:
            response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}/favorite-cryptos")
            response.raise_for_status()
            favorites = response.json()['data'].get('favorites', [])
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting favorites: {e}")
            bot.answer_callback_query(call.id, "Ошибка при получении избранного. Попробуйте позже.")
            return
        except Exception as e:
            logger.error(f"Unexpected error getting favorites: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при получении избранного. Попробуйте позже.")
            return

        is_favorite = symbol.upper() in [fav.upper() for fav in favorites]

        keyboard = types.InlineKeyboardMarkup()
        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")

        if is_favorite:
            btn_favorite = types.InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"unfav_{symbol}")
        else:
            btn_favorite = types.InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"fav_{symbol}")

        keyboard.add(btn_refresh, btn_favorite)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=get_coin_info_message(crypto_data, symbol),
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    bot.answer_callback_query(call.id)


def broadcast_message(message_text):
    """Broadcast message to all users"""
    try:
        response = requests.get(f"{USER_SERVICE_URL}/users/unblocked")
        response.raise_for_status()
        users = response.json()['data'].get('users', [])
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error getting unblocked users: {e}")
        return 0, 0
    except Exception as e:
        logger.error(f"Unexpected error getting unblocked users: {e}")
        return 0, 0

    sent_count = 0
    failed_count = 0

    for user_id in users:
        try:
            bot.send_message(user_id, message_text, parse_mode='Markdown')
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    return sent_count, failed_count



if __name__ == '__main__':
    logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    bot.polling(none_stop=True)
