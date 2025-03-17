import requests
import json
import time
import threading
import telebot
from telebot import types
import logging
import os
from datetime import datetime
from db_handler import DatabaseManager
from admin_panel import AdminPanel, ADMIN_IDS
from config import TOKEN, DATA_FILE
from cachetools import cached, TTLCache
from functools import lru_cache

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Создаем экземпляр бота
bot = telebot.TeleBot(TOKEN)

# Создаем экземпляр менеджера базы данных
db = DatabaseManager()

# Создаем экземпляр админ-панели
admin = AdminPanel(bot)

# Глобальная переменная для отслеживания состояния поиска
searching_crypto = False

# Кэш на 5 минут (300 секунд)
crypto_cache = TTLCache(maxsize=100, ttl=300)


def check_user_blocked(func):
    def wrapper(message, *args, **kwargs):
        if admin.is_user_blocked(message.from_user.id):
            bot.send_message(message.chat.id, "Вы заблокированы администратором и не можете использовать бота.")
            return
        return func(message, *args, **kwargs)
    return wrapper


# Функция для парсинга цен криптовалют
def parse_crypto_prices():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0"
        }

        url = "https://api.coinlore.net/api/tickers/"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            data_formatted = {}

            # Добавляем временную метку
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data_formatted["last_updated"] = timestamp

            # Форматируем данные для более удобного доступа
            for coin in data["data"]:
                data_formatted[coin["symbol"]] = {
                    "name": coin["name"],
                    "price_usd": float(coin["price_usd"]),
                    "percent_change_1h": float(coin["percent_change_1h"]),
                    "percent_change_24h": float(coin["percent_change_24h"]),
                    "percent_change_7d": float(coin["percent_change_7d"]),
                    "market_cap_usd": float(coin["market_cap_usd"]),
                    "rank": int(coin["rank"])
                }

            # Сохраняем данные в файл
            with open(DATA_FILE, 'w') as f:
                json.dump(data_formatted, f, indent=4)

            logger.info(f"Цены успешно обновлены и сохранены в {DATA_FILE}")
            return data_formatted
        else:
            logger.error(f"Ошибка получения данных: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при парсинге цен: {e}")
        return None


# Функция для чтения цен из файла
@cached(crypto_cache)
def read_crypto_prices():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            return data
        else:
            logger.warning(f"Файл {DATA_FILE} не найден")
            return None
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {e}")
        return None


# Функция, которая будет запускаться в отдельном потоке для периодического обновления цен
def scheduled_parsing():
    while True:
        parse_crypto_prices()
        time.sleep(300)  # Ждем 5 минут (300 секунд)


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


# Создаем красивое сообщение с ценами
def format_crypto_message(data, limit=10):
    if not data or "last_updated" not in data:
        return "Данные о ценах недоступны. Попробуйте позже."

    message = f"💰 *Актуальные цены криптовалют* 💰\n_(обновлено: {data['last_updated']})_\n\n"

    # Отфильтруем ключи, которые не являются криптовалютами
    crypto_keys = [key for key in data.keys() if key != "last_updated"]

    # Сортируем по рангу, если доступен
    try:
        sorted_coins = sorted(crypto_keys, key=lambda x: data[x].get("rank", 999))
    except:
        sorted_coins = crypto_keys

    # Ограничиваем вывод
    coins_to_display = sorted_coins[:limit]

    message += print_coins(data, coins_to_display)
    return message


# Функция для получения информации по конкретной криптовалюте
def get_coin_info(data, symbol):
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


# Функция для создания главной клавиатуры
@lru_cache(maxsize=10)
def create_main_keyboard(user_id=None):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    # Создаем кнопки
    btn_prices = types.KeyboardButton('💰 Все криптовалюты')
    btn_top5 = types.KeyboardButton('🔝 Топ-5 криптовалют')
    btn_search = types.KeyboardButton('🔍 Поиск криптовалюты')
    btn_favorites = types.KeyboardButton('⭐ Избранное')
    btn_help = types.KeyboardButton('❓ Помощь')

    # Добавляем кнопки на клавиатуру
    keyboard.add(btn_prices, btn_top5)
    keyboard.add(btn_search, btn_favorites)
    keyboard.add(btn_help)

    # Если пользователь администратор, добавляем кнопку "Админ панель"
    if user_id and user_id in ADMIN_IDS:
        btn_admin = types.KeyboardButton('👨‍💻 Админ панель')
        keyboard.add(btn_admin)

    return keyboard


