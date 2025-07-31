"""
api/routes/admin.py - Admin API endpoints and frontend pages
Handles exchange management, AI agents, and system settings
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json
from pathlib import Path

from src.database import get_db_session
from src.models.models import (
    User, Exchange, AIAgent, SystemSettings, TradingPair
)
from src.exceptions import CryptoBotException

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="templates")

# Pydantic models
from pydantic import BaseModel, Field
from typing import Optional as Opt

class ExchangeCreate(BaseModel):
    name: str = Field(..., description="Exchange name (binance, kucoin, etc.)")
    display_name: str = Field(..., description="Display name")
    api_key: str = Field(..., description="API key")
    api_secret: str = Field(..., description="API secret")
    api_passphrase: Opt[str] = Field(None, description="API passphrase (for KuCoin)")
    is_testnet: bool = Field(False, description="Use testnet/sandbox")

class ExchangeUpdate(BaseModel):
    display_name: Opt[str] = None
    api_key: Opt[str] = None
    api_secret: Opt[str] = None
    api_passphrase: Opt[str] = None
    is_testnet: Opt[bool] = None
    is_active: Opt[bool] = None

class AIAgentCreate(BaseModel):
    name: str = Field(..., description="Agent name")
    agent_type: str = Field(..., description="copilot or perplexity")
    api_key: Opt[str] = Field(None, description="API key")
    api_secret: Opt[str] = Field(None, description="API secret")
    endpoint_url: Opt[str] = Field(None, description="Endpoint URL")
    model_name: Opt[str] = Field(None, description="Model name")
    role_description: Opt[str] = Field(None, description="Role description")

class AIAgentUpdate(BaseModel):
    name: Opt[str] = None
    api_key: Opt[str] = None
    api_secret: Opt[str] = None
    endpoint_url: Opt[str] = None
    model_name: Opt[str] = None
    role_description: Opt[str] = None
    is_active: Opt[bool] = None

class SystemSettingUpdate(BaseModel):
    value: str = Field(..., description="Setting value")
    description: Opt[str] = None

# Helper function for authentication
def get_current_user(request: Request, db: Session = Depends(get_db_session)) -> User:
    """Get current user from session"""
    user = db.query(User).first()
    if not user:
        user = User(
            username="admin",
            email="admin@cryptosdca.ai",
            is_admin=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# ============================================================================
# FRONTEND PAGES (HTML Responses)
# ============================================================================

@router.get("/exchanges", response_class=HTMLResponse)
async def exchanges_page(request: Request, user: User = Depends(get_current_user)):
    """Exchange management page"""
    return templates.TemplateResponse("admin_exchanges.html", {"request": request, "user": user})

@router.get("/ai-agents", response_class=HTMLResponse)
async def ai_agents_page(request: Request, user: User = Depends(get_current_user)):
    """AI agents management page"""
    return templates.TemplateResponse("admin_ai_agents.html", {"request": request, "user": user})

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: User = Depends(get_current_user)):
    """System settings page"""
    return templates.TemplateResponse("admin_system_config.html", {"request": request, "user": user})

@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, user: User = Depends(get_current_user)):
    """Trading history page"""
    return templates.TemplateResponse("history.html", {"request": request, "user": user})

@router.get("/manager", response_class=HTMLResponse)
async def manager_page(request: Request, user: User = Depends(get_current_user)):
    """Manager dashboard page"""
    return templates.TemplateResponse("manager.html", {"request": request, "user": user})

# ============================================================================
# API ENDPOINTS (JSON Responses)
# ============================================================================

# Exchange Management API
@router.get("/api/exchanges")
async def get_exchanges(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get all exchanges"""
    exchanges = db.query(Exchange).filter_by(user_id=user.id).order_by(Exchange.name).all()
    return exchanges

