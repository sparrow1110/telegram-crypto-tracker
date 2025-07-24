import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
from admin_service.admin_panel import AdminPanel
from dotenv import load_dotenv
import logging

load_dotenv()


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Pydantic-модели для ответа
class Error(BaseModel):
    code: str
    message: str


class AdminResponse(BaseModel):
    data: Optional[Dict] = None
    errors: Optional[List[Error]] = None
    meta: Optional[Dict] = None


# Инициализация FastAPI приложения
app = FastAPI(
    title="Admin Service API",
    description="API для администрирования криптобота",
    version="1.0.0",
)

# Инициализация AdminPanel
API_TOKEN = os.getenv('API_TOKEN', 'your-secret-api-token')
admin = AdminPanel(
    user_service_url=os.getenv('USER_SERVICE_URL', 'http://user_service:5001'),
    crypto_service_url=os.getenv('CRYPTO_SERVICE_URL', 'http://crypto_service:5003'),
    api_token=API_TOKEN,
)


# Проверка токена
async def verify_token(request: Request) -> bool:
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    return token == API_TOKEN


# Проверка статуса админа
async def check_admin(requester_id: int) -> bool:
    try:
        return await admin.is_admin(requester_id)
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


@app.get("/v1/admins/{user_id}/status", response_model=AdminResponse)
async def is_admin(user_id: int, request: Request):
    if not await verify_token(request):
        raise HTTPException(
            status_code=401, detail={"errors": [{"code": "Unauthorized", "message": "Invalid or missing API token"}]}
        )
    try:
        is_admin_status = await admin.is_admin(user_id)
        return {"data": {"is_admin": is_admin_status}}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.get("/v1/stats", response_model=AdminResponse)
async def get_stats(request: Request):
    requester_id = request.query_params.get('requester_id')
    if not requester_id or not await check_admin(int(requester_id)):
        raise HTTPException(
            status_code=403, detail={"errors": [{"code": "Forbidden", "message": "User is not an admin"}]}
        )
    try:
        stats = await admin.get_bot_stats(int(requester_id))
        return {"data": {"stats": stats}}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.get("/v1/stats/popular-cryptos", response_model=AdminResponse)
async def popular_cryptos(request: Request):
    requester_id = request.query_params.get('requester_id')
    if not requester_id or not await check_admin(int(requester_id)):
        raise HTTPException(
            status_code=403, detail={"errors": [{"code": "Forbidden", "message": "User is not an admin"}]}
        )
    try:
        popular = await admin.get_popular_cryptos(int(requester_id))
        return {"data": {"popular": popular}}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.post("/v1/users/{user_id}/block", response_model=AdminResponse)
async def block_user(user_id: int, request: Request):
    data = await request.json() or {}
    requester_id = data.get('requester_id')
    if not requester_id or not await check_admin(requester_id):
        raise HTTPException(
            status_code=403, detail={"errors": [{"code": "Forbidden", "message": "User is not an admin"}]}
        )
    try:
        success = await admin.block_user(user_id, requester_id)
        if success:
            return {"data": {"user_id": user_id, "is_blocked": True, "action": "admin_blocked"}}
        raise HTTPException(status_code=404, detail={"errors": [{"code": "NotFound", "message": "User not found"}]})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


@app.post("/v1/users/{user_id}/unblock", response_model=AdminResponse)
async def unblock_user(user_id: int, request: Request):
    data = await request.json() or {}
    requester_id = data.get('requester_id')
    if not requester_id or not await check_admin(requester_id):
        raise HTTPException(
            status_code=403, detail={"errors": [{"code": "Forbidden", "message": "User is not an admin"}]}
        )
    try:
        success = await admin.unblock_user(user_id, requester_id)
        if success:
            return {"data": {"user_id": user_id, "is_blocked": False, "action": "admin_unblocked"}}
        raise HTTPException(status_code=404, detail={"errors": [{"code": "NotFound", "message": "User not found"}]})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errors": [{"code": "InternalServerError", "message": str(e)}]})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("admin_service.app:app", host="0.0.0.0", port=5002, reload=True)