# Функция для создания клавиатуры с популярными криптовалютами
@lru_cache(maxsize=10)
def create_popular_coins_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)

    # Создаем кнопки для популярных криптовалют
    btn_btc = types.KeyboardButton('Bitcoin (BTC)')
    btn_eth = types.KeyboardButton('Ethereum (ETH)')
    btn_usdt = types.KeyboardButton('Tether (USDT)')
    btn_bnb = types.KeyboardButton('Binance Coin (BNB)')
    btn_sol = types.KeyboardButton('Solana (SOL)')
    btn_xrp = types.KeyboardButton('Ripple (XRP)')
    btn_ada = types.KeyboardButton('Cardano (ADA)')
    btn_doge = types.KeyboardButton('Dogecoin (DOGE)')
    btn_back = types.KeyboardButton('🔙 Назад')

    # Добавляем кнопки на клавиатуру
    keyboard.add(btn_btc, btn_eth, btn_usdt)
    keyboard.add(btn_bnb, btn_sol, btn_xrp)
    keyboard.add(btn_ada, btn_doge)
    keyboard.add(btn_back)

    return keyboard


# Функция для создания клавиатуры с кнопками страниц
@lru_cache(maxsize=10)
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


# Функция для регистрации или обновления пользователя в БД
def register_user_from_message(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    db.register_user(user_id, username, first_name, last_name)

    # Если пользователь не заблокирован, обновляем его активность
    if not admin.is_user_blocked(user_id):
        db.update_user_activity(user_id)


# Функция для логирования команды пользователя
def log_user_command(message, command):
    user_id = message.from_user.id
    if not admin.is_user_blocked(user_id):
        db.log_command(user_id, command)


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Регистрируем пользователя
    register_user_from_message(message)

    log_user_command(message, '/start')
    # Создаем клавиатуру
    keyboard = create_main_keyboard(message.from_user.id)

    bot.send_message(message.chat.id,
                     "👋 Привет! Я бот для отслеживания цен криптовалют.\n\n"
                     "Используйте кнопки ниже для навигации или следующие команды:\n"
                     "/prices - получить актуальные цены популярных криптовалют\n"
                     "/favorites - показать ваши избранные криптовалюты\n"
                     "/help - справка по всем командам",
                     reply_markup=keyboard)


# Обработчик команды /prices
@bot.message_handler(commands=['prices'])
def send_prices(message):
    # Обновляем активность пользователя
    register_user_from_message(message)

    log_user_command(message, '/prices')

    data = read_crypto_prices()
    if not data:
        # Если файл не найден, делаем парсинг
        data = parse_crypto_prices()

    formatted_message = format_crypto_message(data)

    # Определяем количество страниц
    crypto_keys = [key for key in data.keys() if key != "last_updated"]
    total_pages = (len(crypto_keys) // 10) + (1 if len(crypto_keys) % 10 > 0 else 0)

    # Создаем клавиатуру с кнопками страниц
    pagination_keyboard = create_pagination_keyboard(1, total_pages)

    bot.send_message(message.chat.id, formatted_message, parse_mode='Markdown', reply_markup=pagination_keyboard)


# Обработчик команды /favorites
@bot.message_handler(commands=['favorites'])
def send_favorites(message):
    # Обновляем активность пользователя
    register_user_from_message(message)

    log_user_command(message, '/favorites')

    user_id = message.from_user.id
    favorites = db.get_favorite_cryptos(user_id)

    if not favorites:
        bot.send_message(message.chat.id,
                         "У вас пока нет избранных криптовалют. Чтобы добавить криптовалюту в ⭐ Избранное, необходимо"
                         " перейти в раздел 🔍 Поиск криптовалюты и выбрать нужную криптовалюту.")
        return

    data = read_crypto_prices()
    if not data:
        data = parse_crypto_prices()

    if not data:
        bot.send_message(message.chat.id, "Не удалось получить данные о ценах. Попробуйте позже.")
        return

    result = f"⭐ *Ваши избранные криптовалюты* ⭐\n\n"

    result += print_coins(data, favorites)

    bot.send_message(message.chat.id, result, parse_mode='Markdown')


# Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    # Обновляем активность пользователя
    register_user_from_message(message)

    log_user_command(message, '/help')

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


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        admin.handle_admin_command(message)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к админ-панели.")


# Обработчик текстовых сообщений (для кнопок)
@bot.message_handler(func=lambda message: True)
@check_user_blocked
def handle_text_messages(message):
    global searching_crypto
    text = message.text

    # Проверяем, не в режиме ли администратора пользователь
    if admin.handle_admin_message(message):
        return

    if text == '💰 Все криптовалюты':
        # Показываем все криптовалюты
        send_prices(message)

    elif text == '🔝 Топ-5 криптовалют':
        # Показываем только топ-5 криптовалют
        register_user_from_message(message)

        log_user_command(message, '/top5')
        data = read_crypto_prices()
        if not data:
            data = parse_crypto_prices()

        formatted_message = format_crypto_message(data, limit=5)
        bot.send_message(message.chat.id, formatted_message, parse_mode='Markdown')

    elif text == '🔍 Поиск криптовалюты':
        # Устанавливаем флаг поиска
        searching_crypto = True

        register_user_from_message(message)
        log_user_command(message, '/search')

        # Показываем клавиатуру с популярными криптовалютами
        keyboard = create_popular_coins_keyboard()
        bot.send_message(message.chat.id,
                         "Выберите криптовалюту из списка или введите её символ (например, BTC):",
                         reply_markup=keyboard)

        # Устанавливаем следующий шаг - ожидание ввода символа монеты
        bot.register_next_step_handler(message, process_coin_search)

    elif text == '❓ Помощь':
        send_help(message)

    elif text == '🔙 Назад':
        # Сбрасываем флаг поиска
        searching_crypto = False

        # Возвращаемся к основной клавиатуре
        keyboard = create_main_keyboard(message.from_user.id)
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)

    elif text == '⭐ Избранное':
        # Показываем избранные криптовалюты
        send_favorites(message)

    elif text == '👨‍💻 Админ панель':
        admin_panel(message)

    elif searching_crypto:
        if '(' in text and ')' in text:
            # Извлекаем символ из текста кнопки
            symbol = text.split('(')[1].split(')')[0]
            show_coin_info(message, symbol)
        else:
            show_coin_info(message, text)

    else:
        # Игнорируем ввод, если он не последовал за кнопкой "Поиск криптовалюты"
        pass


# Функция для обработки поиска монеты
def process_coin_search(message):
    symbol = message.text

    # Если пользователь нажал "Назад", возвращаемся в главное меню
    if symbol == '🔙 Назад':
        keyboard = create_main_keyboard(message.from_user.id)
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)
        return

    # Проверяем, содержит ли текст символ в скобках
    if '(' in symbol and ')' in symbol:
        symbol = symbol.split('(')[1].split(')')[0]

    show_coin_info(message, symbol)


