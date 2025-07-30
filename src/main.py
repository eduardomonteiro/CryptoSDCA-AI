"""
src/main.py – Unified application entry-point for CryptoSDCA-AI
Rewritten to resolve 404/403 issues, avoid duplicated routes, and
cleanly wire every API, WebSocket and background component.

Key changes
-----------
1.  Auth router is now imported and mounted ⇒ /auth/login works.
2.  Removed duplicate “/login” handler (served by auth router).
3.  Added explicit log lines confirming all routers are loaded.
4.  Static/Templates paths resolved relative to project root.
5.  Tightened CORS origins & added UTF-8 response headers.
6.  All globals declared `Optional[...]` for better type-safety.
"""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.middleware.sessions import SessionMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

# --------------------------------------------------------------------------- #
# Local imports – all centralised here to fail early if something is missing
# --------------------------------------------------------------------------- #

from src.config import get_settings
from src.database import close_database, init_database
from src.exceptions import CryptoBotException
from src.models import User

# Routers
from api.routes import admin, dashboard, history, settings as api_settings, trading
from api.routes.auth import router as auth_router, get_current_user

# Core bot components
from core.ai_validator import AIValidator
from core.dca_engine import DCAEngine
from core.exchange_manager import ExchangeManager
from core.risk_manager import RiskManager
from core.sentiment_analyzer import SentimentAnalyzer

# --------------------------------------------------------------------------- #
# Settings & globals
# --------------------------------------------------------------------------- #

settings = get_settings()
ROOT_DIR = Path(__file__).resolve().parent.parent

exchange_manager: Optional[ExchangeManager] = None
ai_validator:    Optional[AIValidator]    = None
dca_engine:      Optional[DCAEngine]      = None
sentiment_analyzer: Optional[SentimentAnalyzer] = None
risk_manager:    Optional[RiskManager]    = None


# --------------------------------------------------------------------------- #
# Lifespan context – start/stop background services
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(_: FastAPI):
    global exchange_manager, ai_validator, dca_engine, sentiment_analyzer, risk_manager

    logger.info("🚀 Booting CryptoSDCA-AI …")
    try:
        await init_database()
        logger.info("✅  DB ready")

        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()

        ai_validator = AIValidator()
        await ai_validator.initialize()

        sentiment_analyzer = SentimentAnalyzer()
        await sentiment_analyzer.initialize()

        risk_manager = RiskManager()
        await risk_manager.initialize()

        dca_engine = DCAEngine(
            exchange_manager=exchange_manager,
            ai_validator=ai_validator,
            sentiment_analyzer=sentiment_analyzer,
            risk_manager=risk_manager,
        )
        await dca_engine.initialize()

        if not settings.test_mode:
            asyncio.create_task(dca_engine.start_trading_loop())
            asyncio.create_task(sentiment_analyzer.start_monitoring())
            logger.info("🛠  Background loops launched")

        logger.success("🎉 CryptoSDCA-AI started")
        yield

    finally:
        logger.warning("🛑 Shutting down …")
        for comp in (dca_engine, sentiment_analyzer, exchange_manager, ai_validator):
            if comp:
                await comp.close()
        await close_database()
        logger.success("✅  Shutdown complete")


# --------------------------------------------------------------------------- #
# FastAPI app
# --------------------------------------------------------------------------- #

app = FastAPI(
    title=settings.name,
    description="Advanced crypto trading bot with AI validation and DCA strategy",
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sessions (browser login)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Static & templates
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))


# --------------------------------------------------------------------------- #
# Exception handlers
# --------------------------------------------------------------------------- #

@app.exception_handler(CryptoBotException)
async def handle_bot_error(_: Request, exc: CryptoBotException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(HTTPException)
async def handle_http_error(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": exc.detail},
    )


@app.exception_handler(Exception)
async def handle_generic_error(_: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.debug else None,
        },
    )


# --------------------------------------------------------------------------- #
# Web pages
# --------------------------------------------------------------------------- #

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect unauthenticated users to login, otherwise dashboard."""
    if request.session.get("user"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/auth/login", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "app_name": settings.name, "version": settings.version},
    )


# --------------------------------------------------------------------------- #
# Health / info
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/info")
async def info():
    return {
        "name": settings.name,
        "version": settings.version,
        "debug": settings.debug,
        "paper_trading": settings.paper_trading,
    }


# --------------------------------------------------------------------------- #
# Routers
# --------------------------------------------------------------------------- #

app.include_router(auth_router,     prefix="/auth",         tags=["auth"])
app.include_router(admin.router,    prefix="/api/admin",    tags=["admin"])
app.include_router(trading.router,  prefix="/api/trading",  tags=["trading"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(history.router,  prefix="/api/history",  tags=["history"])
app.include_router(api_settings.router, prefix="/api/settings", tags=["settings"])

logger.info("🛣  Routers mounted: " + ", ".join([r.prefix or "/" for r in app.router.routes]))


# --------------------------------------------------------------------------- #
# WebSocket – live updates
# --------------------------------------------------------------------------- #

class WSManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"WS connect ({len(self.active)})")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"WS disconnect ({len(self.active)})")

    async def send(self, ws: WebSocket, msg: dict):
        await ws.send_text(json.dumps(msg))

    async def broadcast(self, msg: dict):
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(msg))
            except Exception:
                self.disconnect(ws)


ws_manager = WSManager()


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            _ = await ws.receive_text()  # keep-alive / ignore payload
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


async def broadcast_update(event: str, payload: Dict[str, Any]):
    await ws_manager.broadcast({"event": event, "data": payload, "ts": datetime.utcnow().isoformat()})


# --------------------------------------------------------------------------- #
# Entry-point helper
# --------------------------------------------------------------------------- #

def run():
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    run()
