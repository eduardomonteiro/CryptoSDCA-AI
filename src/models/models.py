"""
SQLAlchemy models for CryptoSDCA-AI Trading Bot

This module defines all database models including users, exchanges,
trading pairs, orders, AI agents, and system settings.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, Enum, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from src.database import Base


class OrderSide(PyEnum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OrderType(PyEnum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(PyEnum):
    """Order status enumeration"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELED = "canceled"
    FAILED = "failed"


class TradingPairStatus(PyEnum):
    """Trading pair status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"


class AIDecision(PyEnum):
    """AI decision enumeration"""
    APPROVE = "approve"
    DENY = "deny"
    PENDING = "pending"


class ExchangeStatus(PyEnum):
    """Exchange connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


# =============================================================================
# User Management Models
# =============================================================================

class User(Base):
    """User authentication and management"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)

    # Relationships
    exchanges = relationship("Exchange", back_populates="user")
    ai_agents = relationship("AIAgent", back_populates="user")
    trade_history = relationship("TradeHistory", back_populates="user")

    def __repr__(self):
        return f"<User(username='{self.username}', is_admin={self.is_admin})>"


# =============================================================================
# Exchange Management Models
# =============================================================================

class Exchange(Base):
    """Exchange configuration and API keys"""
    __tablename__ = "exchanges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)  # binance, kucoin, etc.
    display_name = Column(String(100), nullable=False)
    api_key = Column(String(255), nullable=False)
    api_secret = Column(String(255), nullable=False)
    api_passphrase = Column(String(255), nullable=True)  # For KuCoin
    is_testnet = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    status = Column(Enum(ExchangeStatus), default=ExchangeStatus.DISCONNECTED)
    last_connected = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Rate limiting info
    rate_limit = Column(Integer, default=1000)  # requests per minute
    rate_limit_remaining = Column(Integer, default=1000)
    rate_limit_reset = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="exchanges")
    trading_pairs = relationship("TradingPair", back_populates="exchange")
    orders = relationship("Order", back_populates="exchange")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='unique_user_exchange'),
        Index('idx_exchange_user_active', 'user_id', 'is_active'),
    )

    def __repr__(self):
        return f"<Exchange(name='{self.name}', user_id={self.user_id}, active={self.is_active})>"


# =============================================================================
# AI Agent Models
# =============================================================================

class AIAgent(Base):
    """AI agent configuration (Copilot & Perplexity)"""
    __tablename__ = "ai_agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)  # 'copilot' or 'perplexity'
    api_key = Column(String(255), nullable=True)
    api_secret = Column(String(255), nullable=True)
    endpoint_url = Column(String(255), nullable=True)
    model_name = Column(String(100), nullable=True)
    role_description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # For ordering multiple agents
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Performance tracking
    total_decisions = Column(Integer, default=0)
    correct_decisions = Column(Integer, default=0)
    accuracy_rate = Column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="ai_agents")
    ai_decisions = relationship("TradeDecision", back_populates="ai_agent")

    __table_args__ = (
        Index('idx_ai_agent_user_type', 'user_id', 'agent_type'),
    )

    def __repr__(self):
        return f"<AIAgent(name='{self.name}', type='{self.agent_type}', active={self.is_active})>"


# =============================================================================
# Trading Models
# =============================================================================

class TradingPair(Base):
    """Trading pair configuration"""
    __tablename__ = "trading_pairs"

    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"), nullable=False)
    symbol = Column(String(20), nullable=False)  # BTC/USDT
    base_asset = Column(String(10), nullable=False)  # BTC
    quote_asset = Column(String(10), nullable=False)  # USDT
    status = Column(Enum(TradingPairStatus), default=TradingPairStatus.ACTIVE)

    # DCA Configuration
    target_profit_percent = Column(Float, default=1.0)
    stop_loss_percent = Column(Float, default=-3.0)
    max_position_size_usd = Column(Float, default=1000.0)
    grid_size = Column(Integer, default=10)

    # Market data
    current_price = Column(Float, nullable=True)
    price_24h_change = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)

    # Trading stats
    total_trades = Column(Integer, default=0)
    profitable_trades = Column(Integer, default=0)
    total_profit_loss = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    exchange = relationship("Exchange", back_populates="trading_pairs")
    orders = relationship("Order", back_populates="trading_pair")
    trade_decisions = relationship("TradeDecision", back_populates="trading_pair")

    __table_args__ = (
        UniqueConstraint('exchange_id', 'symbol', name='unique_exchange_symbol'),
        Index('idx_pair_exchange_status', 'exchange_id', 'status'),
    )

    def __repr__(self):
        return f"<TradingPair(symbol='{self.symbol}', exchange_id={self.exchange_id})>"


class Order(Base):
    """Order tracking and management"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"), nullable=False)
    trading_pair_id = Column(Integer, ForeignKey("trading_pairs.id"), nullable=False)

    # Order details
    exchange_order_id = Column(String(100), nullable=True)  # Exchange's order ID
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)

    # Price and quantity
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    filled_quantity = Column(Float, default=0.0)
    remaining_quantity = Column(Float, nullable=True)

    # Execution details
    average_fill_price = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    fees = Column(Float, default=0.0)
    fee_currency = Column(String(10), nullable=True)

    # Grid trading info
    grid_level = Column(Integer, nullable=True)
    is_grid_order = Column(Boolean, default=False)
    parent_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    filled_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationships
    exchange = relationship("Exchange", back_populates="orders")
    trading_pair = relationship("TradingPair", back_populates="orders")
    child_orders = relationship("Order", backref=backref("parent_order", remote_side=[id]))

    __table_args__ = (
        Index('idx_order_exchange_pair', 'exchange_id', 'trading_pair_id'),
        Index('idx_order_status_created', 'status', 'created_at'),
    )

    def __repr__(self):
        return f"<Order(side='{self.side}', price={self.price}, status='{self.status}')>"


