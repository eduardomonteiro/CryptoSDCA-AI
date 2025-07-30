"""
api/routes/settings.py - Settings routes for CryptoSDCA-AI
Handles system configuration and user preferences
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db_session
from src.models.models import User, SystemSettings, UserSettings, TradingPair

from src.utils import verify_password, hash_password
from src.exceptions import AuthenticationError, ValidationError

# Initialize router
router = APIRouter(prefix="/settings", tags=["settings"])

# Templates
templates = Jinja2Templates(directory="templates")

# Settings
settings = get_settings()


def get_current_user(request: Request, db: Session = Depends(get_db_session)) -> User:
    """Get current user from session"""
    try:
        # Check if user is logged in
        user_id = request.session.get("user_id")
        if not user_id:
            raise AuthenticationError("Not authenticated")
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/", response_class=HTMLResponse)
async def settings_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Settings dashboard page"""
    try:
        # Get system configuration
        system_config = db.query(SystemSettings).first()
        if not system_config:
            # Create default config
            system_config = SystemSettings(
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
            db.add(system_config)
            db.commit()
        
        # Get user settings
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
        if not user_settings:
            # Create default user settings
            user_settings = UserSettings(
                user_id=current_user.id,
                default_profit_target=5.0,
                default_stop_loss=-3.0,
                max_position_size=10.0,
                preferred_pairs=["BTC/USDT", "ETH/USDT", "BNB/USDT"],
                notification_email=True,
                notification_telegram=False,
                telegram_chat_id="",
                created_at=datetime.utcnow()
            )
            db.add(user_settings)
            db.commit()
        
        # Get available trading pairs
        trading_pairs = db.query(TradingPair).filter(TradingPair.is_active == True).all()
        
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "user": current_user,
                "system_config": system_config,
                "user_settings": user_settings,
                "trading_pairs": trading_pairs
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load settings: {str(e)}"
        )


