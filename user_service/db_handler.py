from sqlalchemy.future import select
from sqlalchemy import func, delete
from user_service.models import User, UserFavorite, UsageStat
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, engine, sessionmaker):
        self.engine = engine
        self.sessionmaker = sessionmaker

    async def register_user(
        self, user_id: int, username: str = None, first_name: str = None, last_name: str = None
    ) -> tuple[bool, bool]:
        async with self.sessionmaker() as session:
            try:
                user = (await session.execute(select(User).filter_by(user_id=user_id))).scalar_one_or_none()
                is_new = False

                if not user:
                    user = User(
                        user_id=user_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        last_activity=datetime.utcnow(),
                    )
                    session.add(user)
                    is_new = True
                    logger.info(f"New user registered: {user_id}")
                else:
                    user.username = username
                    user.first_name = first_name
                    user.last_name = last_name
                    user.last_activity = datetime.utcnow()
                    logger.info(f"User info updated: {user_id}")

                await session.commit()
                return True, is_new
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error registering user: {e}")
                return False, False

    async def log_command(self, user_id: int, command: str) -> bool:
        async with self.sessionmaker() as session:
            try:
                stat = UsageStat(user_id=user_id, command=command)
                session.add(stat)
                await session.commit()
                return True
            except SQLAlchemyError as e:
                logger.error(f"Error logging command: {e}")
                return False

    async def add_favorite_crypto(self, user_id: int, crypto_symbol: str) -> bool:
        async with self.sessionmaker() as session:
            try:
                user_exists = (await session.execute(select(User).filter_by(user_id=user_id))).scalar_one_or_none()
                if not user_exists:
                    return None
                exists = (
                    await session.execute(
                        select(UserFavorite).filter_by(user_id=user_id, crypto_symbol=crypto_symbol.upper())
                    )
                ).scalar_one_or_none()

                if exists:
                    logger.info(f"Crypto {crypto_symbol} already in favorites for user {user_id}")
                    return False

                favorite = UserFavorite(user_id=user_id, crypto_symbol=crypto_symbol.upper())
                session.add(favorite)
                await session.commit()
                logger.info(f"Added {crypto_symbol} to favorites for user {user_id}")
                return True
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error adding favorite: {e}")
                return False

    async def remove_favorite_crypto(self, user_id: int, crypto_symbol: str) -> bool:
        async with self.sessionmaker() as session:
            try:
                deleted = await session.execute(
                    delete(UserFavorite).where(
                        UserFavorite.user_id == user_id, UserFavorite.crypto_symbol == crypto_symbol.upper()
                    )
                )
                await session.commit()
                if deleted.rowcount:
                    logger.info(f"Removed {crypto_symbol} from favorites for user {user_id}")
                    return True
                logger.info(f"Crypto {crypto_symbol} not in favorites for user {user_id}")
                return False
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error removing favorite: {e}")
                raise

    async def get_favorite_cryptos(self, user_id: int) -> list:
        async with self.sessionmaker() as session:
            try:
                user_exists = (await session.execute(select(User).filter_by(user_id=user_id))).scalar_one_or_none()
                if not user_exists:
                    return None
                favorites = (
                    (
                        await session.execute(
                            select(UserFavorite).filter_by(user_id=user_id).order_by(UserFavorite.added_on)
                        )
                    )
                    .scalars()
                    .all()
                )
                return [fav.crypto_symbol for fav in favorites]
            except SQLAlchemyError as e:
                logger.error(f"Error getting favorites: {e}")
                raise

    async def get_user_count(self) -> int:
        async with self.sessionmaker() as session:
            try:
                result = await session.execute(select(func.count()).select_from(User))
                return result.scalar()
            except SQLAlchemyError as e:
                logger.error(f"Error counting users: {e}")
                return 0

    async def get_active_users(self, days: int = 7) -> int:
        async with self.sessionmaker() as session:
            try:
                cutoff = datetime.utcnow() - timedelta(days=days)
                result = await session.execute(
                    select(func.count()).select_from(User).filter(User.last_activity >= cutoff)
                )
                return result.scalar()
            except SQLAlchemyError as e:
                logger.error(f"Error counting active users: {e}")
                return 0

    async def get_popular_cryptos(self, limit: int = 5) -> list:
        async with self.sessionmaker() as session:
            try:
                result = (
                    await session.execute(
                        select(UserFavorite.crypto_symbol, func.count(UserFavorite.crypto_symbol).label('count'))
                        .group_by(UserFavorite.crypto_symbol)
                        .order_by(func.count(UserFavorite.crypto_symbol).desc())
                        .limit(limit)
                    )
                ).all()
                return [(row.crypto_symbol, row.count) for row in result]
            except SQLAlchemyError as e:
                logger.error(f"Error getting popular cryptos: {e}")
                raise

    async def get_popular_commands(self) -> list:
        async with self.sessionmaker() as session:
            try:
                week_ago = datetime.utcnow() - timedelta(days=7)
                result = (
                    await session.execute(
                        select(UsageStat.command, func.count(UsageStat.command).label('count'))
                        .filter(UsageStat.timestamp >= week_ago)
                        .group_by(UsageStat.command)
                        .order_by(func.count(UsageStat.command).desc())
                        .limit(5)
                    )
                ).all()
                return [(row.command, row.count) for row in result]
            except SQLAlchemyError as e:
                logger.error(f"Error getting popular commands: {e}")
                return []

    async def get_unblocked_users(self) -> list:
        async with self.sessionmaker() as session:
            try:
                users = (await session.execute(select(User).filter(User.is_blocked == False))).scalars().all()
                return [user.user_id for user in users]
            except SQLAlchemyError as e:
                logger.error(f"Error getting unblocked users: {e}")
                return []

    async def get_blocked_users_count(self) -> int:
        async with self.sessionmaker() as session:
            try:
                result = await session.execute(select(func.count()).select_from(User).filter(User.is_blocked == True))
                return result.scalar()
            except SQLAlchemyError as e:
                logger.error(f"Error counting blocked users: {e}")
                return 0

    async def get_user_exists(self, user_id: int) -> bool:
        async with self.sessionmaker() as session:
            try:
                user = (await session.execute(select(User).filter_by(user_id=user_id))).scalar_one_or_none()
                return user is not None
            except SQLAlchemyError as e:
                logger.error(f"Error checking user existence: {e}")
                return False

    async def block_user(self, user_id: int) -> bool:
        async with self.sessionmaker() as session:
            try:
                user = (await session.execute(select(User).filter_by(user_id=user_id))).scalar_one_or_none()
                if user:
                    user.is_blocked = True
                    await session.commit()
                    logger.info(f"User {user_id} blocked")
                    return True
                logger.warning(f"User {user_id} not found for blocking")
                return False
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error blocking user {user_id}: {e}")
                raise

    async def unblock_user(self, user_id: int) -> bool:
        async with self.sessionmaker() as session:
            try:
                user = (await session.execute(select(User).filter_by(user_id=user_id))).scalar_one_or_none()
                if user:
                    user.is_blocked = False
                    await session.commit()
                    logger.info(f"User {user_id} unblocked")
                    return True
                logger.warning(f"User {user_id} not found for unblocking")
                return False
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error unblocking user {user_id}: {e}")
                raise

    async def get_count_favorite(self) -> int:
        async with self.sessionmaker() as session:
            try:
                result = await session.execute(select(func.count()).select_from(UserFavorite))
                return result.scalar()
            except SQLAlchemyError as e:
                logger.error(f"Error counting favorites: {e}")
                return 0

    async def is_blocked(self, user_id: int) -> bool:
        async with self.sessionmaker() as session:
            try:
                user = (await session.execute(select(User).filter_by(user_id=user_id))).scalar_one_or_none()
                return user.is_blocked if user else None
            except SQLAlchemyError as e:
                logger.error(f"Error checking user block status: {e}")
                raise

    async def get_stats(self) -> dict:
        async with self.sessionmaker() as session:
            try:
                user_count = await self.get_user_count()
                active_users_24h = await self.get_active_users(1)
                active_users_7d = await self.get_active_users(7)
                blocked_count = await self.get_blocked_users_count()
                favorites_count = await self.get_count_favorite()
                popular_commands = await self.get_popular_commands()
                return {
                    'user_count': user_count,
                    'active_users_24h': active_users_24h,
                    'active_users_7d': active_users_7d,
                    'blocked_count': blocked_count,
                    'favorites_count': favorites_count,
                    'popular_commands': popular_commands,
                }
            except SQLAlchemyError as e:
                logger.error(f"Error getting stats: {e}")
                raise
