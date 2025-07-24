import asyncio
import logging
from .crypto_parser import CryptoParser
from .price_cache import get_cached_prices, get_cached_coin_info
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class Error(BaseModel):
    code: str
    message: str


class CryptoResponse(BaseModel):
    data: Optional[Dict] = None
    errors: Optional[List[Error]] = None
    meta: Optional[Dict] = None


app = FastAPI(
    title="Crypto Service API",
    description="API для получения данных о криптовалютах",
    version="1.0.0",
)

parser = CryptoParser()


async def scheduled_parsing():
    while True:
        try:
            await parser.fetch_and_save_crypto_prices()
            logger.info("Crypto prices updated successfully")
        except Exception as e:
            logger.error(f"Error in scheduled parsing: {e}")
        await asyncio.sleep(300)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_parsing())
    logger.info("Started scheduled parsing task")


@app.get("/v1/crypto-prices", response_model=CryptoResponse)
async def get_crypto_prices():
    try:
        prices = await get_cached_prices()
        if prices is None or "error" in prices:
            raise HTTPException(
                status_code=503,
                detail={
                    "errors": [
                        {
                            "code": "ServiceUnavailable",
                            "message": (
                                prices.get("error", "Crypto data unavailable") if prices else "Crypto data unavailable"
                            ),
                        }
                    ]
                },
            )
        return {"data": prices, "errors": None, "meta": None}
    except ValueError as e:
        raise HTTPException(status_code=503, detail={"errors": [{"code": "ServiceUnavailable", "message": str(e)}]})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500, detail={"errors": [{"code": "InternalError", "message": "Internal server error"}]}
        )


@app.get("/v1/crypto-prices/{crypto_symbol}", response_model=CryptoResponse)
async def get_coin_price(crypto_symbol: str):
    try:
        coin_info = await get_cached_coin_info(crypto_symbol.upper())
        if coin_info is None or "error" in coin_info:
            raise HTTPException(
                status_code=404,
                detail={
                    "errors": [
                        {"code": "NotFound", "message": coin_info.get("error", f"Crypto {crypto_symbol} not found")}
                    ]
                },
            )
        return {"data": coin_info, "errors": None, "meta": None}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail={"errors": [{"code": "NotFound", "message": str(e)}]})
        raise HTTPException(status_code=503, detail={"errors": [{"code": "ServiceUnavailable", "message": str(e)}]})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500, detail={"errors": [{"code": "InternalError", "message": "Internal server error"}]}
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("crypto_service.app:app", host="0.0.0.0", port=5003, reload=True)