@router.post("/user/update")
async def update_user_settings(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update user settings"""
    try:
        form = await request.form()
        
        # Get user settings
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
        if not user_settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )
        
        # Update settings
        if "default_profit_target" in form:
            user_settings.default_profit_target = float(form["default_profit_target"])
        
        if "default_stop_loss" in form:
            user_settings.default_stop_loss = float(form["default_stop_loss"])
        
        if "max_position_size" in form:
            user_settings.max_position_size = float(form["max_position_size"])
        
        if "preferred_pairs" in form:
            pairs = form.getlist("preferred_pairs")
            user_settings.preferred_pairs = pairs
        
        if "notification_email" in form:
            user_settings.notification_email = form["notification_email"] == "on"
        
        if "notification_telegram" in form:
            user_settings.notification_telegram = form["notification_telegram"] == "on"
        
        if "telegram_chat_id" in form:
            user_settings.telegram_chat_id = form["telegram_chat_id"]
        
        user_settings.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "User settings updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/system/update")
async def update_system_settings(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update system settings (admin only)"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        form = await request.form()
        
        # Get system configuration
        system_config = db.query(SystemSettings).first()
        if not system_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System configuration not found"
            )
        
        # Update configuration values
        if "default_profit_target" in form:
            system_config.default_profit_target = float(form["default_profit_target"])
        
        if "default_stop_loss" in form:
            system_config.default_stop_loss = float(form["default_stop_loss"])
        
        if "max_portfolio_exposure" in form:
            system_config.max_portfolio_exposure = float(form["max_portfolio_exposure"])
        
        if "max_daily_drawdown" in form:
            system_config.max_daily_drawdown = float(form["max_daily_drawdown"])
        
        if "max_position_size" in form:
            system_config.max_position_size = float(form["max_position_size"])
        
        if "min_pairs_count" in form:
            system_config.min_pairs_count = int(form["min_pairs_count"])
        
        if "max_pairs_count" in form:
            system_config.max_pairs_count = int(form["max_pairs_count"])
        
        if "max_operation_duration_hours" in form:
            system_config.max_operation_duration_hours = int(form["max_operation_duration_hours"])
        
        if "min_notional" in form:
            system_config.min_notional = float(form["min_notional"])
        
        if "max_correlation" in form:
            system_config.max_correlation = float(form["max_correlation"])
        
        if "var_limit" in form:
            system_config.var_limit = float(form["var_limit"])
        
        if "volatility_limit" in form:
            system_config.volatility_limit = float(form["volatility_limit"])
        
        system_config.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "System settings updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/trading-pairs", response_class=HTMLResponse)
async def trading_pairs_settings(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Trading pairs management page"""
    try:
        # Get all trading pairs
        trading_pairs = db.query(TradingPair).all()
        
        return templates.TemplateResponse(
            "trading_pairs_settings.html",
            {
                "request": request,
                "user": current_user,
                "trading_pairs": trading_pairs
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load trading pairs: {str(e)}"
        )


@router.post("/trading-pairs/create")
async def create_trading_pair(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new trading pair"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        form = await request.form()
        
        symbol = form.get("symbol")
        base_currency = form.get("base_currency")
        quote_currency = form.get("quote_currency")
        min_order_size = form.get("min_order_size")
        max_order_size = form.get("max_order_size")
        price_precision = form.get("price_precision")
        quantity_precision = form.get("quantity_precision")
        is_active = form.get("is_active") == "on"
        
        # Validate input
        if not symbol or not base_currency or not quote_currency:
            raise ValidationError("Symbol, base currency, and quote currency are required")
        
        # Check if trading pair already exists
        existing_pair = db.query(TradingPair).filter(TradingPair.symbol == symbol).first()
        if existing_pair:
            raise ValidationError("Trading pair with this symbol already exists")
        
        # Create new trading pair
        new_pair = TradingPair(
            symbol=symbol,
            base_currency=base_currency,
            quote_currency=quote_currency,
            min_order_size=float(min_order_size) if min_order_size else 0.0,
            max_order_size=float(max_order_size) if max_order_size else 0.0,
            price_precision=int(price_precision) if price_precision else 8,
            quantity_precision=int(quantity_precision) if quantity_precision else 8,
            is_active=is_active,
            created_at=datetime.utcnow()
        )
        
        db.add(new_pair)
        db.commit()
        db.refresh(new_pair)
        
        return {"success": True, "message": "Trading pair created successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/trading-pairs/{pair_id}")
async def update_trading_pair(
    pair_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update trading pair"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Get trading pair to update
        trading_pair = db.query(TradingPair).filter(TradingPair.id == pair_id).first()
        if not trading_pair:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trading pair not found"
            )
        
        # Get form data
        form = await request.form()
        
        # Update fields
        if "symbol" in form:
            trading_pair.symbol = form["symbol"]
        
        if "base_currency" in form:
            trading_pair.base_currency = form["base_currency"]
        
        if "quote_currency" in form:
            trading_pair.quote_currency = form["quote_currency"]
        
        if "min_order_size" in form:
            trading_pair.min_order_size = float(form["min_order_size"])
        
        if "max_order_size" in form:
            trading_pair.max_order_size = float(form["max_order_size"])
        
        if "price_precision" in form:
            trading_pair.price_precision = int(form["price_precision"])
        
        if "quantity_precision" in form:
            trading_pair.quantity_precision = int(form["quantity_precision"])
        
        if "is_active" in form:
            trading_pair.is_active = form["is_active"] == "on"
        
        trading_pair.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "Trading pair updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/trading-pairs/{pair_id}")
async def delete_trading_pair(
    pair_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete trading pair"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Get trading pair to delete
        trading_pair = db.query(TradingPair).filter(TradingPair.id == pair_id).first()
        if not trading_pair:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trading pair not found"
            )
        
        # Delete trading pair
        db.delete(trading_pair)
        db.commit()
        
        return {"success": True, "message": "Trading pair deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/profile", response_class=HTMLResponse)
async def user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """User profile page"""
    try:
        return templates.TemplateResponse(
            "user_profile.html",
            {
                "request": request,
                "user": current_user
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load profile: {str(e)}"
        )


@router.post("/profile/update")
async def update_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update user profile"""
    try:
        form = await request.form()
        
        # Update fields
        if "username" in form:
            # Check if username is already taken
            existing_user = db.query(User).filter(
                User.username == form["username"],
                User.id != current_user.id
            ).first()
            if existing_user:
                raise ValidationError("Username already taken")
            current_user.username = form["username"]
        
        if "email" in form:
            # Check if email is already taken
            existing_user = db.query(User).filter(
                User.email == form["email"],
                User.id != current_user.id
            ).first()
            if existing_user:
                raise ValidationError("Email already taken")
            current_user.email = form["email"]
        
        if "password" in form and form["password"]:
            # Verify current password
            current_password = form.get("current_password")
            if not current_password or not verify_password(current_password, current_user.hashed_password):
                raise ValidationError("Current password is incorrect")
            
            # Update password
            current_user.hashed_password = hash_password(form["password"])
        
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "Profile updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/notifications", response_class=HTMLResponse)
async def notification_settings(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Notification settings page"""
    try:
        # Get user settings
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
        if not user_settings:
            # Create default user settings
            user_settings = UserSettings(
                user_id=current_user.id,
                default_profit_target=5.0,
                default_stop_loss=-3.0,
                max_position_size=10.0,
                preferred_pairs=["BTC/USDT", "ETH/USDT", "BNB/USDT"],
                notification_email=True,
                notification_telegram=False,
                telegram_chat_id="",
                created_at=datetime.utcnow()
            )
            db.add(user_settings)
            db.commit()
        
        return templates.TemplateResponse(
            "notification_settings.html",
            {
                "request": request,
                "user": current_user,
                "user_settings": user_settings
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load notification settings: {str(e)}"
        )


@router.post("/notifications/update")
async def update_notification_settings(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update notification settings"""
    try:
        form = await request.form()
        
        # Get user settings
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
        if not user_settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )
        
        # Update notification settings
        if "notification_email" in form:
            user_settings.notification_email = form["notification_email"] == "on"
        
        if "notification_telegram" in form:
            user_settings.notification_telegram = form["notification_telegram"] == "on"
        
        if "telegram_chat_id" in form:
            user_settings.telegram_chat_id = form["telegram_chat_id"]
        
        user_settings.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "Notification settings updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/api/user-settings")
async def get_user_settings_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """API endpoint for user settings"""
    try:
        # Get user settings
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
        if not user_settings:
            return {"error": "User settings not found"}
        
        return {
            "default_profit_target": user_settings.default_profit_target,
            "default_stop_loss": user_settings.default_stop_loss,
            "max_position_size": user_settings.max_position_size,
            "preferred_pairs": user_settings.preferred_pairs,
            "notification_email": user_settings.notification_email,
            "notification_telegram": user_settings.notification_telegram,
            "telegram_chat_id": user_settings.telegram_chat_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user settings: {str(e)}"
        )


@router.get("/api/system-config")
async def get_system_config_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """API endpoint for system configuration"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Get system configuration
        system_config = db.query(SystemSettings).first()
        if not system_config:
            return {"error": "System configuration not found"}
        
        return {
            "default_profit_target": system_config.default_profit_target,
            "default_stop_loss": system_config.default_stop_loss,
            "max_portfolio_exposure": system_config.max_portfolio_exposure,
            "max_daily_drawdown": system_config.max_daily_drawdown,
            "max_position_size": system_config.max_position_size,
            "min_pairs_count": system_config.min_pairs_count,
            "max_pairs_count": system_config.max_pairs_count,
            "max_operation_duration_hours": system_config.max_operation_duration_hours,
            "min_notional": system_config.min_notional,
            "max_correlation": system_config.max_correlation,
            "var_limit": system_config.var_limit,
            "volatility_limit": system_config.volatility_limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system configuration: {str(e)}"
        )