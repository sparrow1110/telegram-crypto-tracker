import pytest
import os
from fastapi.testclient import TestClient
from admin_service.app import app, admin
from dotenv import load_dotenv
from unittest.mock import AsyncMock, patch

load_dotenv()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_is_admin_success(client):
    with patch('admin_service.app.verify_token', return_value=True):
        with patch.object(admin, 'is_admin', new=AsyncMock(return_value=True)):
            headers = {'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}'}
            response = client.get('/v1/admins/123/status', headers=headers)
            assert response.status_code == 200
            assert response.json() == {'data': {'is_admin': True}, 'errors': None, 'meta': None}


@pytest.mark.asyncio
async def test_is_admin_invalid_token(client):
    headers = {'Authorization': 'Bearer invalid-token'}
    response = client.get('/v1/admins/123/status', headers=headers)
    assert response.status_code == 401
    assert 'errors' in response.json()['detail']
    assert response.json()['detail']['errors'][0]['code'] == 'Unauthorized'


@pytest.mark.asyncio
async def test_is_admin_no_token(client):
    response = client.get('/v1/admins/123/status')
    assert response.status_code == 401
    assert 'errors' in response.json()['detail']
    assert response.json()['detail']['errors'][0]['code'] == 'Unauthorized'


@pytest.mark.asyncio
async def test_get_stats_success(client):
    with patch('admin_service.app.verify_token', return_value=True):
        with patch('admin_service.app.check_admin', new=AsyncMock(return_value=True)):
            with patch.object(admin, 'get_bot_stats', new=AsyncMock(return_value='📊 Статистика бота...')):
                headers = {
                    'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
                    'Content-Type': 'application/json',
                }
                response = client.get('/v1/stats?requester_id=123', headers=headers)
                assert response.status_code == 200
                assert response.json() == {'data': {'stats': '📊 Статистика бота...'}, 'errors': None, 'meta': None}


@pytest.mark.asyncio
async def test_block_user_success(client):
    with patch('admin_service.app.verify_token', return_value=True):
        with patch('admin_service.app.check_admin', new=AsyncMock(return_value=True)):
            with patch.object(admin, 'block_user', new=AsyncMock(return_value=True)):
                headers = {
                    'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
                    'Content-Type': 'application/json',
                }
                response = client.post('/v1/users/123/block', headers=headers, json={'requester_id': 123})
                assert response.status_code == 200
                assert response.json() == {
                    'data': {'user_id': 123, 'is_blocked': True, 'action': 'admin_blocked'},
                    'errors': None,
                    'meta': None,
                }


@pytest.mark.asyncio
async def test_not_found_handler(client):
    response = client.get('/nonexistent-route')
    assert response.status_code == 404
    assert response.json() == {'detail': 'Not Found'}
