import pytest
from user_service.db_handler import DatabaseManager
from user_service.models import User, UserFavorite, UsageStat


@pytest.mark.asyncio
async def test_register_user_new(async_session):
    db_manager = DatabaseManager(None, async_session)
    success, is_new = await db_manager.register_user(123, 'testuser', 'Test', 'User')

    assert success is True
    assert is_new is True

    async with async_session() as session:
        user = await session.get(User, 123)
        assert user is not None
        assert user.username == 'testuser'


@pytest.mark.asyncio
async def test_register_user_existing(async_session):
    db_manager = DatabaseManager(None, async_session)
    await db_manager.register_user(123, 'testuser', 'Test', 'User')

    success, is_new = await db_manager.register_user(123, 'updateduser', 'Updated', 'User')

    assert success is True
    assert is_new is False

    async with async_session() as session:
        user = await session.get(User, 123)
        assert user.username == 'updateduser'


@pytest.mark.asyncio
async def test_log_command(async_session):
    db_manager = DatabaseManager(None, async_session)
    await db_manager.register_user(123, 'testuser', 'Test', 'User')

    success = await db_manager.log_command(123, '/start')
    assert success is True

    async with async_session() as session:
        from sqlalchemy import select

        stats = (await session.execute(select(UsageStat).filter_by(user_id=123))).scalars().all()
        assert len(stats) == 1
        assert stats[0].command == '/start'


@pytest.mark.asyncio
async def test_add_favorite_crypto(async_session):
    db_manager = DatabaseManager(None, async_session)
    await db_manager.register_user(123, 'testuser', 'Test', 'User')

    success = await db_manager.add_favorite_crypto(123, 'BTC')
    assert success is True

    async with async_session() as session:
        from sqlalchemy import select

        favorites = (await session.execute(select(UserFavorite).filter_by(user_id=123))).scalars().all()
        assert len(favorites) == 1
        assert favorites[0].crypto_symbol == 'BTC'


@pytest.mark.asyncio
async def test_remove_favorite_crypto(async_session):
    db_manager = DatabaseManager(None, async_session)
    await db_manager.register_user(123, 'testuser', 'Test', 'User')
    await db_manager.add_favorite_crypto(123, 'BTC')

    success = await db_manager.remove_favorite_crypto(123, 'BTC')
    assert success is True

    async with async_session() as session:
        from sqlalchemy import select

        favorites = (await session.execute(select(UserFavorite).filter_by(user_id=123))).scalars().all()
        assert len(favorites) == 0


@pytest.mark.asyncio
async def test_get_favorite_cryptos(async_session):
    db_manager = DatabaseManager(None, async_session)
    await db_manager.register_user(123, 'testuser', 'Test', 'User')
    await db_manager.add_favorite_crypto(123, 'BTC')
    await db_manager.add_favorite_crypto(123, 'ETH')

    favorites = await db_manager.get_favorite_cryptos(123)
    assert len(favorites) == 2
    assert 'BTC' in favorites
    assert 'ETH' in favorites


@pytest.mark.asyncio
async def test_block_unblock_user(async_session):
    db_manager = DatabaseManager(None, async_session)
    await db_manager.register_user(123, 'testuser', 'Test', 'User')

    success = await db_manager.block_user(123)
    assert success is True
    assert await db_manager.is_blocked(123) is True

    success = await db_manager.unblock_user(123)
    assert success is True
    assert await db_manager.is_blocked(123) is False
