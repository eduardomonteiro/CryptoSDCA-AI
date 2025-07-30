"""
api/routes/history.py - History routes for CryptoSDCA-AI
Handles trade history and operation logs
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from src.config import get_settings
from src.database import get_db_session
from src.models.models import User, TradeHistory, OperationLog, DCAOperation

from src.utils import verify_password, hash_password
from src.exceptions import AuthenticationError, ValidationError

# Initialize router
router = APIRouter(prefix="/history", tags=["history"])

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
async def history_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """History dashboard page"""
    try:
        # Get recent trades
        recent_trades = db.query(TradeHistory).order_by(desc(TradeHistory.created_at)).limit(10).all()
        
        # Get recent operations
        recent_operations = db.query(DCAOperation).order_by(desc(DCAOperation.created_at)).limit(10).all()
        
        # Get statistics
        stats = await get_history_statistics(db, current_user.id)
        
        return templates.TemplateResponse(
            "history.html",
            {
                "request": request,
                "user": current_user,
                "recent_trades": recent_trades,
                "recent_operations": recent_operations,
                "stats": stats
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load history dashboard: {str(e)}"
        )


@router.get("/trades", response_class=HTMLResponse)
async def trade_history(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    pair: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Trade history page with filtering"""
    try:
        # Build query
        query = db.query(TradeHistory)
        
        # Apply filters
        if pair:
            query = query.filter(TradeHistory.pair.ilike(f"%{pair}%"))
        
        if side:
            query = query.filter(TradeHistory.side == side)
        
        if status:
            query = query.filter(TradeHistory.status == status)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(TradeHistory.created_at >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(TradeHistory.created_at <= end_dt)
            except ValueError:
                pass
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        trades = query.order_by(desc(TradeHistory.created_at)).offset(offset).limit(limit).all()
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        
        return templates.TemplateResponse(
            "trade_history.html",
            {
                "request": request,
                "user": current_user,
                "trades": trades,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_prev": page > 1,
                    "has_next": page < total_pages
                },
                "filters": {
                    "pair": pair,
                    "side": side,
                    "status": status,
                    "start_date": start_date,
                    "end_date": end_date
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load trade history: {str(e)}"
        )


@router.get("/operations", response_class=HTMLResponse)
async def operation_history(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    operation_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Operation history page with filtering"""
    try:
        # Build query
        query = db.query(DCAOperation)
        
        # Apply filters
        if operation_type:
            query = query.filter(DCAOperation.operation_type == operation_type)
        
        if status:
            query = query.filter(DCAOperation.status == status)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(DCAOperation.created_at >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(DCAOperation.created_at <= end_dt)
            except ValueError:
                pass
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        operations = query.order_by(desc(DCAOperation.created_at)).offset(offset).limit(limit).all()
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        
        return templates.TemplateResponse(
            "operation_history.html",
            {
                "request": request,
                "user": current_user,
                "operations": operations,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_prev": page > 1,
                    "has_next": page < total_pages
                },
                "filters": {
                    "operation_type": operation_type,
                    "status": status,
                    "start_date": start_date,
                    "end_date": end_date
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load operation history: {str(e)}"
        )


@router.get("/logs", response_class=HTMLResponse)
async def system_logs(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    level: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """System logs page with filtering"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Build query
        query = db.query(OperationLog)
        
        # Apply filters
        if level:
            query = query.filter(OperationLog.level == level)
        
        if module:
            query = query.filter(OperationLog.module.ilike(f"%{module}%"))
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(OperationLog.timestamp >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(OperationLog.timestamp <= end_dt)
            except ValueError:
                pass
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        logs = query.order_by(desc(OperationLog.timestamp)).offset(offset).limit(limit).all()
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        
        return templates.TemplateResponse(
            "system_logs.html",
            {
                "request": request,
                "user": current_user,
                "logs": logs,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_prev": page > 1,
                    "has_next": page < total_pages
                },
                "filters": {
                    "level": level,
                    "module": module,
                    "start_date": start_date,
                    "end_date": end_date
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load system logs: {str(e)}"
        )


@router.get("/analytics", response_class=HTMLResponse)
async def history_analytics(
    request: Request,
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """History analytics page"""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
        else:  # 1y
            start_date = end_date - timedelta(days=365)
        
        # Get analytics data
        analytics = await get_analytics_data(db, current_user.id, start_date, end_date)
        
        return templates.TemplateResponse(
            "history_analytics.html",
            {
                "request": request,
                "user": current_user,
                "analytics": analytics,
                "period": period
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load analytics: {str(e)}"
        )


@router.get("/api/trades")
async def get_trades_api(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    pair: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """API endpoint for trade history"""
    try:
        # Build query
        query = db.query(TradeHistory)
        
        # Apply filters
        if pair:
            query = query.filter(TradeHistory.pair.ilike(f"%{pair}%"))
        
        if side:
            query = query.filter(TradeHistory.side == side)
        
        if status:
            query = query.filter(TradeHistory.status == status)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(TradeHistory.created_at >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(TradeHistory.created_at <= end_dt)
            except ValueError:
                pass
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        trades = query.order_by(desc(TradeHistory.created_at)).offset(offset).limit(limit).all()
        
        # Convert to dict
        trades_data = []
        for trade in trades:
            trades_data.append({
                "id": trade.id,
                "pair": trade.pair,
                "side": trade.side,
                "quantity": float(trade.quantity),
                "price": float(trade.price),
                "total": float(trade.total),
                "status": trade.status,
                "exchange_id": trade.exchange_id,
                "created_at": trade.created_at.isoformat(),
                "updated_at": trade.updated_at.isoformat() if trade.updated_at else None
            })
        
        return {
            "trades": trades_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trades: {str(e)}"
        )


@router.get("/api/operations")
async def get_operations_api(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    operation_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """API endpoint for operation history"""
    try:
        # Build query
        query = db.query(DCAOperation)
        
        # Apply filters
        if operation_type:
            query = query.filter(DCAOperation.operation_type == operation_type)
        
        if status:
            query = query.filter(DCAOperation.status == status)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(DCAOperation.created_at >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(DCAOperation.created_at <= end_dt)
            except ValueError:
                pass
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        operations = query.order_by(desc(DCAOperation.created_at)).offset(offset).limit(limit).all()
        
        # Convert to dict
        operations_data = []
        for operation in operations:
            operations_data.append({
                "id": operation.id,
                "pair": operation.pair,
                "operation_type": operation.operation_type,
                "quantity": float(operation.quantity),
                "price": float(operation.price),
                "total": float(operation.total),
                "status": operation.status,
                "grid_level": operation.grid_level,
                "created_at": operation.created_at.isoformat(),
                "updated_at": operation.updated_at.isoformat() if operation.updated_at else None
            })
        
        return {
            "operations": operations_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get operations: {str(e)}"
        )


@router.get("/api/analytics")
async def get_analytics_api(
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """API endpoint for analytics data"""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
        else:  # 1y
            start_date = end_date - timedelta(days=365)
        
        # Get analytics data
        analytics = await get_analytics_data(db, current_user.id, start_date, end_date)
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


async def get_history_statistics(db: Session, user_id: int) -> Dict[str, Any]:
    """Get history statistics for dashboard"""
    try:
        # Get trade statistics
        total_trades = db.query(TradeHistory).count()
        successful_trades = db.query(TradeHistory).filter(TradeHistory.status == "completed").count()
        failed_trades = db.query(TradeHistory).filter(TradeHistory.status == "failed").count()
        
        # Get operation statistics
        total_operations = db.query(DCAOperation).count()
        active_operations = db.query(DCAOperation).filter(DCAOperation.status == "active").count()
        completed_operations = db.query(DCAOperation).filter(DCAOperation.status == "completed").count()
        
        # Calculate total volume
        total_volume = db.query(func.sum(TradeHistory.total)).scalar() or 0.0
        
        # Calculate total P&L
        total_pnl = db.query(func.sum(TradeHistory.pnl)).scalar() or 0.0
        
        return {
            "trades": {
                "total": total_trades,
                "successful": successful_trades,
                "failed": failed_trades,
                "success_rate": (successful_trades / total_trades * 100) if total_trades > 0 else 0
            },
            "operations": {
                "total": total_operations,
                "active": active_operations,
                "completed": completed_operations
            },
            "volume": {
                "total": float(total_volume)
            },
            "pnl": {
                "total": float(total_pnl)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ History statistics error: {e}")
        return {
            "trades": {"total": 0, "successful": 0, "failed": 0, "success_rate": 0},
            "operations": {"total": 0, "active": 0, "completed": 0},
            "volume": {"total": 0.0},
            "pnl": {"total": 0.0}
        }


async def get_analytics_data(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Get analytics data for the specified period"""
    try:
        # Get daily trade volume
        daily_volume = db.query(
            func.date(TradeHistory.created_at).label('date'),
            func.sum(TradeHistory.total).label('volume')
        ).filter(
            TradeHistory.created_at >= start_date,
            TradeHistory.created_at <= end_date
        ).group_by(
            func.date(TradeHistory.created_at)
        ).all()
        
        # Get daily P&L
        daily_pnl = db.query(
            func.date(TradeHistory.created_at).label('date'),
            func.sum(TradeHistory.pnl).label('pnl')
        ).filter(
            TradeHistory.created_at >= start_date,
            TradeHistory.created_at <= end_date
        ).group_by(
            func.date(TradeHistory.created_at)
        ).all()
        
        # Get top trading pairs
        top_pairs = db.query(
            TradeHistory.pair,
            func.count(TradeHistory.id).label('trade_count'),
            func.sum(TradeHistory.total).label('total_volume')
        ).filter(
            TradeHistory.created_at >= start_date,
            TradeHistory.created_at <= end_date
        ).group_by(
            TradeHistory.pair
        ).order_by(
            desc(func.sum(TradeHistory.total))
        ).limit(10).all()
        
        # Get trade success rate by day
        daily_success_rate = db.query(
            func.date(TradeHistory.created_at).label('date'),
            func.count(TradeHistory.id).label('total_trades'),
            func.sum(func.case([(TradeHistory.status == "completed", 1)], else_=0)).label('successful_trades')
        ).filter(
            TradeHistory.created_at >= start_date,
            TradeHistory.created_at <= end_date
        ).group_by(
            func.date(TradeHistory.created_at)
        ).all()
        
        return {
            "daily_volume": [
                {
                    "date": str(record.date),
                    "volume": float(record.volume)
                }
                for record in daily_volume
            ],
            "daily_pnl": [
                {
                    "date": str(record.date),
                    "pnl": float(record.pnl)
                }
                for record in daily_pnl
            ],
            "top_pairs": [
                {
                    "pair": record.pair,
                    "trade_count": record.trade_count,
                    "total_volume": float(record.total_volume)
                }
                for record in top_pairs
            ],
            "daily_success_rate": [
                {
                    "date": str(record.date),
                    "total_trades": record.total_trades,
                    "successful_trades": record.successful_trades,
                    "success_rate": (record.successful_trades / record.total_trades * 100) if record.total_trades > 0 else 0
                }
                for record in daily_success_rate
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Analytics data error: {e}")
        return {
            "daily_volume": [],
            "daily_pnl": [],
            "top_pairs": [],
            "daily_success_rate": []
        }