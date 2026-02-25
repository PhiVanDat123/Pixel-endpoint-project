from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from typing import Literal
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
import orjson
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
PIXEL_KEY = "pixels"

redis: aioredis.Redis = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo Redis connection pool khi app start
    global redis
    redis = aioredis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,        # pool size per worker
    )
    yield
    await redis.aclose()


app = FastAPI(default_response_class=ORJSONResponse, lifespan=lifespan)


class PixelRequest(BaseModel):
    x: int
    y: int
    channel: Literal["R", "G", "B"]
    value: int  # 0-255

    model_config = {"frozen": True}


@app.post("/pixel", status_code=200)
async def receive_pixel(req: PixelRequest):
    # RPUSH: append vào Redis list — atomic, không cần lock
    await redis.rpush(PIXEL_KEY, orjson.dumps(req.model_dump()).decode())
    return {"status": "ok"}


@app.get("/pixels")
async def get_all_pixels():
    # LRANGE 0 -1: lấy toàn bộ list
    raw = await redis.lrange(PIXEL_KEY, 0, -1)
    data = [orjson.loads(item) for item in raw]
    return {"total": len(data), "data": data}


@app.delete("/pixels")
async def clear_pixels():
    await redis.delete(PIXEL_KEY)
    return {"status": "cleared"}


@app.get("/health")
async def health():
    total = await redis.llen(PIXEL_KEY)
    return {"status": "healthy", "pid": os.getpid(), "store_size": total}