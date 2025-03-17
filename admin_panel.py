from telebot import types
import logging
from datetime import datetime
from db_handler import DatabaseManager
from config import ADMIN_IDS
from functools import lru_cache

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AdminPanel:
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.broadcast_mode = {}  # Словарь для отслеживания режима рассылки
        self.block_mode = {}  # Словарь для отслеживания режима блокировки

    def is_admin(self, user_id):
        """Проверка, является ли пользователь администратором"""
        return user_id in ADMIN_IDS

    @lru_cache(maxsize=10)
    def create_admin_keyboard(self):
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

    def handle_admin_command(self, message):
        """Обработка команды /admin"""
        user_id = message.from_user.id

        if not self.is_admin(user_id):
            self.bot.send_message(user_id, "У вас нет доступа к админ-панели.")
            return False

        keyboard = self.create_admin_keyboard()
        self.bot.send_message(user_id,
                              "👨‍💻 *Админ-панель криптобота* 👨‍💻\n\n"
                              "Выберите действие из меню ниже:",
                              parse_mode='Markdown',
                              reply_markup=keyboard)
        return True

    def handle_admin_message(self, message):
        """Обработка сообщений в режиме админ-панели"""
        user_id = message.from_user.id
        text = message.text

        if not self.is_admin(user_id):
            return False

        # Проверка режима рассылки
        if user_id in self.broadcast_mode and self.broadcast_mode[user_id]:
            if text == 'Отмена':
                self.broadcast_mode[user_id] = False
                keyboard = self.create_admin_keyboard()
                self.bot.send_message(user_id, "Рассылка отменена.", reply_markup=keyboard)
            else:
                self.bot.send_message(user_id, "⏳ Начинаю рассылку сообщения всем пользователям...")
                sent_count, failed_count = self.broadcast_message(text)

                self.broadcast_mode[user_id] = False
                keyboard = self.create_admin_keyboard()

                result_message = f"✅ Рассылка завершена!\n\n"
                result_message += f"📤 Отправлено: {sent_count}\n"
                result_message += f"❌ Не доставлено: {failed_count}"

                self.bot.send_message(user_id, result_message, reply_markup=keyboard)
            return True

        # Проверка режима блокировки пользователя
        if user_id in self.block_mode and self.block_mode[user_id]:
            if text == 'Отмена':
                self.block_mode[user_id] = False
                keyboard = self.create_admin_keyboard()
                self.bot.send_message(user_id, "Операция отменена.", reply_markup=keyboard)
            else:
                try:
                    target_user_id = int(text)
                    action = self.block_mode[user_id]

                    if action == "block":
                        success = self.block_user(target_user_id)
                        if success:
                            self.bot.send_message(user_id, f"✅ Пользователь {target_user_id} заблокирован.")
                        else:
                            self.bot.send_message(user_id, f"❌ Не удалось заблокировать пользователя {target_user_id}.")
                    elif action == "unblock":
                        success = self.unblock_user(target_user_id)
                        if success:
                            self.bot.send_message(user_id, f"✅ Пользователь {target_user_id} разблокирован.")
                        else:
                            self.bot.send_message(user_id,
                                                  f"❌ Не удалось разблокировать пользователя {target_user_id}.")

                except ValueError:
                    self.bot.send_message(user_id, "❌ Неверный формат ID пользователя. Введите числовой ID.")

                self.block_mode[user_id] = False
                keyboard = self.create_admin_keyboard()
                self.bot.send_message(user_id, "Вернулись в главное меню админ-панели.", reply_markup=keyboard)
            return True

        # Обработка основных команд админ-панели
        if text == '📣 Рассылка сообщений':
            self.broadcast_mode[user_id] = True

            # Создаем клавиатуру с кнопкой отмены
            keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            btn_cancel = types.KeyboardButton('Отмена')
            keyboard.add(btn_cancel)

            self.bot.send_message(user_id,
                                  "📣 *Режим рассылки сообщений*\n\n"
                                  "Введите текст сообщения, которое нужно разослать всем пользователям.\n"
                                  "Поддерживается форматирование *Markdown*.\n\n"
                                  "Для отмены рассылки нажмите кнопку 'Отмена'.",
                                  parse_mode='Markdown',
                                  reply_markup=keyboard)
            return True

        elif text == '🚫 Заблокировать пользователя':
            self.block_mode[user_id] = "block"

            # Создаем клавиатуру с кнопкой отмены
            keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            btn_cancel = types.KeyboardButton('Отмена')
            keyboard.add(btn_cancel)

            self.bot.send_message(user_id,
                                  "🚫 *Блокировка пользователя*\n\n"
                                  "Введите ID пользователя, которого нужно заблокировать.\n\n"
                                  "Для отмены операции нажмите кнопку 'Отмена'.",
                                  parse_mode='Markdown',
                                  reply_markup=keyboard)
            return True

        elif text == '✅ Разблокировать пользователя':
            self.block_mode[user_id] = "unblock"

            # Создаем клавиатуру с кнопкой отмены
            keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            btn_cancel = types.KeyboardButton('Отмена')
            keyboard.add(btn_cancel)

            self.bot.send_message(user_id,
                                  "✅ *Разблокировка пользователя*\n\n"
                                  "Введите ID пользователя, которого нужно разблокировать.\n\n"
                                  "Для отмены операции нажмите кнопку 'Отмена'.",
                                  parse_mode='Markdown',
                                  reply_markup=keyboard)
            return True

        elif text == '📊 Статистика бота':
            stats = self.get_bot_stats()
            self.bot.send_message(user_id, stats, parse_mode='Markdown')
            return True

        elif text == '🔝 Популярные криптовалюты':
            popular = self.get_popular_cryptos()
            self.bot.send_message(user_id, popular, parse_mode='Markdown')
            return True

        elif text == '🔙 Выход из админ-панели':
            from main import create_main_keyboard  # Импортируем функцию из основного модуля
            keyboard = create_main_keyboard(message.from_user.id)
            self.bot.send_message(user_id, "Вы вышли из режима администратора.", reply_markup=keyboard)
            return True

        return False

    def broadcast_message(self, message_text):
        """Отправка сообщения всем пользователям"""
        try:
            if not self.db.conn or self.db.conn.closed:
                self.db.connect()

            # Получаем список всех незаблокированных пользователей
            users = self.db.get_unblocked_users()

            sent_count = 0
            failed_count = 0

            for user in users:
                user_id = user[0]
                try:
                    self.bot.send_message(user_id, message_text, parse_mode='Markdown')
                    sent_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

            return sent_count, failed_count
        except Exception as e:
            logger.error(f"Ошибка при рассылке: {e}")
            return 0, 0

    def block_user(self, user_id):
        """Блокировка пользователя"""
        try:
            if not self.db.conn or self.db.conn.closed:
                self.db.connect()

            # Проверяем, существует ли пользователь
            user_exists = self.db.get_user_exists(user_id)

            if not user_exists:
                logger.warning(f"Попытка заблокировать несуществующего пользователя: {user_id}")
                return False

            # Блокируем пользователя
            self.db.block_user(user_id)

            logger.info(f"Пользователь {user_id} заблокирован")
            return True
        except Exception as e:
            logger.error(f"Ошибка при блокировке пользователя {user_id}: {e}")
            return False

    def unblock_user(self, user_id):
        """Разблокировка пользователя"""
        try:
            if not self.db.conn or self.db.conn.closed:
                self.db.connect()

            # Проверяем, существует ли пользователь
            user_exists = self.db.get_user_exists(user_id)

            if not user_exists:
                logger.warning(f"Попытка разблокировать несуществующего пользователя: {user_id}")
                return False

            # Разблокируем пользователя
            self.db.unblock_user(user_id)

            logger.info(f"Пользователь {user_id} разблокирован")
            return True
        except Exception as e:
            logger.error(f"Ошибка при разблокировке пользователя {user_id}: {e}")
            return False

    def get_bot_stats(self):
        """Получение статистики бота"""
        try:
            if not self.db.conn or self.db.conn.closed:
                self.db.connect()

            # Общее количество пользователей
            total_users = self.db.get_user_count()

            # Активные пользователи за 24 часа
            active_24h = self.db.get_active_users(1)

            # Активные пользователи за 7 дней
            active_7d = self.db.get_active_users()

            # Заблокированные пользователи
            blocked_users = self.db.get_blocked_users()

            # Количество криптовалют в избранном
            favorites_count = self.db.get_count_favorite()

            stats = f"📊 *Статистика бота*\n\n"
            stats += f"👥 *Пользователи:*\n"
            stats += f"• Всего пользователей: {total_users}\n"
            stats += f"• Активных за 24 часа: {active_24h}\n"
            stats += f"• Активных за 7 дней: {active_7d}\n"
            stats += f"• Заблокированных: {blocked_users}\n\n"
            stats += f"⭐ *Избранное:*\n"
            stats += f"• Всего добавлено в избранное: {favorites_count}\n"

            # Получаем статистику по командам за последние 7 дней
            commands = self.db.get_popular_commands()

            if commands:
                stats += f"\n🔄 *Популярные команды (7 дней):*\n"
                for cmd, count in commands:
                    stats += f"• {cmd}: {count} раз\n"

            stats += f"\n🕒 *Актуально на:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            return stats

        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return "Ошибка при получении статистики. Попробуйте позже."

    def get_popular_cryptos(self):
        """Получение списка популярных криптовалют"""
        try:
            popular_cryptos = self.db.get_popular_cryptos(10)

            if not popular_cryptos:
                return "Нет данных о популярных криптовалютах."

            result = f"🔝 *Популярные криптовалюты*\n\n"

            for i, (symbol, count) in enumerate(popular_cryptos, 1):
                result += f"{i}. *{symbol}* - {count} пользователей\n"

            result += f"\n🕒 *Актуально на:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            return result
        except Exception as e:
            logger.error(f"Ошибка при получении популярных криптовалют: {e}")
            return "Ошибка при получении данных. Попробуйте позже."

    def is_user_blocked(self, user_id):
        """Проверка, заблокирован ли пользователь"""
        try:
            if not self.db.conn or self.db.conn.closed:
                self.db.connect()

            result = self.db.is_blocked(user_id)

            if result and result[0]:
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке блокировки пользователя {user_id}: {e}")
            return False
