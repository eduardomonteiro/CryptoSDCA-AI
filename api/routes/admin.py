"""
api/routes/admin.py - Admin routes for CryptoSDCA-AI
Handles administrative functions like user management and system configuration
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db_session
from src.models.models import User, Exchange, AIAgent, TradingPair, SystemSettings

from src.utils import verify_password, hash_password, generate_secure_password
from src.exceptions import AuthenticationError, ValidationError

# Initialize router
router = APIRouter(prefix="/admin", tags=["admin"])

# Templates
templates = Jinja2Templates(directory="templates")

# Settings
settings = get_settings()


def get_current_admin_user(request: Request, db: Session = Depends(get_db_session)) -> User:
    """Get current admin user from session"""
    try:
        # Check if user is logged in
        user_id = request.session.get("user_id")
        if not user_id:
            raise AuthenticationError("Not authenticated")
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        # Check if user is admin
        if not user.is_admin:
            raise AuthenticationError("Admin access required")
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Admin dashboard page"""
    try:
        # Get system statistics
        stats = await get_system_statistics(db)
        
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "user": current_user,
                "stats": stats
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load admin dashboard: {str(e)}"
        )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """User management page"""
    try:
        # Get all users
        users = db.query(User).all()
        
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "user": current_user,
                "users": users
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load users: {str(e)}"
        )


