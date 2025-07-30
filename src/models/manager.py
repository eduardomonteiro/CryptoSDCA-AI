"""
src/models/manager.py
Defines database tables exclusively for the Manager area, including API keys,
AI agents, wallets, bot settings, and indicator presets.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base

# Import the global Base declared once in your project
from src.models.base import Base

class ExchangeKey(Base):
    __tablename__ = "exchange_keys"
    __table_args__ = (
        UniqueConstraint("name", "exchange"),
        {"extend_existing": True},
    )

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(50), nullable=False, index=True)
    exchange: str = Column(String(20), nullable=False)  # e.g. 'binance'
    api_key: str = Column(Text, nullable=False)
    secret_key: str = Column(Text, nullable=False)
    passphrase: Optional[str] = Column(String(100))
    sandbox: bool = Column(Boolean, default=False)
    active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<ExchangeKey {self.exchange}:{self.name} active={self.active}>"


class AIAgent(Base):
    __tablename__ = "ai_agents"
    __table_args__ = (
        UniqueConstraint("name", "platform"),
        {"extend_existing": True},
    )

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(50), nullable=False)
    platform: str = Column(String(20), nullable=False)  # 'copilot', 'perplexity'
    api_key: str = Column(Text, nullable=False)
    api_url: str = Column(Text, nullable=False)
    active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AIAgent {self.platform}:{self.name} active={self.active}>"


class FundingWallet(Base):
    __tablename__ = "funding_wallets"
    __table_args__ = {"extend_existing": True}

    id: int = Column(Integer, primary_key=True, index=True)
    label: str = Column(String(50), nullable=False)
    chain: str = Column(String(20), nullable=False)  # e.g., 'ETH', 'TRON'
    address: str = Column(String(120), nullable=False, unique=True)
    active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FundingWallet {self.chain}:{self.label} active={self.active}>"


class BotSetting(Base):
    __tablename__ = "bot_settings"
    __table_args__ = {"extend_existing": True}

    id: int = Column(Integer, primary_key=True, default=1)
    daily_profit_target: float = Column(Float, default=1.0)  # percent
    global_stop_loss: float = Column(Float, default=-3.0)    # percent
    min_notional: float = Column(Float, default=15.0)        # minimum dollar order size
    max_hours: int = Column(Integer, default=72)              # Max running hours of strategy
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<BotSetting target={self.daily_profit_target}% "
            f"sl={self.global_stop_loss}% min_notional=${self.min_notional} max_hours={self.max_hours}>"
        )


class IndicatorPreset(Base):
    __tablename__ = "indicator_presets"
    __table_args__ = {"extend_existing": True}

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(50), unique=True, nullable=False)
    json_blob: str = Column(Text, nullable=False)  # JSON serialized indicator parameters
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<IndicatorPreset {self.name}>"