# Функция для отображения информации о монете (с кнопкой добавления в избранное)
def show_coin_info(message, symbol):
    data = read_crypto_prices()
    if not data:
        data = parse_crypto_prices()

    coin_message = get_coin_info(data, symbol)
    if coin_message[0] == "💰":
        # Проверяем, находится ли монета в избранном
        user_id = message.from_user.id
        favorites = db.get_favorite_cryptos(user_id)
        is_favorite = symbol.upper() in [fav.upper() for fav in favorites]

        # Создаем инлайн-клавиатуру для действий с монетой
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")

        # Кнопка добавления/удаления из избранного
        if is_favorite:
            btn_favorite = types.InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"unfav_{symbol}")
        else:
            btn_favorite = types.InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"fav_{symbol}")

        keyboard.add(btn_refresh, btn_favorite)

        bot.send_message(message.chat.id, coin_message, parse_mode='Markdown', reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, coin_message)


# Обработчик callback-запросов (для пагинации и инлайн-кнопок)
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    # Получаем данные из callback
    data = call.data
    user_id = call.from_user.id

    if admin.is_user_blocked(user_id):
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Вы заблокированы администратором и не можете использовать бота.",
        )

    # Обработка пагинации
    elif data.startswith('page_'):
        page = int(data.split('_')[1])

        crypto_data = read_crypto_prices()
        if not crypto_data:
            crypto_data = parse_crypto_prices()

        # Отфильтруем ключи, которые не являются криптовалютами
        crypto_keys = [key for key in crypto_data.keys() if key != "last_updated"]

        # Сортируем по рангу, если доступен
        try:
            sorted_coins = sorted(crypto_keys, key=lambda x: crypto_data[x].get("rank", 999))
        except:
            sorted_coins = crypto_keys

        total_pages = (len(sorted_coins) // 10) + (1 if len(sorted_coins) % 10 > 0 else 0)

        # Вычисляем индексы для текущей страницы
        start_index = (page - 1) * 10
        end_index = min(start_index + 10, len(sorted_coins))

        # Создаем сообщение с криптовалютами для текущей страницы
        message_text = f"💰 *Криптовалюты (страница {page} из {total_pages})* 💰\n_(обновлено: {crypto_data['last_updated']})_\n\n"

        message_text += print_coins(crypto_data, sorted_coins[start_index:end_index])

        # Создаем новую клавиатуру для пагинации
        pagination_keyboard = create_pagination_keyboard(page, total_pages)

        # Обновляем сообщение
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=pagination_keyboard
        )

    # Обработка обновления информации о монете
    elif data.startswith('refresh_'):
        symbol = data.split('_')[1]

        # Обновляем данные принудительно
        crypto_data = parse_crypto_prices()

        coin_message = get_coin_info(crypto_data, symbol)

        # Создаем инлайн-клавиатуру для действий с монетой
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")
        keyboard.add(btn_refresh)

        # Обновляем сообщение
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=coin_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    # Обработка добавления в избранное
    elif data.startswith('fav_'):
        symbol = data.split('_')[1]
        user_id = call.from_user.id

        result = db.add_favorite_crypto(user_id, symbol)

        if result:
            bot.answer_callback_query(
                callback_query_id=call.id,
                text=f"{symbol} добавлен в избранное!",
                show_alert=False
            )
        else:
            bot.answer_callback_query(
                callback_query_id=call.id,
                text=f"{symbol} уже в избранном",
                show_alert=False
            )

        # Обновляем сообщение с новой кнопкой "Удалить из избранного"
        crypto_data = read_crypto_prices()
        coin_message = get_coin_info(crypto_data, symbol)

        # Создаем обновленную клавиатуру
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")
        btn_unfavorite = types.InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"unfav_{symbol}")
        keyboard.add(btn_refresh, btn_unfavorite)

        # Обновляем сообщение
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=coin_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    # Обработка удаления из избранного
    elif data.startswith('unfav_'):
        symbol = data.split('_')[1]
        user_id = call.from_user.id

        result = db.remove_favorite_crypto(user_id, symbol)

        if result:
            bot.answer_callback_query(
                callback_query_id=call.id,
                text=f"{symbol} удален из избранного",
                show_alert=False
            )
        else:
            bot.answer_callback_query(
                callback_query_id=call.id,
                text=f"{symbol} не был в избранном",
                show_alert=False
            )

        # Обновляем сообщение с новой кнопкой "Добавить в избранное"
        crypto_data = read_crypto_prices()
        coin_message = get_coin_info(crypto_data, symbol)

        # Создаем обновленную клавиатуру
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        btn_refresh = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")
        btn_favorite = types.InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"fav_{symbol}")
        keyboard.add(btn_refresh, btn_favorite)

        # Обновляем сообщение
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=coin_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    # Отмечаем callback как обработанный
    bot.answer_callback_query(call.id)


if __name__ == "__main__":
    # Запускаем поток для периодического парсинга цен
    parsing_thread = threading.Thread(target=scheduled_parsing)
    parsing_thread.daemon = True  # Поток завершится при завершении основной программы
    parsing_thread.start()

    logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    try:
        # Запускаем бота
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Ошибка в работе бота: {e}")
