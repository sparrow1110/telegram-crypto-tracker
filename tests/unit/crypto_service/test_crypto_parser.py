import pytest
from unittest.mock import Mock, patch
from crypto_service.crypto_parser import CryptoParser


@pytest.fixture
def crypto_parser():
    return CryptoParser()


@patch('crypto_service.crypto_parser.requests.get')
def test_fetch_and_save_crypto_prices(mock_get, crypto_parser):
    mock_response = Mock()
    mock_response.json.return_value = {
        'data': [
            {
                'symbol': 'BTC',
                'name': 'Bitcoin',
                'price_usd': '50000.00',
                'percent_change_1h': '0.5',
                'percent_change_24h': '2.5',
                'percent_change_7d': '10.0',
                'market_cap_usd': '1000000000000',
                'rank': 1
            }
        ]
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    with patch('crypto_service.crypto_parser.redis_client') as mock_redis:
        mock_redis.save_crypto_data.return_value = True
        result = crypto_parser.fetch_and_save_crypto_prices()

        assert 'BTC' in result
        assert result['BTC']['name'] == 'Bitcoin'
        assert result['BTC']['price_usd'] == 50000.00
        assert 'last_updated' in result


def test_format_data(crypto_parser):
    api_data = {
        'data': [
            {
                'symbol': 'BTC',
                'name': 'Bitcoin',
                'price_usd': '50000.00',
                'percent_change_1h': '0.5',
                'percent_change_24h': '2.5',
                'percent_change_7d': '10.0',
                'market_cap_usd': '1000000000000',
                'rank': 1
            }
        ]
    }

    formatted = crypto_parser._format_data(api_data)

    assert 'BTC' in formatted
    assert formatted['BTC']['name'] == 'Bitcoin'
    assert formatted['BTC']['price_usd'] == 50000.00
    assert 'last_updated' in formatted
