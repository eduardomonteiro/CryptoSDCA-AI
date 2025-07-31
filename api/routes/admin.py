"""
api/routes/admin.py - Admin API endpoints
Handles exchange management, AI agents, and system settings
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from src.database import get_db_session
from src.models.models import (
    User, Exchange, AIAgent, SystemSettings, TradingPair
)
from src.exceptions import CryptoBotException

router = APIRouter()

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

# Exchange Management
@router.get("/exchanges", response_class=HTMLResponse)
async def exchanges_page(request: Request, user: User = Depends(get_current_user)):
    """Exchange management page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Exchange Management - CryptoSDCA-AI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h1><i class="fas fa-exchange-alt"></i> Exchange Management</h1>
                    
                    <!-- Add Exchange Form -->
                    <div class="card mb-4">
                        <div class="card-header">
                            <h5><i class="fas fa-plus"></i> Add New Exchange</h5>
                        </div>
                        <div class="card-body">
                            <form id="addExchangeForm">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">Exchange</label>
                                            <select class="form-select" name="name" required>
                                                <option value="">Select Exchange</option>
                                                <option value="binance">Binance</option>
                                                <option value="kucoin">KuCoin</option>
                                                <option value="bingx">BingX</option>
                                                <option value="kraken">Kraken</option>
                                            </select>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Display Name</label>
                                            <input type="text" class="form-control" name="display_name" required>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">API Key</label>
                                            <input type="text" class="form-control" name="api_key" required>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">API Secret</label>
                                            <input type="password" class="form-control" name="api_secret" required>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">API Passphrase (KuCoin only)</label>
                                            <input type="password" class="form-control" name="api_passphrase">
                                        </div>
                                        <div class="mb-3">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="is_testnet" id="isTestnet">
                                                <label class="form-check-label" for="isTestnet">
                                                    Use Testnet/Sandbox
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save"></i> Add Exchange
                                </button>
                            </form>
                        </div>
                    </div>
                    
                    <!-- Exchanges List -->
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-list"></i> Configured Exchanges</h5>
                        </div>
                        <div class="card-body">
                            <div id="exchangesList">
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
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Load exchanges on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadExchanges();
            });
            
            // Add exchange form submission
            document.getElementById('addExchangeForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = {
                    name: formData.get('name'),
                    display_name: formData.get('display_name'),
                    api_key: formData.get('api_key'),
                    api_secret: formData.get('api_secret'),
                    api_passphrase: formData.get('api_passphrase'),
                    is_testnet: formData.get('is_testnet') === 'on'
                };
                
                try {
                    const response = await fetch('/api/admin/exchanges', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });
                    
                    if (response.ok) {
                        alert('Exchange added successfully!');
                        e.target.reset();
                        loadExchanges();
                    } else {
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            });
            
            async function loadExchanges() {
                try {
                    const response = await fetch('/api/admin/exchanges');
                    const exchanges = await response.json();
                    displayExchanges(exchanges);
                } catch (error) {
                    console.error('Error loading exchanges:', error);
                }
            }
            
            function displayExchanges(exchanges) {
                const container = document.getElementById('exchangesList');
                
                if (exchanges.length === 0) {
                    container.innerHTML = '<p class="text-muted">No exchanges configured</p>';
                    return;
                }
                
                const html = exchanges.map(exchange => `
                    <div class="card mb-3">
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-8">
                                    <h6>${exchange.display_name}</h6>
                                    <p class="text-muted mb-1">${exchange.name.toUpperCase()}</p>
                                    <span class="badge bg-${exchange.is_active ? 'success' : 'secondary'}">
                                        ${exchange.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                    ${exchange.is_testnet ? '<span class="badge bg-warning ms-1">Testnet</span>' : ''}
                                </div>
                                <div class="col-md-4 text-end">
                                    <button class="btn btn-sm btn-outline-primary" onclick="editExchange(${exchange.id})">
                                        <i class="fas fa-edit"></i> Edit
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteExchange(${exchange.id})">
                                        <i class="fas fa-trash"></i> Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
                
                container.innerHTML = html;
            }
            
            async function deleteExchange(id) {
                if (!confirm('Are you sure you want to delete this exchange?')) {
                    return;
                }
                
                try {
                    const response = await fetch(`/api/admin/exchanges/${id}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        alert('Exchange deleted successfully!');
                        loadExchanges();
                    } else {
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
        </script>
    </body>
    </html>
    """

@router.get("/api/admin/exchanges")
async def get_exchanges(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get all exchanges"""
    exchanges = db.query(Exchange).filter_by(user_id=user.id).order_by(Exchange.name).all()
    return exchanges

@router.post("/api/admin/exchanges")
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
        
        return exchange
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create exchange: {str(e)}")

@router.put("/api/admin/exchanges/{exchange_id}")
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
        return exchange
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update exchange: {str(e)}")

@router.delete("/api/admin/exchanges/{exchange_id}")
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

# AI Agents Management
@router.get("/ai-agents", response_class=HTMLResponse)
async def ai_agents_page(request: Request, user: User = Depends(get_current_user)):
    """AI agents management page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Agents Management - CryptoSDCA-AI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h1><i class="fas fa-brain"></i> AI Agents Management</h1>
                    
                    <!-- Add AI Agent Form -->
                    <div class="card mb-4">
                        <div class="card-header">
                            <h5><i class="fas fa-plus"></i> Add New AI Agent</h5>
                        </div>
                        <div class="card-body">
                            <form id="addAIAgentForm">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">Agent Name</label>
                                            <input type="text" class="form-control" name="name" required>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Agent Type</label>
                                            <select class="form-select" name="agent_type" required>
                                                <option value="">Select Type</option>
                                                <option value="copilot">Microsoft 365 Copilot</option>
                                                <option value="perplexity">Perplexity AI</option>
                                            </select>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">API Key</label>
                                            <input type="password" class="form-control" name="api_key">
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">API Secret</label>
                                            <input type="password" class="form-control" name="api_secret">
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Endpoint URL</label>
                                            <input type="url" class="form-control" name="endpoint_url">
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Model Name</label>
                                            <input type="text" class="form-control" name="model_name">
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Role Description</label>
                                    <textarea class="form-control" name="role_description" rows="3"></textarea>
                                </div>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save"></i> Add AI Agent
                                </button>
                            </form>
                        </div>
                    </div>
                    
                    <!-- AI Agents List -->
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-list"></i> Configured AI Agents</h5>
                        </div>
                        <div class="card-body">
                            <div id="aiAgentsList">
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
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Load AI agents on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadAIAgents();
            });
            
            // Add AI agent form submission
            document.getElementById('addAIAgentForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = {
                    name: formData.get('name'),
                    agent_type: formData.get('agent_type'),
                    api_key: formData.get('api_key'),
                    api_secret: formData.get('api_secret'),
                    endpoint_url: formData.get('endpoint_url'),
                    model_name: formData.get('model_name'),
                    role_description: formData.get('role_description')
                };
                
                try {
                    const response = await fetch('/api/admin/ai-agents', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });
                    
                    if (response.ok) {
                        alert('AI Agent added successfully!');
                        e.target.reset();
                        loadAIAgents();
                    } else {
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            });
            
            async function loadAIAgents() {
                try {
                    const response = await fetch('/api/admin/ai-agents');
                    const agents = await response.json();
                    displayAIAgents(agents);
                } catch (error) {
                    console.error('Error loading AI agents:', error);
                }
            }
            
            function displayAIAgents(agents) {
                const container = document.getElementById('aiAgentsList');
                
                if (agents.length === 0) {
                    container.innerHTML = '<p class="text-muted">No AI agents configured</p>';
                    return;
                }
                
                const html = agents.map(agent => `
                    <div class="card mb-3">
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-8">
                                    <h6>${agent.name}</h6>
                                    <p class="text-muted mb-1">${agent.agent_type.toUpperCase()}</p>
                                    <span class="badge bg-${agent.is_active ? 'success' : 'secondary'}">
                                        ${agent.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                    ${agent.model_name ? `<span class="badge bg-info ms-1">${agent.model_name}</span>` : ''}
                                </div>
                                <div class="col-md-4 text-end">
                                    <button class="btn btn-sm btn-outline-primary" onclick="editAIAgent(${agent.id})">
                                        <i class="fas fa-edit"></i> Edit
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteAIAgent(${agent.id})">
                                        <i class="fas fa-trash"></i> Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
                
                container.innerHTML = html;
            }
            
            async function deleteAIAgent(id) {
                if (!confirm('Are you sure you want to delete this AI agent?')) {
                    return;
                }
                
                try {
                    const response = await fetch(`/api/admin/ai-agents/${id}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        alert('AI Agent deleted successfully!');
                        loadAIAgents();
                    } else {
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
        </script>
    </body>
    </html>
    """

@router.get("/api/admin/ai-agents")
async def get_ai_agents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get all AI agents"""
    agents = db.query(AIAgent).filter_by(user_id=user.id).order_by(AIAgent.name).all()
    return agents

@router.post("/api/admin/ai-agents")
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
        
        return agent
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create AI agent: {str(e)}")

@router.put("/api/admin/ai-agents/{agent_id}")
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
        return agent
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update AI agent: {str(e)}")

@router.delete("/api/admin/ai-agents/{agent_id}")
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

# System Settings
@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: User = Depends(get_current_user)):
    """System settings page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>System Settings - CryptoSDCA-AI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h1><i class="fas fa-cog"></i> System Settings</h1>
                    
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-sliders-h"></i> Trading Configuration</h5>
                        </div>
                        <div class="card-body">
                            <form id="settingsForm">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">Default Profit Target (%)</label>
                                            <input type="number" class="form-control" name="default_profit_target" step="0.1" value="1.0">
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Default Stop Loss (%)</label>
                                            <input type="number" class="form-control" name="default_stop_loss" step="0.1" value="-3.0">
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Max Daily Loss (USD)</label>
                                            <input type="number" class="form-control" name="max_daily_loss_usd" step="1" value="100">
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">Min Pairs Count</label>
                                            <input type="number" class="form-control" name="min_pairs_count" step="1" value="3">
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Max Operation Duration (hours)</label>
                                            <input type="number" class="form-control" name="max_operation_duration_hours" step="1" value="72">
                                        </div>
                                        <div class="mb-3">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="paper_trading" id="paperTrading" checked>
                                                <label class="form-check-label" for="paperTrading">
                                                    Paper Trading Mode
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save"></i> Save Settings
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Load settings on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadSettings();
            });
            
            // Settings form submission
            document.getElementById('settingsForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = {};
                
                for (let [key, value] of formData.entries()) {
                    if (key === 'paper_trading') {
                        data[key] = value === 'on';
                    } else {
                        data[key] = value;
                    }
                }
                
                try {
                    const response = await fetch('/api/admin/settings', {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });
                    
                    if (response.ok) {
                        alert('Settings saved successfully!');
                    } else {
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            });
            
            async function loadSettings() {
                try {
                    const response = await fetch('/api/admin/settings');
                    const settings = await response.json();
                    
                    // Populate form fields
                    for (let [key, value] of Object.entries(settings)) {
                        const field = document.querySelector(`[name="${key}"]`);
                        if (field) {
                            if (field.type === 'checkbox') {
                                field.checked = value === 'true' || value === true;
                            } else {
                                field.value = value;
                            }
                        }
                    }
                } catch (error) {
                    console.error('Error loading settings:', error);
                }
            }
        </script>
    </body>
    </html>
    """

@router.get("/api/admin/settings")
async def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get system settings"""
    settings = db.query(SystemSettings).all()
    return {setting.key: setting.value for setting in settings}

@router.put("/api/admin/settings")
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