import pytest
from unittest.mock import AsyncMock, patch
from crypto_service.price_cache import get_cached_prices, get_cached_coin_info


@pytest.mark.asyncio
async def test_get_cached_prices():
    test_data = {
        'last_updated': '2025-07-24 01:23:06',
        'BTC': {
            'name': 'Bitcoin',
            'price_usd': 50000.00,
            'percent_change_1h': 0.5,
            'percent_change_24h': 2.5,
            'percent_change_7d': 10.0,
            'market_cap_usd': 1000000000000,
            'rank': 1,
        },
    }
    with patch('crypto_service.crypto_parser.CryptoParser.get_crypto_prices', new=AsyncMock(return_value=test_data)):
        result = await get_cached_prices()
        assert result == test_data


@pytest.mark.asyncio
async def test_get_cached_coin_info():
    test_data = {
        'name': 'Bitcoin',
        'price_usd': 50000.00,
        'percent_change_1h': 0.5,
        'percent_change_24h': 2.5,
        'percent_change_7d': 10.0,
        'market_cap_usd': 1000000000000,
        'rank': 1,
        'last_updated': '2025-07-24 01:23:06',
    }
    with patch('crypto_service.crypto_parser.CryptoParser.get_coin_info', new=AsyncMock(return_value=test_data)):
        result = await get_cached_coin_info('BTC')
        assert result == test_data