@router.post("/users/create")
async def create_user(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Create a new user"""
    try:
        form = await request.form()
        
        username = form.get("username")
        email = form.get("email")
        password = form.get("password")
        is_admin = form.get("is_admin") == "on"
        
        # Validate input
        if not username or not email or not password:
            raise ValidationError("All fields are required")
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            raise ValidationError("Username or email already exists")
        
        # Create new user
        hashed_password = hash_password(password)
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=is_admin,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {"success": True, "message": "User created successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Update user information"""
    try:
        # Get user to update
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get form data
        form = await request.form()
        
        # Update fields
        if "username" in form:
            user.username = form["username"]
        
        if "email" in form:
            user.email = form["email"]
        
        if "is_admin" in form:
            user.is_admin = form["is_admin"] == "on"
        
        if "is_active" in form:
            user.is_active = form["is_active"] == "on"
        
        if "password" in form and form["password"]:
            user.hashed_password = hash_password(form["password"])
        
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "User updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Delete a user"""
    try:
        # Prevent self-deletion
        if user_id == current_user.id:
            raise ValidationError("Cannot delete your own account")
        
        # Get user to delete
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete user
        db.delete(user)
        db.commit()
        
        return {"success": True, "message": "User deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/exchanges", response_class=HTMLResponse)
async def admin_exchanges(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Exchange management page"""
    try:
        # Get all exchanges
        exchanges = db.query(Exchange).all()
        
        return templates.TemplateResponse(
            "admin_exchanges.html",
            {
                "request": request,
                "user": current_user,
                "exchanges": exchanges
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load exchanges: {str(e)}"
        )


@router.post("/exchanges/create")
async def create_exchange(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Create a new exchange"""
    try:
        form = await request.form()
        
        name = form.get("name")
        exchange_type = form.get("exchange_type")
        api_key = form.get("api_key")
        api_secret = form.get("api_secret")
        passphrase = form.get("passphrase", "")
        is_active = form.get("is_active") == "on"
        
        # Validate input
        if not name or not exchange_type or not api_key or not api_secret:
            raise ValidationError("Name, type, API key, and secret are required")
        
        # Check if exchange already exists
        existing_exchange = db.query(Exchange).filter(Exchange.name == name).first()
        if existing_exchange:
            raise ValidationError("Exchange with this name already exists")
        
        # Create new exchange
        new_exchange = Exchange(
            name=name,
            exchange_type=exchange_type,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            is_active=is_active,
            created_at=datetime.utcnow()
        )
        
        db.add(new_exchange)
        db.commit()
        db.refresh(new_exchange)
        
        return {"success": True, "message": "Exchange created successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/exchanges/{exchange_id}")
async def update_exchange(
    exchange_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Update exchange information"""
    try:
        # Get exchange to update
        exchange = db.query(Exchange).filter(Exchange.id == exchange_id).first()
        if not exchange:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange not found"
            )
        
        # Get form data
        form = await request.form()
        
        # Update fields
        if "name" in form:
            exchange.name = form["name"]
        
        if "exchange_type" in form:
            exchange.exchange_type = form["exchange_type"]
        
        if "api_key" in form:
            exchange.api_key = form["api_key"]
        
        if "api_secret" in form:
            exchange.api_secret = form["api_secret"]
        
        if "passphrase" in form:
            exchange.passphrase = form["passphrase"]
        
        if "is_active" in form:
            exchange.is_active = form["is_active"] == "on"
        
        exchange.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "Exchange updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/exchanges/{exchange_id}")
async def delete_exchange(
    exchange_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Delete an exchange"""
    try:
        # Get exchange to delete
        exchange = db.query(Exchange).filter(Exchange.id == exchange_id).first()
        if not exchange:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange not found"
            )
        
        # Delete exchange
        db.delete(exchange)
        db.commit()
        
        return {"success": True, "message": "Exchange deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/ai-agents", response_class=HTMLResponse)
async def admin_ai_agents(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """AI agents management page"""
    try:
        # Get all AI agents
        ai_agents = db.query(AIAgent).all()
        
        return templates.TemplateResponse(
            "admin_ai_agents.html",
            {
                "request": request,
                "user": current_user,
                "ai_agents": ai_agents
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load AI agents: {str(e)}"
        )


@router.post("/ai-agents/create")
async def create_ai_agent(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Create a new AI agent"""
    try:
        form = await request.form()
        
        name = form.get("name")
        platform = form.get("platform")
        api_url = form.get("api_url")
        api_key = form.get("api_key")
        role = form.get("role", "")
        is_active = form.get("is_active") == "on"
        
        # Validate input
        if not name or not platform or not api_url or not api_key:
            raise ValidationError("Name, platform, API URL, and key are required")
        
        # Check if AI agent already exists
        existing_agent = db.query(AIAgent).filter(AIAgent.name == name).first()
        if existing_agent:
            raise ValidationError("AI agent with this name already exists")
        
        # Create new AI agent
        new_agent = AIAgent(
            name=name,
            platform=platform,
            api_url=api_url,
            api_key=api_key,
            role=role,
            is_active=is_active,
            created_at=datetime.utcnow()
        )
        
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        return {"success": True, "message": "AI agent created successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/ai-agents/{agent_id}")
async def update_ai_agent(
    agent_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Update AI agent information"""
    try:
        # Get AI agent to update
        agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI agent not found"
            )
        
        # Get form data
        form = await request.form()
        
        # Update fields
        if "name" in form:
            agent.name = form["name"]
        
        if "platform" in form:
            agent.platform = form["platform"]
        
        if "api_url" in form:
            agent.api_url = form["api_url"]
        
        if "api_key" in form:
            agent.api_key = form["api_key"]
        
        if "role" in form:
            agent.role = form["role"]
        
        if "is_active" in form:
            agent.is_active = form["is_active"] == "on"
        
        agent.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "AI agent updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/ai-agents/{agent_id}")
async def delete_ai_agent(
    agent_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Delete an AI agent"""
    try:
        # Get AI agent to delete
        agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI agent not found"
            )
        
        # Delete AI agent
        db.delete(agent)
        db.commit()
        
        return {"success": True, "message": "AI agent deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/system-config", response_class=HTMLResponse)
async def admin_system_config(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """System configuration page"""
    try:
        # Get system configuration
        config = db.query(SystemSettings).first()
        if not config:
            # Create default config
            config = SystemSettings(
                default_profit_target=5.0,
                default_stop_loss=-3.0,
                max_portfolio_exposure=50.0,
                max_daily_drawdown=10.0,
                max_position_size=10.0,
                min_pairs_count=3,
                max_pairs_count=10,
                max_operation_duration_hours=24,
                min_notional=10.0,
                max_correlation=0.7,
                var_limit=5.0,
                volatility_limit=0.5,
                created_at=datetime.utcnow()
            )
            db.add(config)
            db.commit()
        
        return templates.TemplateResponse(
            "admin_system_config.html",
            {
                "request": request,
                "user": current_user,
                "config": config
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load system config: {str(e)}"
        )


@router.post("/system-config/update")
async def update_system_config(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Update system configuration"""
    try:
        form = await request.form()
        
        # Get current config
        config = db.query(SystemSettings).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System configuration not found"
            )
        
        # Update configuration values
        if "default_profit_target" in form:
            config.default_profit_target = float(form["default_profit_target"])
        
        if "default_stop_loss" in form:
            config.default_stop_loss = float(form["default_stop_loss"])
        
        if "max_portfolio_exposure" in form:
            config.max_portfolio_exposure = float(form["max_portfolio_exposure"])
        
        if "max_daily_drawdown" in form:
            config.max_daily_drawdown = float(form["max_daily_drawdown"])
        
        if "max_position_size" in form:
            config.max_position_size = float(form["max_position_size"])
        
        if "min_pairs_count" in form:
            config.min_pairs_count = int(form["min_pairs_count"])
        
        if "max_pairs_count" in form:
            config.max_pairs_count = int(form["max_pairs_count"])
        
        if "max_operation_duration_hours" in form:
            config.max_operation_duration_hours = int(form["max_operation_duration_hours"])
        
        if "min_notional" in form:
            config.min_notional = float(form["min_notional"])
        
        if "max_correlation" in form:
            config.max_correlation = float(form["max_correlation"])
        
        if "var_limit" in form:
            config.var_limit = float(form["var_limit"])
        
        if "volatility_limit" in form:
            config.volatility_limit = float(form["volatility_limit"])
        
        config.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "System configuration updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


async def get_system_statistics(db: Session) -> Dict[str, Any]:
    """Get system statistics for admin dashboard"""
    try:
        # Count users
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        admin_users = db.query(User).filter(User.is_admin == True).count()
        
        # Count exchanges
        total_exchanges = db.query(Exchange).count()
        active_exchanges = db.query(Exchange).filter(Exchange.is_active == True).count()
        
        # Count AI agents
        total_ai_agents = db.query(AIAgent).count()
        active_ai_agents = db.query(AIAgent).filter(AIAgent.is_active == True).count()
        
        # Count trading pairs
        total_pairs = db.query(TradingPair).count()
        active_pairs = db.query(TradingPair).filter(TradingPair.is_active == True).count()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "admins": admin_users
            },
            "exchanges": {
                "total": total_exchanges,
                "active": active_exchanges
            },
            "ai_agents": {
                "total": total_ai_agents,
                "active": active_ai_agents
            },
            "trading_pairs": {
                "total": total_pairs,
                "active": active_pairs
            }
        }
        
    except Exception as e:
        logger.error(f"❌ System statistics error: {e}")
        return {
            "users": {"total": 0, "active": 0, "admins": 0},
            "exchanges": {"total": 0, "active": 0},
            "ai_agents": {"total": 0, "active": 0},
            "trading_pairs": {"total": 0, "active": 0}
        }