import redis
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WSLRedisClient:
    def __init__(self):
        self.redis = None
        self._connect()

    def _connect(self):
        try:
            self.redis = redis.Redis(
                host='172.21.18.121',  # Ваш IP WSL
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                password=os.getenv('REDIS_PASSWORD') or None,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis.ping()
            logger.info(f"Connected to Redis at 172.21.18.121:{os.getenv('REDIS_PORT', 6379)}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    def save_crypto_data(self, data):
        try:
            expire = int(os.getenv('REDIS_EXPIRE_SECONDS', 300))
            self.redis.setex('crypto:all_data', expire, json.dumps(data))
            self.redis.setex('crypto:last_updated', expire, data.get('last_updated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            return True
        except Exception as e:
            logger.error(f"Error saving crypto data to Redis: {e}")
            return False

    def get_crypto_data(self):
        try:
            data = self.redis.get('crypto:all_data')
            print('Redis')
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error getting crypto data: {e}")
            return None

    def is_data_expired(self):
        return self.redis.ttl('crypto:all_data') < 60

    #def get_connection(self):
        #if not self.redis or not self.redis.ping():
            #self._connect()
        #return self.redis

# Глобальный экземпляр клиента
redis_client = WSLRedisClient()