"""
src/main.py – Unified application entry-point for CryptoSDCA-AI
Production-ready crypto trading bot with AI validation and DCA strategy.
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

# Local imports
from src.config import get_settings
from src.database import close_database, init_database
from src.exceptions import CryptoBotException
from src.models.models import User

# Routers
from api.routes import admin, dashboard, history, settings as api_settings, trading
from api.routes.auth import router as auth_router, get_current_user

# Core bot components
from src.core.ai_validator import AIValidator
from src.core.dca_engine import DCAEngine
from src.core.exchange_manager import ExchangeManager
from src.core.risk_manager import RiskManager
from src.core.sentiment_analyzer import SentimentAnalyzer
from src.core.indicators import TechnicalIndicators

# Settings & globals
settings = get_settings()
ROOT_DIR = Path(__file__).resolve().parent.parent

# Global instances
exchange_manager: Optional[ExchangeManager] = None
ai_validator: Optional[AIValidator] = None
dca_engine: Optional[DCAEngine] = None
sentiment_analyzer: Optional[SentimentAnalyzer] = None
risk_manager: Optional[RiskManager] = None
indicators: Optional[TechnicalIndicators] = None

# WebSocket manager
ws_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global exchange_manager, ai_validator, dca_engine, sentiment_analyzer, risk_manager, indicators, ws_manager
    
    try:
        logger.info("🚀 Starting CryptoSDCA-AI...")
        
        # Initialize database
        if not await init_database():
            logger.error("❌ Database initialization failed")
            raise RuntimeError("Database initialization failed")
        logger.info("✅ Database ready")

        # Initialize core components
        logger.info("🔄 Initializing core components...")
        
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()
        logger.info("✅ Exchange Manager ready")

        ai_validator = AIValidator()
        await ai_validator.initialize()
        logger.info("✅ AI Validator ready")

        sentiment_analyzer = SentimentAnalyzer()
        await sentiment_analyzer.initialize()
        logger.info("✅ Sentiment Analyzer ready")

        risk_manager = RiskManager(exchange_manager=exchange_manager)
        await risk_manager.initialize()
        logger.info("✅ Risk Manager ready")

        indicators = TechnicalIndicators()
        await indicators.initialize()
        logger.info("✅ Technical Indicators ready")

        dca_engine = DCAEngine(
            exchange_manager=exchange_manager,
            ai_validator=ai_validator,
            sentiment_analyzer=sentiment_analyzer,
            risk_manager=risk_manager,
        )
        await dca_engine.initialize()
        logger.info("✅ DCA Engine ready")

        # Initialize WebSocket manager
        ws_manager = WSManager()
        logger.info("✅ WebSocket Manager ready")

        # Start background tasks if not in test mode
        if not settings.test_mode:
            asyncio.create_task(dca_engine.start_trading_loop())
            asyncio.create_task(sentiment_analyzer.start_monitoring())
            logger.info("🛠 Background tasks started")

        logger.success("🎉 CryptoSDCA-AI fully initialized and ready!")

        yield

    except Exception as e:
        logger.error(f"❌ Failed to start CryptoSDCA-AI: {e}")
        raise

    finally:
        logger.warning("🛑 Shutting down CryptoSDCA-AI...")
        
        # Stop background tasks
        if dca_engine:
            await dca_engine.stop()
        
        # Close all components
        for component in [dca_engine, sentiment_analyzer, exchange_manager, ai_validator, indicators]:
            if component:
                try:
                    await component.close()
                except Exception as e:
                    logger.warning(f"Error closing component: {e}")
        
        await close_database()
        logger.success("✅ Shutdown complete")

# FastAPI app
app = FastAPI(
    title="CryptoSDCA-AI",
    version="1.0.0",
    description="Intelligent Multi-Layer DCA Trading Bot with AI Validation",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Static files and templates
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))

# Exception handlers
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

# Include routers
app.include_router(admin.router, prefix="/admin")
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(history.router, prefix="/admin/history")
app.include_router(api_settings.router, prefix="/admin/settings")
app.include_router(trading.router, prefix="/api/trading")
app.include_router(auth_router, prefix="/auth")

# Main routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main landing page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, user: User = Depends(get_current_user)):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.version,
        "components": {
            "database": "connected",
            "exchange_manager": "ready" if exchange_manager else "not_ready",
            "ai_validator": "ready" if ai_validator else "not_ready",
            "dca_engine": "ready" if dca_engine else "not_ready",
        }
    }

@app.get("/info")
async def info():
    """System information"""
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "debug": settings.debug,
        "paper_trading": settings.paper_trading,
        "test_mode": settings.test_mode,
        "exchanges_supported": ["binance", "kucoin", "bingx", "kraken"],
        "ai_services": ["microsoft_copilot", "perplexity"],
        "features": [
            "Multi-exchange trading",
            "AI validation",
            "DCA strategy",
            "Risk management",
            "Real-time monitoring",
            "Web dashboard"
        ]
    }

# WebSocket manager
class WSManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send(self, ws: WebSocket, msg: dict):
        try:
            await ws.send_text(json.dumps(msg))
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            self.disconnect(ws)

    async def broadcast(self, msg: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(msg))
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket(ws: WebSocket):
    if ws_manager:
        await ws_manager.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                # Handle incoming WebSocket messages if needed
                logger.debug(f"Received WebSocket message: {data}")
        except WebSocketDisconnect:
            ws_manager.disconnect(ws)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            ws_manager.disconnect(ws)

async def broadcast_update(event: str, payload: Dict[str, Any]):
    """Broadcast update to all connected WebSocket clients"""
    if ws_manager:
        message = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": payload
        }
        await ws_manager.broadcast(message)

# Utility function to run the application
def run():
    """Run the application"""
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    run()
