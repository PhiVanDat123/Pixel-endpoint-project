from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal
import threading

app = FastAPI()

store = []
lock = threading.Lock()


class PixelRequest(BaseModel):
    x: int
    y: int
    channel: Literal["R", "G", "B"]
    value: int  # 0-255


@app.post("/pixel")
async def receive_pixel(req: PixelRequest):
    with lock:
        store.append(req.dict())
    return {"status": "ok"}


@app.get("/pixels")
async def get_all_pixels():
    with lock:
        return {"total": len(store), "data": store}


@app.delete("/pixels")
async def clear_pixels():
    with lock:
        store.clear()
    return {"status": "cleared"}


@app.get("/health")
async def health():
    return {"status": "healthy"}