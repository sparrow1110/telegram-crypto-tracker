import pytest
from unittest.mock import patch
from crypto_service.app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_get_prices_success(client):
    test_data = {
        "last_updated": "2023-10-01 12:00:00",
        "BTC": {"price_usd": 50000}
    }

    with patch('crypto_service.app.get_cached_prices', return_value=test_data):
        response = client.get('/v1/crypto-prices')
        assert response.status_code == 200
        assert response.json == {
            "data": test_data
        }


def test_get_prices_error(client):
    with patch('crypto_service.app.get_cached_prices', return_value=None):
        response = client.get('/v1/crypto-prices')
        assert response.status_code == 503
        assert "errors" in response.json


def test_get_coin_success(client):
    test_data = {
        "name": "Bitcoin",
        "price_usd": 50000,
        "last_updated": "2023-10-01 12:00:00"
    }

    with patch('crypto_service.app.get_cached_coin_info', return_value=test_data):
        response = client.get('/v1/crypto-prices/BTC')
        assert response.status_code == 200
        assert response.json == {
            "data": test_data
        }


def test_get_coin_not_found(client):
    with patch('crypto_service.app.get_cached_coin_info', return_value={"error": "Not found"}):
        response = client.get('/v1/crypto-prices/UNKNOWN')
        assert response.status_code == 404
        assert "errors" in response.json


def test_not_found_handler(client):
    response = client.get('/nonexistent-route')
    assert response.status_code == 404
    assert "errors" in response.json
