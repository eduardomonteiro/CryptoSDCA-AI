"""
api/routes/trading.py - Trading API endpoints
Handles all trading operations, CRUD for trades, sessions, and AI validation
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import asyncio
import json

from src.database import get_db_session
from src.models.models import (
    User, Trade, TradingSession, AIValidationLog, Exchange, 
    TradingPair, AIAgent, OrderStatus, OrderSide, OrderType
)
from src.core.ai_validator import AIValidator, TradeHypothesis
from src.core.indicators import TechnicalIndicators
from src.core.sentiment_analyzer import SentimentAnalyzer
from src.core.risk_manager import RiskManager
from src.core.exchange_manager import ExchangeManager
from src.exceptions import TradingError, AIValidationError

router = APIRouter()

# Global instances (will be initialized in main.py)
ai_validator: Optional[AIValidator] = None
indicators: Optional[TechnicalIndicators] = None
sentiment_analyzer: Optional[SentimentAnalyzer] = None
risk_manager: Optional[RiskManager] = None
exchange_manager: Optional[ExchangeManager] = None

# Pydantic models for API
from pydantic import BaseModel, Field
from typing import Optional as Opt

class TradeCreate(BaseModel):
    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="buy or sell")
    quantity: float = Field(..., description="Trade quantity")
    price: Opt[float] = Field(None, description="Limit price (optional for market orders)")
    order_type: str = Field("market", description="market or limit")
    exchange_id: int = Field(..., description="Exchange ID")
    session_id: Opt[int] = Field(None, description="Trading session ID")

class TradeUpdate(BaseModel):
    status: Opt[str] = None
    price: Opt[float] = None
    quantity: Opt[float] = None

class TradingSessionCreate(BaseModel):
    session_name: str = Field(..., description="Session name")
    max_trades_per_session: int = Field(100, description="Maximum trades per session")
    min_interval_minutes: int = Field(5, description="Minimum interval between trades")
    max_daily_loss: float = Field(100.0, description="Maximum daily loss")
    target_profit: float = Field(5.0, description="Target profit percentage")

class TradingSessionUpdate(BaseModel):
    status: Opt[str] = None
    session_name: Opt[str] = None
    max_trades_per_session: Opt[int] = None
    min_interval_minutes: Opt[int] = None
    max_daily_loss: Opt[float] = None
    target_profit: Opt[float] = None

class TradeResponse(BaseModel):
    id: int
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float
    total_cost: float
    status: str
    ai_validation_passed: Opt[bool] = None
    ai_consensus: Opt[str] = None
    created_at: datetime
    executed_at: Opt[datetime] = None

    class Config:
        from_attributes = True

class TradingSessionResponse(BaseModel):
    id: int
    session_name: str
    status: str
    start_time: datetime
    end_time: Opt[datetime] = None
    total_trades: int
    successful_trades: int
    total_profit_loss: float
    min_interval_minutes: int
    max_daily_loss: float
    target_profit: float

    class Config:
        from_attributes = True

# Bot control endpoints
@router.post("/start")
async def start_trading_bot(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Start the trading bot"""
    try:
        # Check if bot is already running
        active_session = db.query(TradingSession).filter_by(status="active").first()
        if active_session:
            raise HTTPException(status_code=400, detail="Trading bot is already running")
        
        # Create new trading session
        session = TradingSession(
            user_id=user.id,
            session_name=f"Auto Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            status="active",
            max_trades_per_session=100,
            min_interval_minutes=5,
            max_daily_loss=100.0,
            target_profit=1.0
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return {
            "success": True,
            "message": "Trading bot started successfully",
            "session_id": session.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start trading bot: {str(e)}")

@router.post("/stop")
async def stop_trading_bot(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Stop the trading bot"""
    try:
        # Find active session
        active_session = db.query(TradingSession).filter_by(status="active").first()
        if not active_session:
            raise HTTPException(status_code=400, detail="No active trading session found")
        
        # Stop the session
        active_session.status = "stopped"
        active_session.end_time = datetime.now()
        db.commit()
        
        return {
            "success": True,
            "message": "Trading bot stopped successfully",
            "session_id": active_session.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to stop trading bot: {str(e)}")

@router.post("/pause")
async def pause_trading_bot(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Pause the trading bot"""
    try:
        # Find active session
        active_session = db.query(TradingSession).filter_by(status="active").first()
        if not active_session:
            raise HTTPException(status_code=400, detail="No active trading session found")
        
        # Pause the session
        active_session.status = "paused"
        db.commit()
        
        return {
            "success": True,
            "message": "Trading bot paused successfully",
            "session_id": active_session.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to pause trading bot: {str(e)}")

@router.post("/resume")
async def resume_trading_bot(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Resume the trading bot"""
    try:
        # Find paused session
        paused_session = db.query(TradingSession).filter_by(status="paused").first()
        if not paused_session:
            raise HTTPException(status_code=400, detail="No paused trading session found")
        
        # Resume the session
        paused_session.status = "active"
        db.commit()
        
        return {
            "success": True,
            "message": "Trading bot resumed successfully",
            "session_id": paused_session.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to resume trading bot: {str(e)}")

@router.post("/emergency-sell")
async def emergency_sell_all(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Emergency sell all positions"""
    try:
        # Find all open trades
        open_trades = db.query(Trade).filter_by(status="open").all()
        
        if not open_trades:
            return {
                "success": True,
                "message": "No open positions to sell",
                "trades_affected": 0
            }
        
        # Mark all trades as sold
        for trade in open_trades:
            trade.status = "closed"
            trade.executed_at = datetime.now()
        
        # Stop trading session
        active_session = db.query(TradingSession).filter_by(status="active").first()
        if active_session:
            active_session.status = "stopped"
            active_session.end_time = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Emergency sell executed for {len(open_trades)} positions",
            "trades_affected": len(open_trades)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to execute emergency sell: {str(e)}")

@router.get("/status")
async def get_trading_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get current trading bot status"""
    try:
        # Get active session
        active_session = db.query(TradingSession).filter_by(status="active").first()
        paused_session = db.query(TradingSession).filter_by(status="paused").first()
        
        # Count open trades
        open_trades = db.query(Trade).filter_by(status="open").count()
        
        # Calculate total profit/loss
        total_pnl = db.query(Trade).filter(Trade.status == "closed").with_entities(
            db.func.sum(Trade.profit_loss)
        ).scalar() or 0.0
        
        status_info = {
            "bot_status": "stopped",
            "session_id": None,
            "open_trades": open_trades,
            "total_pnl": total_pnl,
            "session_name": None
        }
        
        if active_session:
            status_info.update({
                "bot_status": "active",
                "session_id": active_session.id,
                "session_name": active_session.session_name
            })
        elif paused_session:
            status_info.update({
                "bot_status": "paused",
                "session_id": paused_session.id,
                "session_name": paused_session.session_name
            })
        
        return status_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trading status: {str(e)}")

# Trading sessions CRUD
@router.get("/sessions", response_model=List[TradingSessionResponse])
async def get_trading_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0
):
    """Get all trading sessions"""
    sessions = db.query(TradingSession).filter_by(user_id=user.id).order_by(
        desc(TradingSession.start_time)
    ).offset(offset).limit(limit).all()
    
    return sessions

@router.post("/sessions", response_model=TradingSessionResponse)
async def create_trading_session(
    session_data: TradingSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new trading session"""
    try:
        session = TradingSession(
            user_id=user.id,
            session_name=session_data.session_name,
            status="active",
            max_trades_per_session=session_data.max_trades_per_session,
            min_interval_minutes=session_data.min_interval_minutes,
            max_daily_loss=session_data.max_daily_loss,
            target_profit=session_data.target_profit
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.put("/sessions/{session_id}", response_model=TradingSessionResponse)
async def update_trading_session(
    session_id: int,
    session_data: TradingSessionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update a trading session"""
    try:
        session = db.query(TradingSession).filter_by(id=session_id, user_id=user.id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update fields
        for field, value in session_data.dict(exclude_unset=True).items():
            setattr(session, field, value)
        
        db.commit()
        db.refresh(session)
        return session
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")

@router.delete("/sessions/{session_id}")
async def delete_trading_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete a trading session"""
    try:
        session = db.query(TradingSession).filter_by(id=session_id, user_id=user.id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        db.delete(session)
        db.commit()
        
        return {"success": True, "message": "Session deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

# Trades CRUD
@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None
):
    """Get all trades"""
    query = db.query(Trade).filter_by(user_id=user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    trades = query.order_by(desc(Trade.created_at)).offset(offset).limit(limit).all()
    return trades

@router.post("/trades", response_model=TradeResponse)
async def create_trade(
    trade_data: TradeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new trade"""
    try:
        # Validate exchange exists
        exchange = db.query(Exchange).filter_by(id=trade_data.exchange_id).first()
        if not exchange:
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        # Calculate total cost
        total_cost = trade_data.quantity * (trade_data.price or 0)
        
        trade = Trade(
            user_id=user.id,
            exchange_id=trade_data.exchange_id,
            trading_pair_id=1,  # Default trading pair
            session_id=trade_data.session_id,
            symbol=trade_data.symbol,
            side=trade_data.side,
            order_type=trade_data.order_type,
            quantity=trade_data.quantity,
            price=trade_data.price or 0,
            total_cost=total_cost,
            status="pending",
            ai_validation_required=True
        )
        
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create trade: {str(e)}")

@router.put("/trades/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_data: TradeUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update a trade"""
    try:
        trade = db.query(Trade).filter_by(id=trade_id, user_id=user.id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        # Update fields
        for field, value in trade_data.dict(exclude_unset=True).items():
            setattr(trade, field, value)
        
        db.commit()
        db.refresh(trade)
        return trade
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update trade: {str(e)}")

@router.delete("/trades/{trade_id}")
async def delete_trade(
    trade_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete a trade"""
    try:
        trade = db.query(Trade).filter_by(id=trade_id, user_id=user.id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        db.delete(trade)
        db.commit()
        
        return {"success": True, "message": "Trade deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete trade: {str(e)}")

@router.get("/statistics")
async def get_trading_statistics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get trading statistics"""
    try:
        # Total trades
        total_trades = db.query(Trade).filter_by(user_id=user.id).count()
        
        # Closed trades
        closed_trades = db.query(Trade).filter_by(user_id=user.id, status="closed").count()
        
        # Open trades
        open_trades = db.query(Trade).filter_by(user_id=user.id, status="open").count()
        
        # Total profit/loss
        total_pnl = db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.status == "closed"
        ).with_entities(db.func.sum(Trade.profit_loss)).scalar() or 0.0
        
        # Win rate
        winning_trades = db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.status == "closed",
            Trade.profit_loss > 0
        ).count()
        
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "closed_trades": closed_trades,
            "open_trades": open_trades,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "winning_trades": winning_trades
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

# Helper function for authentication
def get_current_user(request: Request, db: Session = Depends(get_db_session)) -> User:
    """Get current user from session"""
    # This is a simplified version - in production you'd want proper session management
    # For now, we'll return a default user for testing
    user = db.query(User).first()
    if not user:
        # Create a test user if none exists
        user = User(
            username="testuser",
            email="test@example.com",
            is_admin=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
