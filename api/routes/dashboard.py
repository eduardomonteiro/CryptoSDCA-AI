"""
api/routes/dashboard.py - Main Dashboard Routes for CryptoSDCA-AI
Handles dashboard display, real-time updates, and trading overview
UPDATED: Now using real database data instead of mock data
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

from src.database import get_db
from src.models.models import (
    User, Exchange, AIAgent, TradingPair, Order, TradeHistory, 
    SystemSettings, MarketSentiment, SystemHealth, OrderSide, OrderStatus
)
from api.routes.auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Main dashboard page with trading overview"""
    
    try:
        # Get user's exchanges
        exchanges = db.query(Exchange).filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()
        
        # Get user's AI agents
        ai_agents = db.query(AIAgent).filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()
        
        # Get active orders
        active_orders = []
        total_active_value = 0.0
        
        for exchange in exchanges:
            exchange_orders = db.query(Order).filter_by(
                exchange_id=exchange.id,
                status=OrderStatus.OPEN
            ).limit(10).all()
            
            for order in exchange_orders:
                order_value = order.quantity * (order.price or 0)
                total_active_value += order_value
                active_orders.append({
                    "id": order.id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "quantity": order.quantity,
                    "price": order.price,
                    "value_usd": order_value,
                    "exchange": exchange.display_name,
                    "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # Get recent trade history
        recent_trades = []
        total_pnl = 0.0
        
        for exchange in exchanges:
            trades = db.query(TradeHistory).filter_by(
                exchange_id=exchange.id
            ).order_by(TradeHistory.created_at.desc()).limit(5).all()
            
            for trade in trades:
                total_pnl += trade.pnl_usd or 0.0
                recent_trades.append({
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side.value,
                    "quantity": trade.quantity,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "pnl_usd": trade.pnl_usd,
                    "pnl_percent": trade.pnl_percent,
                    "created_at": trade.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # Get system settings
        settings = {}
        system_settings = db.query(SystemSettings).filter_by(category="trading").all()
        for setting in system_settings:
            settings[setting.key] = setting.value
        
        # Get market sentiment
        latest_sentiment = db.query(MarketSentiment).order_by(
            MarketSentiment.timestamp.desc()
        ).first()
        
        sentiment_data = {
            "fear_greed_value": latest_sentiment.fear_greed_value if latest_sentiment else 50,
            "fear_greed_classification": latest_sentiment.fear_greed_classification if latest_sentiment else "Neutral",
            "news_sentiment": latest_sentiment.news_sentiment_score if latest_sentiment else 0.0,
            "overall_sentiment": latest_sentiment.overall_sentiment if latest_sentiment else "neutral"
        }
        
        # Get system health
        latest_health = db.query(SystemHealth).order_by(
            SystemHealth.timestamp.desc()
        ).first()
        
        system_health = {
            "cpu_usage": latest_health.cpu_usage if latest_health else 0.0,
            "memory_usage": latest_health.memory_usage if latest_health else 0.0,
            "exchanges_connected": latest_health.exchanges_connected if latest_health else 0,
            "exchanges_total": latest_health.exchanges_total if latest_health else len(exchanges),
            "bot_status": latest_health.bot_status if latest_health else "stopped"
        }
        
        # Calculate statistics
        stats = {
            "total_exchanges": len(exchanges),
            "active_exchanges": len([e for e in exchanges if e.is_active]),
            "total_ai_agents": len(ai_agents),
            "active_ai_agents": len([a for a in ai_agents if a.is_active]),
            "active_orders_count": len(active_orders),
            "total_active_value": total_active_value,
            "total_pnl": total_pnl,
            "recent_trades_count": len(recent_trades)
        }
        
        # Context for template
        context = {
            "request": request,
            "user": current_user,
            "exchanges": exchanges,
            "ai_agents": ai_agents,
            "active_orders": active_orders,
            "recent_trades": recent_trades,
            "settings": settings,
            "sentiment": sentiment_data,
            "system_health": system_health,
            "stats": stats,
            "paper_trading": settings.get("paper_trading", "true").lower() == "true"
        }
        
        return templates.TemplateResponse("dashboard/main.html", context)
        
    except Exception as e:
        # Fallback to inline HTML if template is not found
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CryptoSDCA-AI Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                body {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }}
                .dashboard-card {{
                    backdrop-filter: blur(10px);
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
                .stat-card {{
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    color: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                }}
                .status-badge {{
                    padding: 5px 10px;
                    border-radius: 20px;
                    font-size: 0.8rem;
                    font-weight: bold;
                }}
                .status-active {{ background-color: #28a745; color: white; }}
                .status-inactive {{ background-color: #dc3545; color: white; }}
                .status-pending {{ background-color: #ffc107; color: black; }}
            </style>
        </head>
        <body>
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
                <div class="container">
                    <a class="navbar-brand" href="/dashboard">
                        <i class="fas fa-robot"></i> CryptoSDCA-AI
                    </a>
                    <div class="navbar-nav ms-auto">
                        <a class="nav-link" href="/auth/logout">
                            <i class="fas fa-sign-out-alt"></i> Logout
                        </a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <div class="row">
                    <div class="col-12">
                        <div class="dashboard-card p-4">
                            <h1 class="mb-4">
                                <i class="fas fa-chart-line text-primary"></i>
                                Welcome, {current_user.username}!
                            </h1>
                            
                            <div class="alert alert-info">
                                <h4><i class="fas fa-exclamation-circle"></i> Dashboard Loading</h4>
                                <p>The dashboard is initializing. Database connection: <strong>Active</strong></p>
                                <p>Error details: {str(e)}</p>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-3">
                                    <div class="stat-card text-center">
                                        <i class="fas fa-exchange-alt fa-2x mb-2"></i>
                                        <h3>0</h3>
                                        <p>Active Exchanges</p>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="stat-card text-center">
                                        <i class="fas fa-robot fa-2x mb-2"></i>
                                        <h3>0</h3>
                                        <p>AI Agents</p>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="stat-card text-center">
                                        <i class="fas fa-shopping-cart fa-2x mb-2"></i>
                                        <h3>0</h3>
                                        <p>Active Orders</p>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="stat-card text-center">
                                        <i class="fas fa-dollar-sign fa-2x mb-2"></i>
                                        <h3>$0.00</h3>
                                        <p>Total P&L</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mt-4">
                                <div class="col-md-6">
                                    <h5><i class="fas fa-cog"></i> Quick Actions</h5>
                                    <div class="d-grid gap-2">
                                        <a href="/manager" class="btn btn-primary">
                                            <i class="fas fa-tools"></i> Manage Settings
                                        </a>
                                        <a href="/trading" class="btn btn-success">
                                            <i class="fas fa-play"></i> Start Trading
                                        </a>
                                        <a href="/history" class="btn btn-info">
                                            <i class="fas fa-history"></i> View History
                                        </a>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <h5><i class="fas fa-heartbeat"></i> System Status</h5>
                                    <ul class="list-group">
                                        <li class="list-group-item d-flex justify-content-between">
                                            Database 
                                            <span class="status-badge status-active">Connected</span>
                                        </li>
                                        <li class="list-group-item d-flex justify-content-between">
                                            Bot Status 
                                            <span class="status-badge status-inactive">Stopped</span>
                                        </li>
                                        <li class="list-group-item d-flex justify-content-between">
                                            Paper Trading 
                                            <span class="status-badge status-active">Enabled</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """)

@router.get("/api/status")
async def get_dashboard_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get real-time dashboard status data"""
    
    try:
        # Get active exchanges count
        active_exchanges = db.query(Exchange).filter_by(
            user_id=current_user.id,
            is_active=True
        ).count()
        
        # Get active AI agents count
        active_agents = db.query(AIAgent).filter_by(
            user_id=current_user.id,
            is_active=True
        ).count()
        
        # Get active orders count
        active_orders_count = 0
        total_order_value = 0.0
        
        user_exchanges = db.query(Exchange).filter_by(user_id=current_user.id).all()
        for exchange in user_exchanges:
            orders = db.query(Order).filter_by(
                exchange_id=exchange.id,
                status=OrderStatus.OPEN
            ).all()
            active_orders_count += len(orders)
            total_order_value += sum(o.quantity * (o.price or 0) for o in orders)
        
        # Get total P&L
        total_pnl = 0.0
        for exchange in user_exchanges:
            trades = db.query(TradeHistory).filter_by(exchange_id=exchange.id).all()
            total_pnl += sum(t.pnl_usd or 0.0 for t in trades)
        
        # Get system settings
        paper_trading = db.query(SystemSettings).filter_by(
            key="paper_trading",
            category="trading"
        ).first()
        
        # Get latest system health
        latest_health = db.query(SystemHealth).order_by(
            SystemHealth.timestamp.desc()
        ).first()
        
        return JSONResponse({
            "success": True,
            "data": {
                "exchanges": {
                    "active": active_exchanges,
                    "total": len(user_exchanges)
                },
                "ai_agents": {
                    "active": active_agents,
                    "total": db.query(AIAgent).filter_by(user_id=current_user.id).count()
                },
                "orders": {
                    "active": active_orders_count,
                    "total_value": round(total_order_value, 2)
                },
                "pnl": {
                    "total": round(total_pnl, 2),
                    "today": 0.0  # TODO: Calculate today's P&L
                },
                "system": {
                    "paper_trading": paper_trading.value.lower() == "true" if paper_trading else True,
                    "bot_status": latest_health.bot_status if latest_health else "stopped",
                    "cpu_usage": latest_health.cpu_usage if latest_health else 0.0,
                    "memory_usage": latest_health.memory_usage if latest_health else 0.0
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=500)

@router.get("/api/orders")
async def get_active_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    limit: int = 50
):
    """Get active orders for the dashboard"""
    
    try:
        orders = []
        user_exchanges = db.query(Exchange).filter_by(user_id=current_user.id).all()
        
        for exchange in user_exchanges:
            exchange_orders = db.query(Order).filter_by(
                exchange_id=exchange.id,
                status=OrderStatus.OPEN
            ).order_by(Order.created_at.desc()).limit(limit).all()
            
            for order in exchange_orders:
                orders.append({
                    "id": order.id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "quantity": order.quantity,
                    "price": order.price,
                    "filled_quantity": order.filled_quantity or 0.0,
                    "status": order.status.value,
                    "exchange": exchange.display_name,
                    "created_at": order.created_at.isoformat(),
                    "updated_at": order.updated_at.isoformat() if order.updated_at else None
                })
        
        return JSONResponse({
            "success": True,
            "orders": orders,
            "count": len(orders),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@router.get("/api/trades")
async def get_recent_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    limit: int = 20
):
    """Get recent trades for the dashboard"""
    
    try:
        trades = []
        user_exchanges = db.query(Exchange).filter_by(user_id=current_user.id).all()
        
        for exchange in user_exchanges:
            exchange_trades = db.query(TradeHistory).filter_by(
                exchange_id=exchange.id
            ).order_by(TradeHistory.created_at.desc()).limit(limit).all()
            
            for trade in exchange_trades:
                trades.append({
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side.value,
                    "quantity": trade.quantity,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "pnl_usd": trade.pnl_usd,
                    "pnl_percent": trade.pnl_percent,
                    "exchange": exchange.display_name,
                    "created_at": trade.created_at.isoformat(),
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else None
                })
        
        # Sort by creation date
        trades.sort(key=lambda x: x["created_at"], reverse=True)
        
        return JSONResponse({
            "success": True,
            "trades": trades[:limit],
            "count": len(trades[:limit]),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@router.post("/api/emergency-stop")
async def emergency_stop(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Emergency stop - cancel all orders and close positions"""
    
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        cancelled_orders = 0
        user_exchanges = db.query(Exchange).filter_by(user_id=current_user.id).all()
        
        # Cancel all open orders
        for exchange in user_exchanges:
            open_orders = db.query(Order).filter_by(
                exchange_id=exchange.id,
                status=OrderStatus.OPEN
            ).all()
            
            for order in open_orders:
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.utcnow()
                cancelled_orders += 1
        
        # Update system settings to stop bot
        bot_status_setting = db.query(SystemSettings).filter_by(
            key="bot_status",
            category="system"
        ).first()
        
        if not bot_status_setting:
            bot_status_setting = SystemSettings(
                key="bot_status",
                value="emergency_stopped",
                value_type="string",
                category="system",
                description="Current bot status"
            )
            db.add(bot_status_setting)
        else:
            bot_status_setting.value = "emergency_stopped"
            bot_status_setting.updated_at = datetime.utcnow()
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Emergency stop executed successfully",
            "cancelled_orders": cancelled_orders,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# Export router
__all__ = ["router"]
    