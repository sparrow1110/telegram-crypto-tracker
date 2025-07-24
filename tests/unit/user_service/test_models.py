import pytest
from datetime import datetime
from user_service.models import User, UserFavorite, UsageStat
from sqlalchemy import select


@pytest.mark.asyncio
async def test_user_model(async_session):
    async with async_session() as session:
        async with session.begin():
            user = User(user_id=123, username='testuser', first_name='Test', last_name='User', is_blocked=False)
            session.add(user)
            await session.commit()

        user = (await session.execute(select(User).filter_by(user_id=123))).scalar_one()
        assert user.user_id == 123
        assert user.username == 'testuser'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.is_blocked is False
        assert isinstance(user.join_date, datetime)
        assert isinstance(user.last_activity, datetime)


@pytest.mark.asyncio
async def test_user_favorite_model(async_session):
    async with async_session() as session:
        async with session.begin():
            user = User(user_id=124, username='testuser2', first_name='Test2', last_name='User2')
            session.add(user)
            await session.commit()

        async with session.begin():
            favorite = UserFavorite(user_id=124, crypto_symbol='BTC')
            session.add(favorite)
            await session.commit()

        favorite = (await session.execute(select(UserFavorite).filter_by(user_id=124))).scalar_one()
        assert favorite.user_id == 124
        assert favorite.crypto_symbol == 'BTC'
        assert isinstance(favorite.added_on, datetime)


@pytest.mark.asyncio
async def test_usage_stat_model(async_session):
    async with async_session() as session:
        async with session.begin():
            user = User(user_id=125, username='testuser3', first_name='Test3', last_name='User3')
            session.add(user)
            await session.commit()

        async with session.begin():
            stat = UsageStat(user_id=125, command='/start')
            session.add(stat)
            await session.commit()

        stat = (await session.execute(select(UsageStat).filter_by(user_id=125))).scalar_one()
        assert stat.user_id == 125
        assert stat.command == '/start'
        assert isinstance(stat.timestamp, datetime)
