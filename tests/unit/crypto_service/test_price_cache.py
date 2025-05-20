import pytest
from unittest.mock import patch
from crypto_service.price_cache import get_cached_prices, get_cached_coin_info


@pytest.fixture
def mock_parser():
    with patch('crypto_service.price_cache.parser') as mock_parser:
        yield mock_parser


def test_get_cached_prices(mock_parser):
    mock_parser.get_crypto_prices.return_value = {'BTC': {'price': 50000}}
    result = get_cached_prices()
    assert result == {'BTC': {'price': 50000}}


def test_get_cached_coin_info(mock_parser):
    mock_parser.get_coin_info.return_value = {'BTC': {'price': 50000}}
    result = get_cached_coin_info('BTC')
    assert result == {'BTC': {'price': 50000}}
