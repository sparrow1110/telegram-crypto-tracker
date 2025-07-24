import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from user_service.app import app, DatabaseManager
from user_service.models import Base
from dotenv import load_dotenv

load_dotenv()

# Устанавливаем REDIS_HOST для тестов
os.environ['REDIS_HOST'] = '172.21.18.121'
os.environ['REDIS_PORT'] = '6379'


@pytest.fixture(scope='module')
async def async_engine():
    # Используем SQLite в памяти для тестов
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope='module')
async def async_session(async_engine):
    AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield AsyncSessionLocal
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope='module')
def client(async_engine, async_session):
    # Переопределяем DatabaseManager для тестов
    app.dependency_overrides[DatabaseManager] = lambda: DatabaseManager(async_engine, async_session)
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