# =============================================================================
# AI Decision Models
# =============================================================================

class TradeDecision(Base):
    """AI trading decisions and validation"""
    __tablename__ = "trade_decisions"

    id = Column(Integer, primary_key=True, index=True)
    trading_pair_id = Column(Integer, ForeignKey("trading_pairs.id"), nullable=False)
    ai_agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=False)

    # Decision details
    decision = Column(Enum(AIDecision), nullable=False)
    confidence_score = Column(Float, nullable=True)  # 0-1
    reasoning = Column(Text, nullable=True)

    # Market context
    market_data = Column(JSON, nullable=True)  # Price, indicators, etc.
    sentiment_data = Column(JSON, nullable=True)  # Fear/greed, news

    # Trade proposal
    proposed_side = Column(Enum(OrderSide), nullable=True)
    proposed_quantity = Column(Float, nullable=True)
    proposed_price = Column(Float, nullable=True)

    # Outcome tracking
    was_executed = Column(Boolean, default=False)
    execution_result = Column(String(50), nullable=True)  # 'profit', 'loss', 'pending'
    actual_profit_loss = Column(Float, nullable=True)

    created_at = Column(DateTime, default=func.now())
    executed_at = Column(DateTime, nullable=True)

    # Relationships
    trading_pair = relationship("TradingPair", back_populates="trade_decisions")
    ai_agent = relationship("AIAgent", back_populates="ai_decisions")

    __table_args__ = (
        Index('idx_decision_pair_agent', 'trading_pair_id', 'ai_agent_id'),
        Index('idx_decision_created', 'created_at'),
    )

    def __repr__(self):
        return f"<TradeDecision(decision='{self.decision}', agent_id={self.ai_agent_id})>"


# =============================================================================
# Trading History Models
# =============================================================================

