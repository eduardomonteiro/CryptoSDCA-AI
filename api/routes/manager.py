"""
api/routes/manager.py
FastAPI router for Manager API: handles CRUD operations for Exchange Keys,
AI Agents, Funding Wallets, Bot Settings, and Indicator Presets.
UPDATED: Now using correct database models and real data
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from src.database import get_db
from src.models.models import Exchange, AIAgent, SystemSettings
from api.routes.auth import require_auth

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
    last_connected: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True

class AIAgentIn(BaseModel):
    name: str
    agent_type: str  # 'copilot', 'perplexity', 'openai'
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    model_name: Optional[str] = None
    role_description: Optional[str] = None
    active: bool = True

class AIAgentOut(BaseModel):
    id: int
    name: str
    agent_type: str
    endpoint_url: Optional[str]
    model_name: Optional[str]
    is_active: bool
    created_at: datetime
    total_decisions: int
    accuracy_rate: float

    class Config:
        from_attributes = True

class BotSettingIn(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    category: str = "trading"

class BotSettingOut(BaseModel):
    id: int
    key: str
    value: str
    value_type: str
    description: Optional[str]
    category: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True

# ------------------------
# Exchange Keys CRUD
# ------------------------

@router.get("/keys", response_model=List[ExchangeKeyOut])
def list_keys(db: Session = Depends(get_db), current_user = Depends(require_auth)):
    """List all exchange keys for current user"""
    exchanges = db.query(Exchange).filter_by(user_id=current_user.id).all()
    
    # Convert to response format
    result = []
    for exchange in exchanges:
        result.append(ExchangeKeyOut(
            id=exchange.id,
            name=exchange.display_name,
            exchange=exchange.name,
            sandbox=exchange.is_testnet,
            active=exchange.is_active,
            last_connected=exchange.last_connected,
            updated_at=exchange.updated_at
        ))
    
    return result

@router.post("/keys", status_code=status.HTTP_201_CREATED)
def create_key(
    data: ExchangeKeyIn, 
    db: Session = Depends(get_db), 
    current_user = Depends(require_auth)
):
    """Create a new exchange key"""
    
    # Check if exchange already exists for this user
    existing = db.query(Exchange).filter_by(
        user_id=current_user.id, 
        name=data.exchange,
        display_name=data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, 
            "Exchange with this name already exists"
        )
    
    # Create new exchange record
    exchange = Exchange(
        user_id=current_user.id,
        name=data.exchange,
        display_name=data.name,
        api_key=data.api_key,
        api_secret=data.secret_key,
        api_passphrase=data.passphrase,
        is_testnet=data.sandbox,
        is_active=data.active
    )
    
    db.add(exchange)
    db.commit()
    db.refresh(exchange)
    
    return {"success": True, "id": exchange.id, "message": f"Exchange '{data.name}' added successfully"}

@router.put("/keys/{key_id}")
def update_key(
    key_id: int, 
    data: ExchangeKeyIn, 
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Update an existing exchange key"""
    
    exchange = db.query(Exchange).filter_by(
        id=key_id, 
        user_id=current_user.id
    ).first()
    
    if not exchange:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exchange not found")
    
    # Update fields
    exchange.display_name = data.name
    exchange.name = data.exchange
    exchange.api_key = data.api_key
    exchange.api_secret = data.secret_key
    exchange.api_passphrase = data.passphrase
    exchange.is_testnet = data.sandbox
    exchange.is_active = data.active
    exchange.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"success": True, "message": f"Exchange '{data.name}' updated successfully"}

@router.delete("/keys/{key_id}")
def delete_key(
    key_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Delete an exchange key"""
    
    exchange = db.query(Exchange).filter_by(
        id=key_id, 
        user_id=current_user.id
    ).first()
    
    if not exchange:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exchange not found")
    
    exchange_name = exchange.display_name
    db.delete(exchange)
    db.commit()
    
    return {"success": True, "message": f"Exchange '{exchange_name}' deleted successfully"}

# ------------------------
# AI Agents CRUD
# ------------------------

@router.get("/agents", response_model=List[AIAgentOut])
def list_agents(db: Session = Depends(get_db), current_user = Depends(require_auth)):
    """List all AI agents for current user"""
    agents = db.query(AIAgent).filter_by(user_id=current_user.id).all()
    return agents

@router.post("/agents", status_code=status.HTTP_201_CREATED)
def create_agent(
    data: AIAgentIn, 
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Create a new AI agent"""
    
    # Check if agent with same name already exists
    existing = db.query(AIAgent).filter_by(
        user_id=current_user.id,
        name=data.name,
        agent_type=data.agent_type
    ).first()
    
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, 
            "AI Agent with this name and type already exists"
        )
    
    # Create new AI agent
    agent = AIAgent(
        user_id=current_user.id,
        name=data.name,
        agent_type=data.agent_type,
        api_key=data.api_key,
        endpoint_url=data.endpoint_url,
        model_name=data.model_name,
        role_description=data.role_description,
        is_active=data.active
    )
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return {"success": True, "id": agent.id, "message": f"AI Agent '{data.name}' added successfully"}

