"""
FinBot API — FastAPI application
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import upload, analyze, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger(__name__).info("FinBot API starting...")
    yield
    logging.getLogger(__name__).info("FinBot API shutting down...")


app = FastAPI(
    title="FinBot API",
    description="Bot phân tích báo cáo tài chính Việt Nam",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analyze"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "finbot-api"}
