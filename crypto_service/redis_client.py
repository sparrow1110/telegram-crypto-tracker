import redis.asyncio as redis
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WSLRedisClient:
    def __init__(self):
        self.redis = None
        self._connect()

    def _connect(self):
        try:
            self.redis = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                password=os.getenv('REDIS_PASSWORD') or None,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            logger.info(f"Connected to Redis at {os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', 6379)}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def save_crypto_data(self, data):
        try:
            expire = int(os.getenv('REDIS_EXPIRE_SECONDS', 300))
            async with self.redis.pipeline() as pipe:
                pipe.setex('crypto:all_data', expire, json.dumps(data))
                pipe.setex(
                    'crypto:last_updated',
                    expire,
                    data.get('last_updated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Error saving crypto data to Redis: {e}")
            return False

    async def get_crypto_data(self):
        try:
            data = await self.redis.get('crypto:all_data')
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error getting crypto data: {e}")
            return None

    async def is_data_expired(self):
        try:
            ttl = await self.redis.ttl('crypto:all_data')
            return ttl < 60
        except Exception as e:
            logger.error(f"Error checking data expiration: {e}")
            return True


redis_client = WSLRedisClient()
