from cachetools import cached, TTLCache
from .crypto_parser import CryptoParser
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

parser = CryptoParser()

# Cache for 5 minutes (300 seconds)
crypto_cache = TTLCache(maxsize=100, ttl=300)


@cached(crypto_cache)
def get_cached_prices():
    return parser.read_crypto_prices() or parser.parse_crypto_prices()


@cached(crypto_cache)
def get_cached_coin_info(symbol):
    return parser.get_coin_info(symbol)