class TradeHistory(Base):
    """Complete trade execution history"""
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Trade identification
    trade_group_id = Column(String(50), nullable=True)  # Group related trades
    symbol = Column(String(20), nullable=False)
    exchange_name = Column(String(50), nullable=False)

    # Trade details
    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)

    # P&L tracking
    profit_loss = Column(Float, nullable=True)
    profit_loss_percent = Column(Float, nullable=True)

    # Market conditions at execution
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    fear_greed_index = Column(Integer, nullable=True)
    market_sentiment = Column(String(20), nullable=True)

    # AI involvement
    ai_approved = Column(Boolean, default=False)
    ai_agents_used = Column(JSON, nullable=True)  # List of agent IDs

    executed_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="trade_history")

    __table_args__ = (
        Index('idx_history_user_symbol', 'user_id', 'symbol'),
        Index('idx_history_executed', 'executed_at'),
    )

    def __repr__(self):
        return f"<TradeHistory(symbol='{self.symbol}', side='{self.side}', profit_loss={self.profit_loss})>"


# =============================================================================
# System Configuration Models
# =============================================================================

class SystemSettings(Base):
    """System-wide configuration settings"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # trading, indicators, risk, etc.
    is_encrypted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_settings_category', 'category'),
    )

    def __repr__(self):
        return f"<SystemSettings(key='{self.key}', category='{self.category}')>"


class NewsSource(Base):
    """News sources for sentiment analysis"""
    __tablename__ = "news_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(255), nullable=False)
    source_type = Column(String(20), default="rss")  # rss, api, websocket
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)
    update_interval_minutes = Column(Integer, default=15)

    # Authentication if needed
    api_key = Column(String(255), nullable=True)
    api_secret = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_updated = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<NewsSource(name='{self.name}', active={self.is_active})>"


class MarketSentiment(Base):
    """Market sentiment data storage"""
    __tablename__ = "market_sentiment"

    id = Column(Integer, primary_key=True, index=True)

    # Fear & Greed Index
    fear_greed_value = Column(Integer, nullable=True)  # 0-100
    fear_greed_classification = Column(String(20), nullable=True)  # Fear, Greed, etc.

    # News sentiment
    news_sentiment_score = Column(Float, nullable=True)  # -1 to 1
    positive_news_count = Column(Integer, default=0)
    negative_news_count = Column(Integer, default=0)
    neutral_news_count = Column(Integer, default=0)

    # Social media sentiment (if available)
    social_sentiment_score = Column(Float, nullable=True)

    # Aggregated data
    overall_sentiment = Column(String(20), nullable=True)  # bullish, bearish, neutral
    sentiment_strength = Column(Float, nullable=True)  # 0-1

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_sentiment_created', 'created_at'),
    )

    def __repr__(self):
        return f"<MarketSentiment(fng={self.fear_greed_value}, sentiment='{self.overall_sentiment}')>"


# =============================================================================
# Performance Monitoring Models
# =============================================================================

class SystemHealth(Base):
    """System health monitoring"""
    __tablename__ = "system_health"

    id = Column(Integer, primary_key=True, index=True)

    # System metrics
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)

    # Database metrics
    db_connections = Column(Integer, nullable=True)
    db_response_time_ms = Column(Float, nullable=True)

    # Exchange connectivity
    exchanges_connected = Column(Integer, default=0)
    exchanges_total = Column(Integer, default=0)

    # AI agents status
    ai_agents_active = Column(Integer, default=0)
    ai_response_time_ms = Column(Float, nullable=True)

    # Trading activity
    orders_per_hour = Column(Integer, default=0)
    trades_per_hour = Column(Integer, default=0)

    # Errors and warnings
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)

    timestamp = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_health_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<SystemHealth(timestamp={self.timestamp}, exchanges={self.exchanges_connected}/{self.exchanges_total})>"


# Create all tables function for easy import
def create_all_tables():
    """Create all database tables"""
    from src.database import sync_engine
    Base.metadata.create_all(bind=sync_engine)


# Export all models
__all__ = [
    "User", "Exchange", "AIAgent", "TradingPair", "Order", "TradeDecision",
    "TradeHistory", "SystemSettings", "NewsSource", "MarketSentiment", 
    "SystemHealth", "OrderSide", "OrderType", "OrderStatus", 
    "TradingPairStatus", "AIDecision", "ExchangeStatus", "create_all_tables"
]
