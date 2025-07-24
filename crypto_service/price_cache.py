from asyncache import cached
from cachetools import TTLCache
from crypto_service.crypto_parser import CryptoParser
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parser = CryptoParser()
crypto_cache = TTLCache(maxsize=100, ttl=60)


@cached(crypto_cache)
async def get_cached_prices():
    try:
        result = await parser.get_crypto_prices()
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(result["error"])
        return result
    except Exception as e:
        logger.error(f"Error getting cached prices: {e}")
        raise


@cached(crypto_cache)
async def get_cached_coin_info(symbol):
    try:
        result = await parser.get_coin_info(symbol)
        if result.get("error"):
            raise ValueError(result["error"])
        return result
    except Exception as e:
        logger.error(f"Error getting cached coin info for {symbol}: {e}")
        raise
