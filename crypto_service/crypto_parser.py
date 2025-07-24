import logging
from datetime import datetime
import aiohttp
from .redis_client import redis_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CryptoParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0"
        }

    async def fetch_and_save_crypto_prices(self):
        try:
            url = "https://api.coinlore.net/api/tickers/"
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        api_data = await response.json()
                        formatted_data = self._format_data(api_data)
                        if await redis_client.save_crypto_data(formatted_data):
                            logger.info("Crypto prices updated in Redis")
                            return formatted_data
                        else:
                            logger.error("Failed to save data to Redis")
                            return {"error": "Failed to save data to Redis"}
                    else:
                        error_msg = f"API request failed: {response.status}"
                        logger.error(error_msg)
                        return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error fetching crypto prices: {e}"
            logger.error(error_msg)
            return {"error": error_msg}

    def _format_data(self, api_data):
        formatted = {"last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        for coin in api_data["data"]:
            formatted[coin["symbol"]] = {
                "name": coin["name"],
                "price_usd": float(coin["price_usd"]),
                "percent_change_1h": float(coin["percent_change_1h"]),
                "percent_change_24h": float(coin["percent_change_24h"]),
                "percent_change_7d": float(coin["percent_change_7d"]),
                "market_cap_usd": float(coin["market_cap_usd"]),
                "rank": int(coin["rank"]),
            }
        return formatted

    async def get_crypto_prices(self):
        data = await redis_client.get_crypto_data()
        if not data or await redis_client.is_data_expired():
            logger.info("Data expired or not found, fetching fresh data")
            fresh_data = await self.fetch_and_save_crypto_prices()
            return fresh_data if not fresh_data.get('error') else data or fresh_data
        return data

    async def get_coin_info(self, symbol):
        data = await self.get_crypto_prices()
        if not data or "last_updated" not in data:
            return {"error": "Crypto data not available"}
        symbol = symbol.upper()
        if symbol in data:
            coin_info = data[symbol].copy()
            coin_info["last_updated"] = data["last_updated"]
            return coin_info
        similar_coins = [coin for coin in data.keys() if coin != "last_updated" and coin.upper().startswith(symbol[0])]
        return {"error": f"Crypto {symbol} not found", "suggestions": similar_coins[:5]}
