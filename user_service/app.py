import os
import logging
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from user_service.models import Base
from user_service.db_handler import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting user_service")

# Инициализация FastAPI приложения
app = FastAPI(
    title="User Service API",
    description="API для управления пользовательскими данными",
    version="1.0.0",
)

# Настройка базы данных
DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Инициализация DatabaseManager
db_manager = DatabaseManager(engine, AsyncSessionLocal)


# Pydantic-модели для ответа
class Error(BaseModel):
    code: str
    message: str


class UserResponse(BaseModel):
    data: Optional[Dict] = None
    errors: Optional[List[Error]] = None
    meta: Optional[Dict] = None
    status_code: Optional[int] = None


# Создание таблиц при старте
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


# Проверка токена
API_TOKEN = os.getenv('API_TOKEN', 'your-secret-api-token')


async def verify_token(request: Request) -> bool:
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    return token == API_TOKEN


@app.get("/v1/stats", response_model=UserResponse)
async def get_stats(request: Request):
    requester_id = request.query_params.get('requester_id')
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    if not requester_id or await db_manager.is_blocked(int(requester_id)):
        raise HTTPException(
            status_code=403,
            detail={"errors": [{"code": "Forbidden", "message": "User is blocked or invalid requester"}]},
        )
    try:
        stats = await db_manager.get_stats()
        return {"data": stats, "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.post("/v1/users")
async def register_user(request: Request, response: Response):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    data = await request.json()
    try:
        success, is_new = await db_manager.register_user(
            data['user_id'], data.get('username'), data.get('first_name'), data.get('last_name')
        )
        if success:
            response.status_code = 201 if is_new else 200
            return {
                "data": {"user_id": data['user_id'], "username": data.get('username'), "is_new": is_new},
                "status_code": 201 if is_new else 200,
                "errors": None,
                "meta": None,
            }
        raise HTTPException(
            status_code=400, detail={"errors": [{"code": "RegistrationFailed", "message": "User registration failed"}]}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.post("/v1/command-logs", response_model=UserResponse)
async def log_command(request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    data = await request.json()
    requester_id = data.get('requester_id')
    if not requester_id or await db_manager.is_blocked(requester_id):
        raise HTTPException(
            status_code=403,
            detail={"errors": [{"code": "Forbidden", "message": "User is blocked or invalid requester"}]},
        )
    try:
        success = await db_manager.log_command(data['user_id'], data['command'])
        if success:
            return {"data": {"user_id": data['user_id'], "command": data['command']}, "status_code": 200}
        raise HTTPException(
            status_code=400, detail={"errors": [{"code": "LoggingFailed", "message": "Failed to log command"}]}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.post("/v1/users/{user_id}/favorite-cryptos", response_model=UserResponse, status_code=201)
async def add_favorite(user_id: int, request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    data = await request.json()
    requester_id = data.get('requester_id')
    if not requester_id or await db_manager.is_blocked(requester_id):
        raise HTTPException(
            status_code=403,
            detail={"errors": [{"code": "Forbidden", "message": "User is blocked or invalid requester"}]},
        )
    try:
        success = await db_manager.add_favorite_crypto(user_id, data['crypto_symbol'])
        logger.info(f"add_favorite_crypto for user {user_id}, symbol {data['crypto_symbol']}: success={success}")
        if success:
            return {"data": {"user_id": user_id, "crypto_symbol": data['crypto_symbol']}, "status_code": 201}
        elif success is None:
            raise HTTPException(status_code=404, detail={"errors": [{"code": "NotFound", "message": "User not found"}]})
        raise HTTPException(
            status_code=400, detail={"errors": [{"code": "AlreadyExists", "message": "Crypto already in favorites"}]}
        )
    except Exception as e:
        logger.error(f"Error adding favorite for user {user_id}, symbol {data['crypto_symbol']}: {e}")
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.delete("/v1/users/{user_id}/favorite-cryptos", response_model=UserResponse)
async def remove_favorite(user_id: int, request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    data = await request.json()
    requester_id = data.get('requester_id')
    if not requester_id or await db_manager.is_blocked(requester_id):
        raise HTTPException(
            status_code=403,
            detail={"errors": [{"code": "Forbidden", "message": "User is blocked or invalid requester"}]},
        )
    try:
        if not data or 'crypto_symbol' not in data:
            raise HTTPException(
                status_code=400,
                detail={"errors": [{"code": "ValidationError", "message": "Missing required field: crypto_symbol"}]},
            )
        success = await db_manager.remove_favorite_crypto(user_id, data['crypto_symbol'])
        if success:
            return {
                "data": {
                    "success": True,
                    "user_id": user_id,
                    "crypto_symbol": data['crypto_symbol'],
                    "action": "removed_from_favorites",
                },
                "status_code": 200,
            }
        raise HTTPException(
            status_code=404,
            detail={"errors": [{"code": "NotFound", "message": "Favorite not found or user does not exist"}]},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.get("/v1/users/{user_id}/favorite-cryptos", response_model=UserResponse)
async def get_favorites(user_id: int, request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    requester_id = request.query_params.get('requester_id')
    if not requester_id or await db_manager.is_blocked(int(requester_id)):
        raise HTTPException(
            status_code=403,
            detail={"errors": [{"code": "Forbidden", "message": "User is blocked or invalid requester"}]},
        )
    try:
        favorites = await db_manager.get_favorite_cryptos(user_id)
        if favorites is None:
            raise HTTPException(status_code=404, detail={"errors": [{"code": "NotFound", "message": "User not found"}]})
        return {"data": {"favorites": favorites}, "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.get("/v1/stats/popular-cryptos", response_model=UserResponse)
async def popular_cryptos(request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    requester_id = request.query_params.get('requester_id')
    if not requester_id or await db_manager.is_blocked(int(requester_id)):
        raise HTTPException(
            status_code=403,
            detail={"errors": [{"code": "Forbidden", "message": "User is blocked or invalid requester"}]},
        )
    try:
        limit = int(request.query_params.get('limit', 5))
        cryptos = await db_manager.get_popular_cryptos(limit)
        return {"data": {"cryptos": cryptos}, "meta": {"limit": limit}, "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.get("/v1/users/unblocked", response_model=UserResponse)
async def unblocked_users(request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    try:
        users = await db_manager.get_unblocked_users()
        return {"data": {"users": users}, "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.post("/v1/users/{user_id}/block", response_model=UserResponse)
async def block_user(user_id: int, request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    data = await request.json()
    requester_id = data.get('requester_id')
    if not requester_id or await db_manager.is_blocked(requester_id):
        raise HTTPException(
            status_code=403,
            detail={"errors": [{"code": "Forbidden", "message": "User is blocked or invalid requester"}]},
        )
    try:
        success = await db_manager.block_user(user_id)
        if success:
            return {"data": {"user_id": user_id, "is_blocked": True, "action": "blocked"}, "status_code": 200}
        raise HTTPException(
            status_code=404, detail={"errors": [{"code": "UserNotFound", "message": f"User {user_id} not found"}]}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.post("/v1/users/{user_id}/unblock", response_model=UserResponse)
async def unblock_user(user_id: int, request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    data = await request.json()
    requester_id = data.get('requester_id')
    if not requester_id or await db_manager.is_blocked(requester_id):
        raise HTTPException(
            status_code=403,
            detail={"errors": [{"code": "Forbidden", "message": "User is blocked or invalid requester"}]},
        )
    try:
        success = await db_manager.unblock_user(user_id)
        if success:
            return {"data": {"user_id": user_id, "is_blocked": False, "action": "unblocked"}, "status_code": 200}
        raise HTTPException(
            status_code=404, detail={"errors": [{"code": "UserNotFound", "message": f"User {user_id} not found"}]}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.get("/v1/users/{user_id}/block-status", response_model=UserResponse)
async def is_blocked(user_id: int, request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    requester_id = request.query_params.get('requester_id')
    if not requester_id:
        raise HTTPException(
            status_code=403, detail={"errors": [{"code": "Forbidden", "message": "Invalid or missing requester_id"}]}
        )
    try:
        blocked = await db_manager.is_blocked(int(requester_id))
        if blocked is None:
            raise HTTPException(
                status_code=404, detail={"errors": [{"code": "UserNotFound", "message": f"User {user_id} not found"}]}
            )
        return {"data": {"user_id": user_id, "is_blocked": blocked}, "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("user_service.app:app", host="0.0.0.0", port=5001, reload=True)
