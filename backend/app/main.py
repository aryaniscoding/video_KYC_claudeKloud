"""
Poonawalla Fincorp — Video KYC Loan Origination Backend
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import get_settings
from app.api.admin import router as admin_router
from app.api.session import router as session_router
from app.api.ws.liveness import router as ws_liveness_router
from app.api.ws.consent import router as ws_consent_router
from app.api.ws.qa import router as ws_qa_router

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.is_dev else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting Video KYC backend (env=%s)", settings.app_env)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Poonawalla Fincorp — Video KYC API",
    version="2.0.0",
    description="Agentic AI video call–based loan origination system",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_dev else None,
    redoc_url="/redoc" if settings.is_dev else None,
)

_CORS_ORIGINS = list({
    settings.frontend_url,
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
})

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# REST routes
app.include_router(admin_router)
app.include_router(session_router)

# WebSocket routes
app.include_router(ws_liveness_router)
app.include_router(ws_consent_router)
app.include_router(ws_qa_router)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env, "version": "2.0.0"}
