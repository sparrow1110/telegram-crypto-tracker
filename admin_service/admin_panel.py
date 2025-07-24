import logging
from datetime import datetime
import httpx
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def escape_markdown_v1(text: str) -> str:
    """Экранирование символов `_` и `*` для Markdown (V1)."""
    return text.replace('_', r'\_').replace('*', r'\*')


class AdminPanel:
    def __init__(self, user_service_url, crypto_service_url, api_token):
        self.user_service_url = user_service_url
        self.crypto_service_url = crypto_service_url
        self.api_token = api_token
        self.headers = {'Authorization': f'Bearer {self.api_token}'}

    async def is_admin(self, user_id: int) -> bool:
        return str(user_id) in os.getenv('ADMIN_IDS', '').split(',')

    async def get_bot_stats(self, requester_id: int) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.user_service_url}/v1/stats", headers=self.headers, params={'requester_id': requester_id}
                )
                response.raise_for_status()
                stats_data = response.json()['data']

                stats = "📊 *Статистика бота*\n\n"
                stats += "👥 *Пользователи:*\n"
                stats += f"• Всего пользователей: {stats_data.get('user_count', 0)}\n"
                stats += f"• Активных за 24 часа: {stats_data.get('active_users_24h', 0)}\n"
                stats += f"• Активных за 7 дней: {stats_data.get('active_users_7d', 0)}\n"
                stats += f"• Заблокированных: {stats_data.get('blocked_count', 0)}\n\n"
                stats += "⭐ *Избранное:*\n"
                stats += f"• Всего добавлено в избранное: {stats_data.get('favorites_count', 0)}\n"

                commands = stats_data.get('popular_commands', [])
                if commands:
                    stats += "\n🔄 *Популярные команды (7 дней):*\n"
                    for cmd, count in commands:
                        stats += f"• {escape_markdown_v1(cmd)}: {count} раз\n"

                stats += f"\n🕒 *Актуально на:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise

    async def get_popular_cryptos(self, requester_id: int) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.user_service_url}/v1/stats/popular-cryptos",
                    headers=self.headers,
                    params={'requester_id': requester_id},
                )
                response.raise_for_status()
                popular = response.json()['data'].get('cryptos', [])

                if not popular:
                    return "Нет данных о популярных криптовалютах."

                result = "🔝 *Популярные криптовалюты*\n\n"
                for i, (symbol, count) in enumerate(popular, 1):
                    result += f"{i}. *{symbol}* - {count} пользователей\n"

                result += f"\n🕒 *Актуально на:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                return result
        except Exception as e:
            logger.error(f"Error getting popular cryptos: {e}")
            raise

    async def block_user(self, user_id: int, requester_id: int) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.user_service_url}/v1/users/{user_id}/block",
                    headers=self.headers,
                    json={'requester_id': requester_id},
                )
                response.raise_for_status()
                return response.json()['data'].get('is_blocked', False)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"User {user_id} not found")
                return False
            else:
                logger.error(f"Error blocking user {user_id}: {e}")
                raise
        except Exception as e:
            logger.error(f"Error blocking user {user_id}: {e}")
            raise

    async def unblock_user(self, user_id: int, requester_id: int) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.user_service_url}/v1/users/{user_id}/unblock",
                    headers=self.headers,
                    json={'requester_id': requester_id},
                )
                response.raise_for_status()
                return not response.json()['data'].get('is_blocked', True)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"User {user_id} not found")
                return False
            else:
                logger.error(f"Error unblocking user {user_id}: {e}")
                raise
        except Exception as e:
            logger.error(f"Error unblocking user {user_id}: {e}")
            raise
