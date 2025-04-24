import requests
import json
import logging
from datetime import datetime
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_FILE = os.getenv('DATA_FILE', 'crypto_service/crypto_prices.json')


class CryptoParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0"
        }

    def parse_crypto_prices(self):
        try:
            url = "https://api.coinlore.net/api/tickers/"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                data_formatted = {}

                # Add timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data_formatted["last_updated"] = timestamp

                # Format data for easier access
                for coin in data["data"]:
                    data_formatted[coin["symbol"]] = {
                        "name": coin["name"],
                        "price_usd": float(coin["price_usd"]),
                        "percent_change_1h": float(coin["percent_change_1h"]),
                        "percent_change_24h": float(coin["percent_change_24h"]),
                        "percent_change_7d": float(coin["percent_change_7d"]),
                        "market_cap_usd": float(coin["market_cap_usd"]),
                        "rank": int(coin["rank"])
                    }

                # Save data to file
                with open(DATA_FILE, 'w') as f:
                    json.dump(data_formatted, f, indent=4)

                logger.info(f"Prices updated and saved to {DATA_FILE}")
                return data_formatted
            else:
                logger.error(f"API request failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error parsing crypto prices: {e}")
            return None

    def read_crypto_prices(self):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            logger.warning(f"Data file {DATA_FILE} not found")
            return None
        except Exception as e:
            logger.error(f"Error reading data file: {e}")
            return None

    def get_coin_info(self, symbol):
        data = self.read_crypto_prices()
        if not data or "last_updated" not in data:
            return None

        symbol = symbol.upper()
        if symbol not in data:
            similar_coins = [coin for coin in data.keys() if coin.upper().startswith(symbol[0]) and coin != "last_updated"]
            return {"error": f"Crypto {symbol} not found", "suggestions": similar_coins[:5]}

        coin_info = data[symbol]
        coin_info["last_updated"] = data["last_updated"]
        return coin_info
