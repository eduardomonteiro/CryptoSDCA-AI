"""
api/routes/trading.py - Trading API endpoints
Handles all trading operations, CRUD for trades, sessions, and AI validation
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
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
# Define get_current_user function locally
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

    class Config:
        from_attributes = True

# Web pages
@router.get("/", response_class=HTMLResponse)
async def trading_dashboard(request: Request, user: User = Depends(get_current_user)):
    """Trading dashboard page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Trading Dashboard - CryptoSDCA-AI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h1><i class="fas fa-chart-line"></i> Trading Dashboard</h1>
                    <div id="trading-content">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h5><i class="fas fa-play-circle"></i> Active Trading Sessions</h5>
                                    </div>
                                    <div class="card-body" id="sessions-list">
                                        <div class="text-center">
                                            <div class="spinner-border" role="status">
                                                <span class="visually-hidden">Loading...</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h5><i class="fas fa-history"></i> Recent Trades</h5>
                                    </div>
                                    <div class="card-body" id="trades-list">
                                        <div class="text-center">
                                            <div class="spinner-border" role="status">
                                                <span class="visually-hidden">Loading...</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Load data on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadSessions();
                loadTrades();
            });

            async function loadSessions() {
                try {
                    const response = await fetch('/api/trading/sessions');
                    const sessions = await response.json();
                    displaySessions(sessions);
                } catch (error) {
                    console.error('Error loading sessions:', error);
                }
            }

            async function loadTrades() {
                try {
                    const response = await fetch('/api/trading/trades');
                    const trades = await response.json();
                    displayTrades(trades);
                } catch (error) {
                    console.error('Error loading trades:', error);
                }
            }

            function displaySessions(sessions) {
                const container = document.getElementById('sessions-list');
                if (sessions.length === 0) {
                    container.innerHTML = '<p class="text-muted">No active sessions</p>';
                    return;
                }

                const html = sessions.map(session => `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <strong>${session.session_name}</strong>
                            <span class="badge bg-${session.status === 'active' ? 'success' : 'secondary'}">${session.status}</span>
                        </div>
                        <div class="text-end">
                            <small class="text-muted">${session.total_trades} trades</small><br>
                            <span class="text-${session.total_profit_loss >= 0 ? 'success' : 'danger'}">
                                $${session.total_profit_loss.toFixed(2)}
                            </span>
                        </div>
                    </div>
                `).join('');
                container.innerHTML = html;
            }

            function displayTrades(trades) {
                const container = document.getElementById('trades-list');
                if (trades.length === 0) {
                    container.innerHTML = '<p class="text-muted">No recent trades</p>';
                    return;
                }

                const html = trades.map(trade => `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <strong>${trade.symbol}</strong>
                            <span class="badge bg-${trade.side === 'buy' ? 'success' : 'danger'}">${trade.side}</span>
                        </div>
                        <div class="text-end">
                            <small>${trade.quantity} @ $${trade.price}</small><br>
                            <span class="text-${trade.ai_validation_passed ? 'success' : 'warning'}">
                                <i class="fas fa-${trade.ai_validation_passed ? 'check' : 'question'}"></i>
                            </span>
                        </div>
                    </div>
                `).join('');
                container.innerHTML = html;
            }
        </script>
    </body>
    </html>
    """

# API Endpoints

@router.get("/sessions", response_model=List[TradingSessionResponse])
async def get_trading_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get all trading sessions for the user"""
    sessions = db.query(TradingSession).filter(
        TradingSession.user_id == user.id
    ).order_by(desc(TradingSession.start_time)).all()
    return sessions

