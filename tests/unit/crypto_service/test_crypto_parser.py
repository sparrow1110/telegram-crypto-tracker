import pytest
from unittest.mock import AsyncMock, Mock, patch
from crypto_service.crypto_parser import CryptoParser


@pytest.fixture
def crypto_parser():
    return CryptoParser()


@pytest.mark.asyncio
async def test_fetch_and_save_crypto_prices(crypto_parser):
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = Mock(
            status=200,
            json=AsyncMock(
                return_value={
                    'data': [
                        {
                            'symbol': 'BTC',
                            'name': 'Bitcoin',
                            'price_usd': '50000.00',
                            'percent_change_1h': '0.5',
                            'percent_change_24h': '2.5',
                            'percent_change_7d': '10.0',
                            'market_cap_usd': '1000000000000',
                            'rank': 1,
                        }
                    ]
                }
            ),
        )
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch('crypto_service.redis_client.redis_client.save_crypto_data', new=AsyncMock(return_value=True)):
            result = await crypto_parser.fetch_and_save_crypto_prices()
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
                'rank': 1,
            }
        ]
    }
    formatted = crypto_parser._format_data(api_data)
    assert 'BTC' in formatted
    assert formatted['BTC']['name'] == 'Bitcoin'
    assert formatted['BTC']['price_usd'] == 50000.00
    assert 'last_updated' in formatted
