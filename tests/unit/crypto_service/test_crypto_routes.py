import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from crypto_service.app import app
from crypto_service.price_cache import crypto_cache


@pytest.fixture
def client():
    with patch('crypto_service.app.scheduled_parsing', new=AsyncMock()):
        yield TestClient(app)


@pytest.fixture(autouse=True)
def clear_cache():
    crypto_cache.clear()
    yield


@pytest.mark.asyncio
async def test_get_prices_success(client):
    test_data = {
        "last_updated": "2025-07-24 01:23:06",
        "BTC": {
            "name": "Bitcoin",
            "price_usd": 50000.00,
            "percent_change_1h": 0.5,
            "percent_change_24h": 2.5,
            "percent_change_7d": 10.0,
            "market_cap_usd": 1000000000000,
            "rank": 1,
        },
    }
    with patch('crypto_service.crypto_parser.CryptoParser.get_crypto_prices', new=AsyncMock(return_value=test_data)):
        response = client.get('/v1/crypto-prices')
        assert response.status_code == 200
        assert response.json() == {"data": test_data, "errors": None, "meta": None}


@pytest.mark.asyncio
async def test_get_prices_error(client):
    with patch(
        'crypto_service.crypto_parser.CryptoParser.get_crypto_prices',
        new=AsyncMock(side_effect=ValueError("Service error")),
    ):
        response = client.get('/v1/crypto-prices')
        assert response.status_code == 503
        assert "detail" in response.json()
        assert "errors" in response.json()["detail"]
        assert response.json()["detail"]["errors"][0]["code"] == "ServiceUnavailable"
        assert "Service error" in response.json()["detail"]["errors"][0]["message"]


@pytest.mark.asyncio
async def test_get_coin_success(client):
    test_data = {
        "name": "Bitcoin",
        "price_usd": 50000.00,
        "percent_change_1h": 0.5,
        "percent_change_24h": 2.5,
        "percent_change_7d": 10.0,
        "market_cap_usd": 1000000000000,
        "rank": 1,
        "last_updated": "2025-07-24 01:23:06",
    }
    with patch('crypto_service.crypto_parser.CryptoParser.get_coin_info', new=AsyncMock(return_value=test_data)):
        response = client.get('/v1/crypto-prices/BTC')
        assert response.status_code == 200
        assert response.json() == {"data": test_data, "errors": None, "meta": None}


@pytest.mark.asyncio
async def test_get_coin_not_found(client):
    with patch(
        'crypto_service.crypto_parser.CryptoParser.get_coin_info',
        new=AsyncMock(return_value={"error": "Crypto UNKNOWN not found"}),
    ):
        response = client.get('/v1/crypto-prices/UNKNOWN')
        assert response.status_code == 404
        assert "detail" in response.json()
        assert "errors" in response.json()["detail"]
        assert response.json()["detail"]["errors"][0]["code"] == "NotFound"
        assert "Crypto UNKNOWN not found" in response.json()["detail"]["errors"][0]["message"]


@pytest.mark.asyncio
async def test_not_found_handler(client):
    response = client.get('/nonexistent-route')
    assert response.status_code == 404
    assert response.json() == {'detail': 'Not Found'}