@router.post("/sessions", response_model=TradingSessionResponse)
async def create_trading_session(
    session_data: TradingSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new trading session"""
    session = TradingSession(
        user_id=user.id,
        session_name=session_data.session_name,
        max_trades_per_session=session_data.max_trades_per_session,
        min_interval_minutes=session_data.min_interval_minutes,
        max_daily_loss=session_data.max_daily_loss,
        target_profit=session_data.target_profit
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.put("/sessions/{session_id}", response_model=TradingSessionResponse)
async def update_trading_session(
    session_id: int,
    session_data: TradingSessionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update a trading session"""
    session = db.query(TradingSession).filter(
        and_(TradingSession.id == session_id, TradingSession.user_id == user.id)
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Trading session not found")
    
    for field, value in session_data.dict(exclude_unset=True).items():
        setattr(session, field, value)
    
    if session_data.status == "stopped":
        session.end_time = datetime.utcnow()
    
    db.commit()
    db.refresh(session)
    return session

@router.delete("/sessions/{session_id}")
async def delete_trading_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete a trading session"""
    session = db.query(TradingSession).filter(
        and_(TradingSession.id == session_id, TradingSession.user_id == user.id)
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Trading session not found")
    
    db.delete(session)
    db.commit()
    return {"message": "Trading session deleted"}

@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0
):
    """Get user's trades"""
    trades = db.query(Trade).filter(
        Trade.user_id == user.id
    ).order_by(desc(Trade.created_at)).offset(offset).limit(limit).all()
    return trades

@router.post("/trades", response_model=TradeResponse)
async def create_trade(
    trade_data: TradeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new trade with AI validation"""
    
    # Validate exchange and trading pair
    exchange = db.query(Exchange).filter(
        and_(Exchange.id == trade_data.exchange_id, Exchange.user_id == user.id)
    ).first()
    if not exchange:
        raise HTTPException(status_code=404, detail="Exchange not found")
    
    trading_pair = db.query(TradingPair).filter(
        and_(TradingPair.symbol == trade_data.symbol, TradingPair.exchange_id == trade_data.exchange_id)
    ).first()
    if not trading_pair:
        raise HTTPException(status_code=404, detail="Trading pair not found")
    
    # Check if enough time has passed since last trade (5-minute interval)
    last_trade = db.query(Trade).filter(
        and_(Trade.user_id == user.id, Trade.symbol == trade_data.symbol)
    ).order_by(desc(Trade.created_at)).first()
    
    if last_trade and (datetime.utcnow() - last_trade.created_at).total_seconds() < 300:  # 5 minutes
        raise HTTPException(
            status_code=400, 
            detail="Minimum 5-minute interval required between trades"
        )
    
    # Create trade hypothesis for AI validation
    hypothesis = TradeHypothesis(
        pair=trade_data.symbol,
        side=trade_data.side,
        quantity=trade_data.quantity,
        entry_price=trade_data.price or 0.0,
        indicators={},  # Will be populated by indicators
        fear_greed_index=50,  # Will be populated by sentiment analyzer
        news_sentiment=0.0,  # Will be populated by sentiment analyzer
        market_context={},
        timestamp=datetime.utcnow()
    )
    
    # Get technical indicators
    if indicators:
        try:
            market_data = await exchange_manager.get_market_data(trade_data.exchange_id, trade_data.symbol)
            if market_data:
                hypothesis.indicators = await indicators.calculate_all_indicators(
                    trade_data.symbol, market_data
                )
        except Exception as e:
            print(f"Error getting indicators: {e}")
    
    # Get sentiment data
    if sentiment_analyzer:
        try:
            sentiment = await sentiment_analyzer.get_current_sentiment()
            hypothesis.fear_greed_index = sentiment.fear_greed_index
            hypothesis.news_sentiment = sentiment.overall_score
        except Exception as e:
            print(f"Error getting sentiment: {e}")
    
    # AI validation
    ai_consensus = "NO"
    ai_validation_passed = False
    ai_agents_used = []
    
    if ai_validator and ai_validator.is_initialized:
        try:
            validation_results = await ai_validator.validate_trade(hypothesis)
            
            # Determine consensus
            yes_votes = sum(1 for r in validation_results if r.decision.value == "approve")
            no_votes = sum(1 for r in validation_results if r.decision.value == "deny")
            
            if yes_votes > no_votes:
                ai_consensus = "YES"
                ai_validation_passed = True
            elif no_votes > yes_votes:
                ai_consensus = "NO"
                ai_validation_passed = False
            else:
                ai_consensus = "SPLIT"
                ai_validation_passed = False
            
            ai_agents_used = [r.ai_agent for r in validation_results]
            
        except Exception as e:
            print(f"AI validation error: {e}")
            ai_consensus = "ERROR"
            ai_validation_passed = False
    
    # Risk management check
    if risk_manager:
        try:
            trading_allowed = await risk_manager.check_trading_allowed()
            if not trading_allowed:
                raise HTTPException(
                    status_code=400,
                    detail="Trading blocked by risk management"
                )
        except Exception as e:
            print(f"Risk management error: {e}")
    
    # Create the trade
    trade = Trade(
        user_id=user.id,
        exchange_id=trade_data.exchange_id,
        trading_pair_id=trading_pair.id,
        symbol=trade_data.symbol,
        side=OrderSide.BUY if trade_data.side == "buy" else OrderSide.SELL,
        order_type=OrderType.MARKET if trade_data.order_type == "market" else OrderType.LIMIT,
        quantity=trade_data.quantity,
        price=trade_data.price or 0.0,
        total_cost=trade_data.quantity * (trade_data.price or 0.0),
        ai_validation_passed=ai_validation_passed,
        ai_agents_used=ai_agents_used,
        ai_consensus=ai_consensus,
        market_sentiment=hypothesis.news_sentiment,
        fear_greed_index=hypothesis.fear_greed_index,
        technical_indicators=hypothesis.indicators
    )
    
    db.add(trade)
    db.commit()
    db.refresh(trade)
    
    # Log AI validation results
    if ai_validator and validation_results:
        for result in validation_results:
            validation_log = AIValidationLog(
                trade_id=trade.id,
                ai_agent_id=1,  # Would need to get actual agent ID
                validation_request=hypothesis.__dict__,
                validation_response=result.__dict__,
                decision=result.decision.value.upper(),
                confidence_score=result.confidence,
                reasoning=result.reasoning,
                response_time=datetime.utcnow(),
                processing_time_ms=int(result.response_time * 1000),
                status="completed"
            )
            db.add(validation_log)
    
    db.commit()
    return trade

@router.put("/trades/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_data: TradeUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update a trade"""
    trade = db.query(Trade).filter(
        and_(Trade.id == trade_id, Trade.user_id == user.id)
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    for field, value in trade_data.dict(exclude_unset=True).items():
        setattr(trade, field, value)
    
    if trade_data.status == "executed":
        trade.executed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(trade)
    return trade

@router.delete("/trades/{trade_id}")
async def delete_trade(
    trade_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete a trade"""
    trade = db.query(Trade).filter(
        and_(Trade.id == trade_id, Trade.user_id == user.id)
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    db.delete(trade)
    db.commit()
    return {"message": "Trade deleted"}

@router.get("/trades/{trade_id}/validations")
async def get_trade_validations(
    trade_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get AI validation logs for a specific trade"""
    trade = db.query(Trade).filter(
        and_(Trade.id == trade_id, Trade.user_id == user.id)
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    validations = db.query(AIValidationLog).filter(
        AIValidationLog.trade_id == trade_id
    ).all()
    
    return validations

@router.get("/statistics")
async def get_trading_statistics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get trading statistics for the user"""
    
    # Get total trades
    total_trades = db.query(Trade).filter(Trade.user_id == user.id).count()
    
    # Get successful trades (executed)
    successful_trades = db.query(Trade).filter(
        and_(Trade.user_id == user.id, Trade.status == OrderStatus.EXECUTED)
    ).count()
    
    # Get AI validation statistics
    ai_validated_trades = db.query(Trade).filter(
        and_(Trade.user_id == user.id, Trade.ai_validation_passed == True)
    ).count()
    
    # Get recent trades (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_trades = db.query(Trade).filter(
        and_(Trade.user_id == user.id, Trade.created_at >= yesterday)
    ).count()
    
    return {
        "total_trades": total_trades,
        "successful_trades": successful_trades,
        "success_rate": (successful_trades / total_trades * 100) if total_trades > 0 else 0,
        "ai_validated_trades": ai_validated_trades,
        "ai_validation_rate": (ai_validated_trades / total_trades * 100) if total_trades > 0 else 0,
        "recent_trades_24h": recent_trades
    }
