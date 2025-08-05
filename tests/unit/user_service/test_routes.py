import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from user_service.app import app, db_manager
from user_service.models import Base
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_manager.engine = engine
    db_manager.SessionLocal = AsyncSessionLocal
    yield
    await engine.dispose()


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.mark.asyncio
async def test_register_user_new(client):
    with patch('user_service.app.db_manager.register_user', new=AsyncMock(return_value=(True, True))), patch(
        'user_service.app.db_manager.is_blocked', new=AsyncMock(return_value=False)
    ):
        token = os.getenv("API_TOKEN", "your-secret-api-token")
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = client.post("/v1/users", json={"user_id": 123, "username": "testuser"}, headers=headers)
        assert response.status_code == 201
        assert response.json() == {
            "data": {"user_id": 123, "username": "testuser", "is_new": True},
            "status_code": 201,
            "errors": None,
            "meta": None,
        }


@pytest.mark.asyncio
async def test_register_user_existing(client):
    with patch('user_service.app.db_manager.register_user', new=AsyncMock(return_value=(True, False))), patch(
        'user_service.app.db_manager.is_blocked', new=AsyncMock(return_value=False)
    ):
        token = os.getenv("API_TOKEN", "your-secret-api-token")
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = client.post("/v1/users", json={"user_id": 123, "username": "testuser"}, headers=headers)
        assert response.status_code == 200
        assert response.json() == {
            "data": {"user_id": 123, "username": "testuser", "is_new": False},
            "status_code": 200,
            "errors": None,
            "meta": None,
        }


@pytest.mark.asyncio
async def test_log_command(client):
    with patch('user_service.db_handler.DatabaseManager.is_blocked', new=AsyncMock(return_value=False)):
        with patch('user_service.db_handler.DatabaseManager.log_command', new=AsyncMock(return_value=True)):
            token = os.getenv("API_TOKEN", "your-secret-api-token")
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            response = client.post(
                '/v1/command-logs',
                headers=headers,
                json={'user_id': 123, 'command': '/start', 'requester_id': 123},
            )
            assert response.status_code == 200
            assert response.json() == {
                'data': {'user_id': 123, 'command': '/start'},
                'errors': None,
                'meta': None,
                'status_code': 200,
            }


@pytest.mark.asyncio
async def test_add_favorite_crypto(client):
    with patch('user_service.db_handler.DatabaseManager.add_favorite_crypto', new=AsyncMock(return_value=True)):
        token = os.getenv("API_TOKEN", "your-secret-api-token")
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = client.post(
            '/v1/users/123/favorite-cryptos',
            headers=headers,
            json={'crypto_symbol': 'BTC', 'requester_id': 123},
        )
        assert response.status_code == 201
        assert response.json() == {
            'data': {'user_id': 123, 'crypto_symbol': 'BTC'},
            'errors': None,
            'meta': None,
            'status_code': 201,
        }


@pytest.mark.asyncio
async def test_get_stats(client):
    with patch('user_service.db_handler.DatabaseManager.get_stats', new=AsyncMock()) as mock_stats:
        mock_stats.return_value = {
            'user_count': 1,
            'active_users_24h': 0,
            'active_users_7d': 0,
            'blocked_count': 0,
            'favorites_count': 0,
            'popular_commands': [],
        }
        token = os.getenv("API_TOKEN", "your-secret-api-token")
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = client.get(
            '/v1/stats?requester_id=123',
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json() == {
            'data': {
                'user_count': 1,
                'active_users_24h': 0,
                'active_users_7d': 0,
                'blocked_count': 0,
                'favorites_count': 0,
                'popular_commands': [],
            },
            'errors': None,
            'meta': None,
            'status_code': 200,
        }