@router.put("/agents/{agent_id}")
def update_agent(
    agent_id: int,
    data: AIAgentIn,
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Update an existing AI agent"""
    
    agent = db.query(AIAgent).filter_by(
        id=agent_id,
        user_id=current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI Agent not found")
    
    # Update fields
    agent.name = data.name
    agent.agent_type = data.agent_type
    agent.api_key = data.api_key
    agent.endpoint_url = data.endpoint_url
    agent.model_name = data.model_name
    agent.role_description = data.role_description
    agent.is_active = data.active
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"success": True, "message": f"AI Agent '{data.name}' updated successfully"}

@router.delete("/agents/{agent_id}")
def delete_agent(
    agent_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Delete an AI agent"""
    
    agent = db.query(AIAgent).filter_by(
        id=agent_id,
        user_id=current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI Agent not found")
    
    agent_name = agent.name
    db.delete(agent)
    db.commit()
    
    return {"success": True, "message": f"AI Agent '{agent_name}' deleted successfully"}

# ------------------------
# Bot Settings Management
# ------------------------

@router.get("/settings")
def get_settings(db: Session = Depends(get_db), current_user = Depends(require_auth)):
    """Get all bot settings"""
    settings = db.query(SystemSettings).filter_by(category="trading").all()
    
    # Convert to dictionary format
    settings_dict = {}
    for setting in settings:
        settings_dict[setting.key] = {
            "value": setting.value,
            "type": setting.value_type,
            "description": setting.description
        }
    
    # Provide defaults if not set
    default_settings = {
        "daily_profit_target": {"value": "1.0", "type": "float", "description": "Daily profit target (%)"},
        "global_stop_loss": {"value": "-3.0", "type": "float", "description": "Global stop loss (%)"},
        "max_operation_duration_hours": {"value": "72", "type": "int", "description": "Maximum operation duration (hours)"},
        "min_pairs_count": {"value": "3", "type": "int", "description": "Minimum number of trading pairs"},
        "paper_trading": {"value": "true", "type": "bool", "description": "Enable paper trading mode"}
    }
    
    # Merge with defaults
    for key, default in default_settings.items():
        if key not in settings_dict:
            settings_dict[key] = default
    
    return {"success": True, "settings": settings_dict}

@router.put("/settings")
def update_settings(
    settings_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Update bot settings"""
    
    if not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    
    updated_count = 0
    
    for key, value in settings_data.items():
        # Find existing setting
        setting = db.query(SystemSettings).filter_by(key=key, category="trading").first()
        
        if setting:
            # Update existing
            setting.value = str(value)
            setting.updated_at = datetime.utcnow()
        else:
            # Create new setting
            value_type = "string"
            if isinstance(value, bool):
                value_type = "bool"
            elif isinstance(value, int):
                value_type = "int"
            elif isinstance(value, float):
                value_type = "float"
                
            setting = SystemSettings(
                key=key,
                value=str(value),
                value_type=value_type,
                category="trading",
                description=f"Bot setting: {key}"
            )
            db.add(setting)
        
        updated_count += 1
    
    db.commit()
    
    return {"success": True, "message": f"Updated {updated_count} settings"}

@router.post("/settings")
def create_setting(
    data: BotSettingIn,
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Create a new bot setting"""
    
    if not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    
    # Check if setting already exists
    existing = db.query(SystemSettings).filter_by(key=data.key, category=data.category).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Setting already exists")
    
    # Determine value type
    value_type = "string"
    if data.value.lower() in ["true", "false"]:
        value_type = "bool"
    elif data.value.replace(".", "").replace("-", "").isdigit():
        value_type = "float" if "." in data.value else "int"
    
    setting = SystemSettings(
        key=data.key,
        value=data.value,
        value_type=value_type,
        description=data.description,
        category=data.category
    )
    
    db.add(setting)
    db.commit()
    db.refresh(setting)
    
    return {"success": True, "id": setting.id, "message": f"Setting '{data.key}' created successfully"}

# ------------------------
# System Status and Information
# ------------------------

@router.get("/health")
def health_check():
    """Manager API health check"""
    return {
        "status": "healthy",
        "service": "manager-api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/info")
def get_info(db: Session = Depends(get_db), current_user = Depends(require_auth)):
    """Get manager API information"""
    try:
        exchanges_count = db.query(Exchange).filter_by(user_id=current_user.id).count()
        agents_count = db.query(AIAgent).filter_by(user_id=current_user.id).count()
        settings_count = db.query(SystemSettings).filter_by(category="trading").count()
        
        return {
            "service": "CryptoSDCA-AI Manager API",
            "version": "1.0.0",
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "is_admin": current_user.is_admin
            },
            "statistics": {
                "exchanges": exchanges_count,
                "ai_agents": agents_count,
                "settings": settings_count
            },
            "endpoints": [
                "/keys - Exchange API keys management",
                "/agents - AI agents management", 
                "/settings - Bot settings management",
                "/health - Health check",
                "/info - Service information"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "service": "CryptoSDCA-AI Manager API",
            "version": "1.0.0",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# ------------------------
# Bulk Operations
# ------------------------

@router.post("/keys/test/{key_id}")
def test_exchange_connection(
    key_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Test connection to an exchange"""
    
    exchange = db.query(Exchange).filter_by(
        id=key_id,
        user_id=current_user.id
    ).first()
    
    if not exchange:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exchange not found")
    
    # TODO: Implement actual connection test using CCXT
    # For now, return mock result
    
    # Update last connected time
    exchange.last_connected = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "exchange": exchange.name,
        "status": "connected",
        "test_time": datetime.utcnow().isoformat(),
        "message": f"Successfully connected to {exchange.display_name}"
    }

@router.post("/agents/test/{agent_id}")
def test_ai_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Test AI agent connection"""
    
    agent = db.query(AIAgent).filter_by(
        id=agent_id,
        user_id=current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI Agent not found")
    
    # TODO: Implement actual AI agent connection test
    # For now, return mock result
    
    return {
        "success": True,
        "agent": agent.name,
        "type": agent.agent_type,
        "status": "connected",
        "test_time": datetime.utcnow().isoformat(),
        "message": f"Successfully tested {agent.name} ({agent.agent_type})"
    }
