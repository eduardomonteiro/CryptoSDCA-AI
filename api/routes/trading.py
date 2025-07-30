"""
api/routes/trading.py - Trading API Routes for CryptoSDCA-AI
Handles trading operations, order management, and trading history
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, Response
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import csv
import io

router = APIRouter()

# Mock trading history data
mock_trades = [
    {
        "id": "trade_1",
        "pair": "BTC/USDT",
        "side": "BUY",
        "entry_price": 45000.00,
        "exit_price": 45500.00,
        "quantity": 0.001,
        "pnl_usd": 0.50,
        "pnl_percent": 1.11,
        "exchange": "binance",
        "status": "completed",
        "ai_decision": "APPROVE",
        "ai_reasoning": "Strong bullish momentum with RSI support",
        "ai_confidence": 85,
        "entry_time": "2024-01-28T09:15:00",
        "exit_time": "2024-01-28T11:30:00",
        "fees": 0.02,
        "technical_indicators": {
            "rsi": 45.2,
            "macd": 0.12,
            "adx": 28.5,
            "atr": 450.0,
            "bb_upper": 46000.0,
            "bb_lower": 44000.0,
            "volume": 1250000,
            "fear_greed_index": 65
        }
    },
    {
        "id": "trade_2",
        "pair": "ETH/USDT",
        "side": "BUY",
        "entry_price": 3200.00,
        "exit_price": 3150.00,
        "quantity": 0.1,
        "pnl_usd": -5.00,
        "pnl_percent": -1.56,
        "exchange": "kucoin",
        "status": "completed",
        "ai_decision": "APPROVE",
        "ai_reasoning": "Technical indicators showed oversold condition",
        "ai_confidence": 72,
        "entry_time": "2024-01-27T14:20:00",
        "exit_time": "2024-01-27T16:45:00",
        "fees": 0.15,
        "lessons_learned": "Market sentiment shifted unexpectedly due to regulatory news",
        "technical_indicators": {
            "rsi": 25.8,
            "macd": -0.08,
            "adx": 22.1,
            "atr": 85.0,
            "bb_upper": 3250.0,
            "bb_lower": 3150.0,
            "volume": 890000,
            "fear_greed_index": 35
        }
    }
]

@router.get("/history")
async def get_trading_history(
    page: int = Query(1, ge=1),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    pair: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Get trading history with filtering and pagination
    
    Args:
        page: Page number for pagination
        date_from: Start date for filtering (YYYY-MM-DD)
        date_to: End date for filtering (YYYY-MM-DD)
        pair: Trading pair filter
        status: Status filter (completed, cancelled, partial)
        
    Returns:
        dict: Paginated trading history with summary statistics
    """
    try:
        # Apply filters
        filtered_trades = mock_trades.copy()
        
        if pair:
            filtered_trades = [t for t in filtered_trades if t["pair"] == pair]
        
        if status:
            filtered_trades = [t for t in filtered_trades if t["status"] == status]
        
        if date_from:
            filtered_trades = [t for t in filtered_trades if t["entry_time"] >= f"{date_from}T00:00:00"]
        
        if date_to:
            filtered_trades = [t for t in filtered_trades if t["entry_time"] <= f"{date_to}T23:59:59"]
        
        # Pagination
        per_page = 20
        total_trades = len(filtered_trades)
        total_pages = (total_trades + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        paginated_trades = filtered_trades[start_idx:end_idx]
        
        # Calculate summary statistics
        total_profit = sum(t["pnl_usd"] for t in filtered_trades)
        winning_trades = len([t for t in filtered_trades if t["pnl_usd"] > 0])
        losing_trades = len([t for t in filtered_trades if t["pnl_usd"] < 0])
        win_rate = (winning_trades / len(filtered_trades) * 100) if filtered_trades else 0
        
        return JSONResponse({
            "trades": paginated_trades,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_trades": total_trades,
                "per_page": per_page
            },
            "summary": {
                "total_trades": len(filtered_trades),
                "total_profit": round(total_profit, 2),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 1)
            }
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trading history: {str(e)}")

@router.get("/history/{trade_id}")
async def get_trade_details(trade_id: str):
    """
    Get detailed information about a specific trade
    
    Args:
        trade_id: The ID of the trade to retrieve
        
    Returns:
        dict: Detailed trade information
    """
    try:
        trade = next((t for t in mock_trades if t["id"] == trade_id), None)
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        return JSONResponse(trade)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trade details: {str(e)}")

@router.get("/history/export")
async def export_trading_history(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    pair: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Export trading history to CSV
    
    Args:
        date_from: Start date for filtering (YYYY-MM-DD)
        date_to: End date for filtering (YYYY-MM-DD)
        pair: Trading pair filter
        status: Status filter
        
    Returns:
        CSV file with trading history
    """
    try:
        # Apply same filters as history endpoint
        filtered_trades = mock_trades.copy()
        
        if pair:
            filtered_trades = [t for t in filtered_trades if t["pair"] == pair]
        
        if status:
            filtered_trades = [t for t in filtered_trades if t["status"] == status]
        
        if date_from:
            filtered_trades = [t for t in filtered_trades if t["entry_time"] >= f"{date_from}T00:00:00"]
        
        if date_to:
            filtered_trades = [t for t in filtered_trades if t["entry_time"] <= f"{date_to}T23:59:59"]
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV headers
        headers = [
            "Trade ID", "Date/Time", "Pair", "Side", "Entry Price", "Exit Price",
            "Quantity", "P&L ($)", "P&L (%)", "Duration", "Exchange", 
            "AI Decision", "Status", "Fees"
        ]
        writer.writerow(headers)
        
        # CSV data
        for trade in filtered_trades:
            duration = "N/A"
            if trade.get("exit_time"):
                entry_time = datetime.fromisoformat(trade["entry_time"])
                exit_time = datetime.fromisoformat(trade["exit_time"])
                duration_delta = exit_time - entry_time
                duration = str(duration_delta).split('.')[0]  # Remove microseconds
            
            row = [
                trade["id"],
                trade["entry_time"],
                trade["pair"],
                trade["side"],
                trade["entry_price"],
                trade.get("exit_price", "N/A"),
                trade["quantity"],
                trade["pnl_usd"],
                trade["pnl_percent"],
                duration,
                trade["exchange"],
                trade.get("ai_decision", "N/A"),
                trade["status"],
                trade.get("fees", 0)
            ]
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        # Return CSV as download
        filename = f"cryptosdca_trading_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting trading history: {str(e)}")

@router.get("/history/summary")
async def get_trading_summary():
    """
    Get comprehensive trading summary statistics
    
    Returns:
        dict: Trading performance summary
    """
    try:
        all_trades = mock_trades
        
        if not all_trades:
            return JSONResponse({
                "total_trades": 0,
                "total_profit": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0
            })
        
        total_profit = sum(t["pnl_usd"] for t in all_trades)
        winning_trades = len([t for t in all_trades if t["pnl_usd"] > 0])
        losing_trades = len([t for t in all_trades if t["pnl_usd"] < 0])
        win_rate = (winning_trades / len(all_trades) * 100)
        
        # Additional statistics
        profitable_trades = [t for t in all_trades if t["pnl_usd"] > 0]
        losing_trade_list = [t for t in all_trades if t["pnl_usd"] < 0]
        
        best_trade = max(all_trades, key=lambda x: x["pnl_usd"])["pnl_usd"] if all_trades else 0
        worst_trade = min(all_trades, key=lambda x: x["pnl_usd"])["pnl_usd"] if all_trades else 0
        avg_trade = total_profit / len(all_trades) if all_trades else 0
        
        avg_winning_trade = sum(t["pnl_usd"] for t in profitable_trades) / len(profitable_trades) if profitable_trades else 0
        avg_losing_trade = sum(t["pnl_usd"] for t in losing_trade_list) / len(losing_trade_list) if losing_trade_list else 0
        
        profit_factor = abs(sum(t["pnl_usd"] for t in profitable_trades) / sum(t["pnl_usd"] for t in losing_trade_list)) if losing_trade_list else float('inf')
        
        return JSONResponse({
            "total_trades": len(all_trades),
            "total_profit": round(total_profit, 2),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 1),
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "average_trade": round(avg_trade, 2),
            "average_winning_trade": round(avg_winning_trade, 2),
            "average_losing_trade": round(avg_losing_trade, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "N/A"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating trading summary: {str(e)}")

@router.get("/pairs")
async def get_trading_pairs():
    """
    Get list of available trading pairs
    
    Returns:
        dict: List of available trading pairs
    """
    # Mock data - replace with actual exchange API calls
    pairs = [
        {"symbol": "BTC/USDT", "exchange": "binance", "status": "active"},
        {"symbol": "ETH/USDT", "exchange": "binance", "status": "active"},
        {"symbol": "BNB/USDT", "exchange": "binance", "status": "active"},
        {"symbol": "ADA/USDT", "exchange": "kucoin", "status": "active"},
        {"symbol": "DOT/USDT", "exchange": "kucoin", "status": "active"}
    ]
    
    return JSONResponse({
        "pairs": pairs,
        "total_pairs": len(pairs),
        "timestamp": datetime.utcnow().isoformat()
    })

@router.get("/performance/daily")
async def get_daily_performance(
    days: int = Query(30, ge=1, le=365)
):
    """
    Get daily performance data for the specified number of days
    
    Args:
        days: Number of days to retrieve (1-365)
        
    Returns:
        dict: Daily performance data
    """
    try:
        # Mock daily performance data
        daily_data = []
        base_date = datetime.now() - timedelta(days=days)
        
        for i in range(days):
            current_date = base_date + timedelta(days=i)
            # Generate mock data based on historical trades
            daily_pnl = sum(t["pnl_usd"] for t in mock_trades 
                          if t["entry_time"].startswith(current_date.strftime('%Y-%m-%d')))
            
            daily_trades = len([t for t in mock_trades 
                              if t["entry_time"].startswith(current_date.strftime('%Y-%m-%d'))])
            
            daily_data.append({
                "date": current_date.strftime('%Y-%m-%d'),
                "pnl": round(daily_pnl if daily_pnl else (i % 7 - 3) * 10.5, 2),  # Mock data
                "trades": daily_trades if daily_trades else max(0, 5 - (i % 3)),
                "win_rate": round(60 + (i % 20 - 10), 1)
            })
        
        return JSONResponse({
            "daily_performance": daily_data,
            "period_days": days,
            "total_pnl": round(sum(d["pnl"] for d in daily_data), 2),
            "total_trades": sum(d["trades"] for d in daily_data),
            "average_daily_pnl": round(sum(d["pnl"] for d in daily_data) / days, 2)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching daily performance: {str(e)}")
