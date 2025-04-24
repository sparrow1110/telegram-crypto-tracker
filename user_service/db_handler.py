from user_service.models import db, User, UserFavorite, UsageStat
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    def register_user(self, user_id, username=None, first_name=None, last_name=None):
        try:
            user = User.query.get(user_id)
            is_new = False

            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    last_activity=datetime.utcnow()
                )
                db.session.add(user)
                is_new = True
                logger.info(f"New user registered: {user_id}")
            else:
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.last_activity = datetime.utcnow()
                logger.info(f"User info updated: {user_id}")

            db.session.commit()
            return True, is_new  # Возвращаем и статус, и флаг создания

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error registering user: {e}")
            return False, False

    def log_command(self, user_id, command):
        try:
            stat = UsageStat(user_id=user_id, command=command)
            db.session.add(stat)
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error logging command: {e}")
            return False

    def add_favorite_crypto(self, user_id, crypto_symbol):
        try:
            user_exists = User.query.get(user_id) is not None
            if not user_exists:
                return None  # Возвращаем None, если пользователь не найден
            # Check if already exists
            exists = UserFavorite.query.filter_by(
                user_id=user_id,
                crypto_symbol=crypto_symbol.upper()
            ).first()

            if exists:
                logger.info(f"Crypto {crypto_symbol} already in favorites for user {user_id}")
                return False

            favorite = UserFavorite(
                user_id=user_id,
                crypto_symbol=crypto_symbol.upper()
            )
            db.session.add(favorite)
            db.session.commit()
            logger.info(f"Added {crypto_symbol} to favorites for user {user_id}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error adding favorite: {e}")
            return False

    def remove_favorite_crypto(self, user_id, crypto_symbol):
        try:
            deleted = UserFavorite.query.filter_by(
                user_id=user_id,
                crypto_symbol=crypto_symbol.upper()
            ).delete()

            db.session.commit()
            if deleted:
                logger.info(f"Removed {crypto_symbol} from favorites for user {user_id}")
                return True
            logger.info(f"Crypto {crypto_symbol} not in favorites for user {user_id}")
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error removing favorite: {e}")
            raise

    def get_favorite_cryptos(self, user_id):
        try:
            user_exists = User.query.get(user_id) is not None
            if not user_exists:
                return None  # Возвращаем None, если пользователь не найден

            favorites = UserFavorite.query.filter_by(user_id=user_id).order_by(UserFavorite.added_on).all()
            return [fav.crypto_symbol for fav in favorites]
        except SQLAlchemyError as e:
            logger.error(f"Error getting favorites: {e}")
            raise  # Передаем исключение дальше, чтобы оно было обработано в маршруте

    def get_user_count(self):
        try:
            return User.query.count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting users: {e}")
            return 0

    def get_active_users(self, days=7):
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            return User.query.filter(User.last_activity >= cutoff).count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting active users: {e}")
            return 0

    def get_popular_cryptos(self, limit=5):
        try:
            result = db.session.query(
                UserFavorite.crypto_symbol,
                db.func.count(UserFavorite.crypto_symbol).label('count')
            ).group_by(UserFavorite.crypto_symbol).order_by(db.desc('count')).limit(limit).all()

            return [(row.crypto_symbol, row.count) for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Error getting popular cryptos: {e}")
            raise

    def get_popular_commands(self):
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            result = db.session.query(
                UsageStat.command,
                db.func.count(UsageStat.command).label('count')
            ).filter(UsageStat.timestamp >= week_ago).group_by(UsageStat.command).order_by(db.desc('count')).limit(
                5).all()

            return [(row.command, row.count) for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Error getting popular commands: {e}")
            return []

    def get_unblocked_users(self):
        try:
            users = User.query.filter(User.is_blocked is False).all()
            return [user.user_id for user in users]
        except SQLAlchemyError as e:
            logger.error(f"Error getting unblocked users: {e}")
            return []

    def get_blocked_users_count(self):
        try:
            return User.query.filter(User.is_blocked is True).count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting blocked users: {e}")
            return 0

    def get_user_exists(self, user_id):
        try:
            return User.query.get(user_id) is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking user existence: {e}")
            return False

    def block_user(self, user_id):
        try:
            user = User.query.get(user_id)
            if user:
                user.is_blocked = True
                db.session.commit()
                logger.info(f"User {user_id} blocked")
                return True
            logger.warning(f"User {user_id} not found for blocking")
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error blocking user {user_id}: {e}")
            raise

    def unblock_user(self, user_id):
        try:
            user = User.query.get(user_id)
            if user:
                user.is_blocked = False
                db.session.commit()
                logger.info(f"User {user_id} unblocked")
                return True
            logger.warning(f"User {user_id} not found for unblocking")
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error unblocking user {user_id}: {e}")
            raise

    def get_count_favorite(self):
        try:
            return UserFavorite.query.count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting favorites: {e}")
            return 0

    def is_blocked(self, user_id):
        try:
            user = User.query.get(user_id)
            return user.is_blocked if user else None
        except SQLAlchemyError as e:
            logger.error(f"Error checking user block status: {e}")
            raise
