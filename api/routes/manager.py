"""
api/routes/manager.py
FastAPI router for Manager API: handles CRUD operations for Exchange Keys,
AI Agents, Funding Wallets, Bot Settings, and Indicator Presets.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from src.core.database import get_db
from src.models.manager import ExchangeKey, AIAgent, FundingWallet, BotSetting, IndicatorPreset

# Create the router instance
router = APIRouter()

# ------------------------
# Pydantic Schemas
# ------------------------

class ExchangeKeyIn(BaseModel):
    name: str
    exchange: str
    api_key: str
    secret_key: str
    passphrase: Optional[str] = None
    sandbox: bool = False
    active: bool = True

class ExchangeKeyOut(BaseModel):
    id: int
    name: str
    exchange: str
    sandbox: bool
    active: bool
    updated_at: datetime

    class Config:
        from_attributes = True

class AIAgentIn(BaseModel):
    name: str
    platform: str  # e.g. 'copilot', 'perplexity'
    api_key: str
    api_url: str
    active: bool = True

class AIAgentOut(BaseModel):
    id: int
    name: str
    platform: str
    api_url: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class FundingWalletIn(BaseModel):
    label: str
    chain: str
    address: str
    active: bool = True

class FundingWalletOut(BaseModel):
    id: int
    label: str
    chain: str
    address: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class BotSettingIn(BaseModel):
    daily_profit_target: float
    global_stop_loss: float
    min_notional: float
    max_hours: int

class BotSettingOut(BaseModel):
    id: int
    daily_profit_target: float
    global_stop_loss: float
    min_notional: float
    max_hours: int
    created_at: datetime

    class Config:
        from_attributes = True

class IndicatorPresetIn(BaseModel):
    name: str
    json_blob: str

class IndicatorPresetOut(BaseModel):
    id: int
    name: str
    json_blob: str
    created_at: datetime

    class Config:
        from_attributes = True

# ------------------------
# Exchange Keys CRUD
# ------------------------

@router.get("/keys", response_model=List[ExchangeKeyOut])
def list_keys(db: Session = Depends(get_db)):
    """List all exchange keys"""
    keys = db.query(ExchangeKey).all()
    return keys

@router.post("/keys", status_code=status.HTTP_201_CREATED)
def create_key(data: ExchangeKeyIn, db: Session = Depends(get_db)):
    """Create a new exchange key"""
    exists = db.query(ExchangeKey).filter_by(name=data.name, exchange=data.exchange).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "ExchangeKey with given name and exchange already exists")
    
    key = ExchangeKey(**data.dict())
    db.add(key)
    db.commit()
    db.refresh(key)
    return {"success": True, "id": key.id}

@router.put("/keys/{key_id}")
def update_key(key_id: int, data: ExchangeKeyIn, db: Session = Depends(get_db)):
    """Update an existing exchange key"""
    key = db.query(ExchangeKey).filter_by(id=key_id).first()
    if not key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Key not found")
    
    for field, value in data.dict().items():
        setattr(key, field, value)
    db.commit()
    return {"success": True}

@router.delete("/keys/{key_id}")
def delete_key(key_id: int, db: Session = Depends(get_db)):
    """Delete an exchange key"""
    key = db.query(ExchangeKey).filter_by(id=key_id).first()
    if not key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Key not found")
    
    db.delete(key)
    db.commit()
    return {"success": True}

# ------------------------
# AI Agents CRUD
# ------------------------

@router.get("/agents", response_model=List[AIAgentOut])
def list_agents(db: Session = Depends(get_db)):
    """List all AI agents"""
    agents = db.query(AIAgent).all()
    return agents

@router.post("/agents", status_code=status.HTTP_201_CREATED)
def create_agent(data: AIAgentIn, db: Session = Depends(get_db)):
    """Create a new AI agent"""
    exists = db.query(AIAgent).filter_by(name=data.name, platform=data.platform).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Agent with this name and platform already exists")
    
    agent = AIAgent(**data.dict())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {"success": True, "id": agent.id}

@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    """Delete an AI agent"""
    agent = db.query(AIAgent).filter_by(id=agent_id).first()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    
    db.delete(agent)
    db.commit()
    return {"success": True}

# ------------------------
# Funding Wallets CRUD
# ------------------------

@router.get("/wallets", response_model=List[FundingWalletOut])
def list_wallets(db: Session = Depends(get_db)):
    """List all funding wallets"""
    wallets = db.query(FundingWallet).all()
    return wallets

@router.post("/wallets", status_code=status.HTTP_201_CREATED)
def create_wallet(data: FundingWalletIn, db: Session = Depends(get_db)):
    """Create a new funding wallet"""
    exists = db.query(FundingWallet).filter_by(address=data.address).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Wallet address already exists")
    
    wallet = FundingWallet(**data.dict())
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return {"success": True, "id": wallet.id}

@router.delete("/wallets/{wallet_id}")
def delete_wallet(wallet_id: int, db: Session = Depends(get_db)):
    """Delete a funding wallet"""
    wallet = db.query(FundingWallet).filter_by(id=wallet_id).first()
    if not wallet:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Wallet not found")
    
    db.delete(wallet)
    db.commit()
    return {"success": True}

# ------------------------
# Bot Settings (singleton)
# ------------------------

@router.get("/settings", response_model=BotSettingOut)
def get_settings(db: Session = Depends(get_db)):
    """Get bot settings (creates default if not exists)"""
    settings = db.query(BotSetting).filter_by(id=1).first()
    if not settings:
        settings = BotSetting(
            daily_profit_target=1.0,
            global_stop_loss=-3.0,
            min_notional=15.0,
            max_hours=72,
            id=1
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/settings")
def update_settings(
    daily_profit_target: float = Form(...),
    global_stop_loss: float = Form(...),
    min_notional: float = Form(...),
    max_hours: int = Form(...),
    db: Session = Depends(get_db)
):
    """Update bot settings"""
    settings = db.query(BotSetting).filter_by(id=1).first()
    if not settings:
        settings = BotSetting(id=1)
        db.add(settings)
    
    settings.daily_profit_target = daily_profit_target
    settings.global_stop_loss = global_stop_loss
    settings.min_notional = min_notional
    settings.max_hours = max_hours
    
    db.commit()
    return {"success": True}

# ------------------------
# Indicator Presets CRUD
# ------------------------

@router.get("/presets", response_model=List[IndicatorPresetOut])
def list_presets(db: Session = Depends(get_db)):
    """List all indicator presets"""
    presets = db.query(IndicatorPreset).all()
    return presets

@router.post("/presets", status_code=status.HTTP_201_CREATED)
def create_preset(data: IndicatorPresetIn, db: Session = Depends(get_db)):
    """Create a new indicator preset"""
    exists = db.query(IndicatorPreset).filter_by(name=data.name).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Preset with this name already exists")
    
    preset = IndicatorPreset(**data.dict())
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return {"success": True, "id": preset.id}

@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: int, db: Session = Depends(get_db)):
    """Delete an indicator preset"""
    preset = db.query(IndicatorPreset).filter_by(id=preset_id).first()
    if not preset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Preset not found")
    
    db.delete(preset)
    db.commit()
    return {"success": True}

# ------------------------
# Health Check
# ------------------------

@router.get("/health")
def health_check():
    """Manager API health check"""
    return {
        "status": "healthy",
        "service": "manager-api",
        "timestamp": datetime.utcnow().isoformat()
    }

# ------------------------
# Info Endpoint
# ------------------------

@router.get("/info")
def get_info(db: Session = Depends(get_db)):
    """Get manager API information"""
    try:
        keys_count = db.query(ExchangeKey).count()
        agents_count = db.query(AIAgent).count()
        wallets_count = db.query(FundingWallet).count()
        presets_count = db.query(IndicatorPreset).count()
        
        return {
            "service": "CryptoSDCA-AI Manager API",
            "version": "1.0.0",
            "endpoints": {
                "exchange_keys": keys_count,
                "ai_agents": agents_count,
                "funding_wallets": wallets_count,
                "indicator_presets": presets_count
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "service": "CryptoSDCA-AI Manager API",
            "version": "1.0.0",
            "status": "database_error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