@router.post("/api/exchanges")
async def create_exchange(
    exchange_data: ExchangeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new exchange"""
    try:
        # Check if exchange already exists
        existing = db.query(Exchange).filter_by(
            user_id=user.id, 
            name=exchange_data.name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Exchange already exists")
        
        exchange = Exchange(
            user_id=user.id,
            name=exchange_data.name,
            display_name=exchange_data.display_name,
            api_key=exchange_data.api_key,
            api_secret=exchange_data.api_secret,
            api_passphrase=exchange_data.api_passphrase,
            is_testnet=exchange_data.is_testnet,
            is_active=True,
            status="disconnected"
        )
        
        db.add(exchange)
        db.commit()
        db.refresh(exchange)
        
        return {"success": True, "message": "Exchange created successfully", "exchange": exchange}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create exchange: {str(e)}")

@router.put("/api/exchanges/{exchange_id}")
async def update_exchange(
    exchange_id: int,
    exchange_data: ExchangeUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update an exchange"""
    try:
        exchange = db.query(Exchange).filter_by(id=exchange_id, user_id=user.id).first()
        if not exchange:
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        # Update fields
        for field, value in exchange_data.dict(exclude_unset=True).items():
            setattr(exchange, field, value)
        
        db.commit()
        db.refresh(exchange)
        return {"success": True, "message": "Exchange updated successfully", "exchange": exchange}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update exchange: {str(e)}")

@router.delete("/api/exchanges/{exchange_id}")
async def delete_exchange(
    exchange_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete an exchange"""
    try:
        exchange = db.query(Exchange).filter_by(id=exchange_id, user_id=user.id).first()
        if not exchange:
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        db.delete(exchange)
        db.commit()
        
        return {"success": True, "message": "Exchange deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete exchange: {str(e)}")

# AI Agents Management API
@router.get("/api/ai-agents")
async def get_ai_agents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get all AI agents"""
    agents = db.query(AIAgent).filter_by(user_id=user.id).order_by(AIAgent.name).all()
    return agents

@router.post("/api/ai-agents")
async def create_ai_agent(
    agent_data: AIAgentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new AI agent"""
    try:
        # Check if agent already exists
        existing = db.query(AIAgent).filter_by(
            user_id=user.id, 
            name=agent_data.name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="AI Agent already exists")
        
        agent = AIAgent(
            user_id=user.id,
            name=agent_data.name,
            agent_type=agent_data.agent_type,
            api_key=agent_data.api_key,
            api_secret=agent_data.api_secret,
            endpoint_url=agent_data.endpoint_url,
            model_name=agent_data.model_name,
            role_description=agent_data.role_description,
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        return {"success": True, "message": "AI Agent created successfully", "agent": agent}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create AI agent: {str(e)}")

@router.put("/api/ai-agents/{agent_id}")
async def update_ai_agent(
    agent_id: int,
    agent_data: AIAgentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update an AI agent"""
    try:
        agent = db.query(AIAgent).filter_by(id=agent_id, user_id=user.id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="AI Agent not found")
        
        # Update fields
        for field, value in agent_data.dict(exclude_unset=True).items():
            setattr(agent, field, value)
        
        db.commit()
        db.refresh(agent)
        return {"success": True, "message": "AI Agent updated successfully", "agent": agent}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update AI agent: {str(e)}")

@router.delete("/api/ai-agents/{agent_id}")
async def delete_ai_agent(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete an AI agent"""
    try:
        agent = db.query(AIAgent).filter_by(id=agent_id, user_id=user.id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="AI Agent not found")
        
        db.delete(agent)
        db.commit()
        
        return {"success": True, "message": "AI Agent deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete AI agent: {str(e)}")

# System Settings API
@router.get("/api/settings")
async def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get system settings"""
    settings = db.query(SystemSettings).all()
    return {setting.key: setting.value for setting in settings}

@router.put("/api/settings")
async def update_settings(
    settings_data: Dict[str, Any],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update system settings"""
    try:
        for key, value in settings_data.items():
            setting = db.query(SystemSettings).filter_by(key=key).first()
            if setting:
                setting.value = str(value)
                setting.updated_at = datetime.now()
            else:
                # Create new setting
                setting = SystemSettings(
                    key=key,
                    value=str(value),
                    value_type="string",
                    description=f"Setting for {key}",
                    category="system"
                )
                db.add(setting)
        
        db.commit()
        return {"success": True, "message": "Settings updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

# History API
@router.get("/api/history")
async def get_trading_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0
):
    """Get trading history"""
    from src.models.models import Trade
    
    trades = db.query(Trade).filter_by(user_id=user.id).order_by(
        desc(Trade.created_at)
    ).offset(offset).limit(limit).all()
    
    return trades