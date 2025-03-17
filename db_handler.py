import psycopg2
import logging
from datetime import datetime, timedelta
from config import DB_CONFIG

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, config=DB_CONFIG):
        self.config = config
        self.conn = None
        self.cursor = None

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.conn = psycopg2.connect(**self.config)
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            logger.info("Успешное подключение к PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            return False

    def disconnect(self):
        """Закрытие соединения с базой данных"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
                logger.info("Соединение с PostgreSQL закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения: {e}")

    def create_tables(self):
        """Создание необходимых таблиц в базе данных"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            # Создаем таблицу для пользователей
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT FALSE
                )
            """)

            # Создаем таблицу для отслеживания избранных криптовалют пользователей
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_favorites (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    crypto_symbol VARCHAR(20) NOT NULL,
                    added_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, crypto_symbol)
                )
            """)

            # Создаем таблицу для отслеживания статистики использования
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    command VARCHAR(100) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            logger.info("Таблицы успешно созданы или уже существуют")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            return False

    def register_user(self, user_id, username=None, first_name=None, last_name=None):
        """Регистрация нового пользователя или обновление существующего"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            # Проверяем существует ли пользователь
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            user_exists = self.cursor.fetchone()

            if not user_exists:
                # Вставляем нового пользователя
                self.cursor.execute(
                    "INSERT INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s)",
                    (user_id, username, first_name, last_name)
                )
                logger.info(f"Новый пользователь зарегистрирован: {user_id}")
            else:
                # Обновляем информацию о существующем пользователе
                self.cursor.execute(
                    "UPDATE users SET username = %s, first_name = %s, last_name = %s, last_activity = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (username, first_name, last_name, user_id)
                )
                logger.info(f"Информация о пользователе обновлена: {user_id}")

            return True
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {e}")
            return False

    def update_user_activity(self, user_id):
        """Обновление времени последней активности пользователя"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute(
                "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = %s",
                (user_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении активности пользователя: {e}")
            return False

    def log_command(self, user_id, command):
        """Логирование команды пользователя"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute(
                "INSERT INTO usage_stats (user_id, command) VALUES (%s, %s)",
                (user_id, command)
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при логировании команды: {e}")
            return False

    def add_favorite_crypto(self, user_id, crypto_symbol):
        """Добавление криптовалюты в избранное пользователя"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            # Используем ON CONFLICT для обработки дубликатов
            self.cursor.execute(
                """
                INSERT INTO user_favorites (user_id, crypto_symbol) 
                VALUES (%s, %s) 
                ON CONFLICT (user_id, crypto_symbol) 
                DO NOTHING
                """,
                (user_id, crypto_symbol.upper())
            )

            # Проверяем, была ли вставка
            if self.cursor.rowcount > 0:
                logger.info(f"Добавлена криптовалюта {crypto_symbol} в избранное для пользователя {user_id}")
                return True
            else:
                logger.info(f"Криптовалюта {crypto_symbol} уже в избранном у пользователя {user_id}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при добавлении в избранное: {e}")
            return False

    def remove_favorite_crypto(self, user_id, crypto_symbol):
        """Удаление криптовалюты из избранного пользователя"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute(
                "DELETE FROM user_favorites WHERE user_id = %s AND crypto_symbol = %s",
                (user_id, crypto_symbol.upper())
            )

            if self.cursor.rowcount > 0:
                logger.info(f"Удалена криптовалюта {crypto_symbol} из избранного для пользователя {user_id}")
                return True
            else:
                logger.info(f"Криптовалюты {crypto_symbol} не было в избранном у пользователя {user_id}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при удалении из избранного: {e}")
            return False

    def get_favorite_cryptos(self, user_id):
        """Получение списка избранных криптовалют пользователя"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute(
                "SELECT crypto_symbol FROM user_favorites WHERE user_id = %s ORDER BY added_on",
                (user_id,)
            )

            favorites = [row[0] for row in self.cursor.fetchall()]
            return favorites
        except Exception as e:
            logger.error(f"Ошибка при получении избранных криптовалют: {e}")
            return []

    def get_user_count(self):
        """Получение общего количества пользователей"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("SELECT COUNT(*) FROM users")
            count = self.cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"Ошибка при подсчете пользователей: {e}")
            return 0

    def get_active_users(self, days=7):
        """Получение количества активных пользователей за указанный период (в днях)"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute(
                "SELECT COUNT(DISTINCT user_id) FROM users WHERE last_activity >= CURRENT_TIMESTAMP - INTERVAL '%s DAY'",
                (days,)
            )
            count = self.cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"Ошибка при подсчете активных пользователей: {e}")
            return 0

    def get_popular_cryptos(self, limit=5):
        """Получение самых популярных криптовалют среди всех пользователей"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute(
                """
                SELECT crypto_symbol, COUNT(*) as count 
                FROM user_favorites 
                GROUP BY crypto_symbol 
                ORDER BY count DESC 
                LIMIT %s
                """,
                (limit,)
            )

            popular = [(row[0], row[1]) for row in self.cursor.fetchall()]
            return popular
        except Exception as e:
            logger.error(f"Ошибка при получении популярных криптовалют: {e}")
            return []

    def get_popular_commands(self):
        """Получение самых популярных команд за последнюю неделю"""
        try:
            week_ago = datetime.now() - timedelta(days=7)
            self.cursor.execute(
                """
                SELECT command, COUNT(*) as count 
                FROM usage_stats 
                WHERE timestamp >= %s 
                GROUP BY command 
                ORDER BY count DESC 
                LIMIT 5
                """,
                (week_ago,)
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении популярных команд: {e}")
            return []

    def get_unblocked_users(self):
        """Получение списка незаблокированных пользователей"""
        try:
            query = "SELECT user_id FROM users WHERE is_blocked = FALSE OR is_blocked IS NULL"
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении незаблокированных пользователей: {e}")
            return []

    def get_blocked_users(self):
        """Получение количества заблокированных пользователей"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = TRUE")
            return self.cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка при получении количества заблокированных пользователей: {e}")
            return 0

    def get_user_exists(self, user_id):
        """Проверка существования пользователя"""
        try:
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при проверке существования пользователя: {e}")
            return None

    def block_user(self, user_id):
        """Блокировка пользователя"""
        try:
            self.cursor.execute(
                "UPDATE users SET is_blocked = TRUE WHERE user_id = %s",
                (user_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при блокировке пользователя: {e}")
            return False

    def unblock_user(self, user_id):
        """Разблокировка пользователя"""
        try:
            self.cursor.execute(
                "UPDATE users SET is_blocked = FALSE WHERE user_id = %s",
                (user_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при разблокировке пользователя: {e}")
            return False

    def get_count_favorite(self):
        """Получение количества избранных криптовалют"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM user_favorites")
            return self.cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка при получении количества избранных криптовалют: {e}")
            return 0

    def is_blocked(self, user_id):
        """Проверка, заблокирован ли пользователь"""
        try:
            self.cursor.execute(
                "SELECT is_blocked FROM users WHERE user_id = %s",
                (user_id,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при проверке блокировки пользователя: {e}")
            return None


# Пример использования
if __name__ == "__main__":
    db = DatabaseManager()
    if db.connect():
        db.create_tables()
        db.disconnect()
    else:
        logger.error("Не удалось подключиться к базе данных")
