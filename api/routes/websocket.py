"""
api/routes/websocket.py - WebSocket Routes for CryptoSDCA-AI
Handles real-time WebSocket connections for live data updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime
import logging

router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = "anonymous"):
        """Accept WebSocket connection and add to active connections"""
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            self.connection_info[websocket] = {
                "user_id": user_id,
                "connected_at": datetime.utcnow().isoformat(),
                "last_ping": datetime.utcnow().isoformat()
            }
            
            # Send welcome message
            await self.send_personal_message({
                "type": "connection_established",
                "message": "Connected to CryptoSDCA-AI WebSocket",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
            
            logging.info(f"WebSocket connection established for user: {user_id}")
            
        except Exception as e:
            logging.error(f"Error establishing WebSocket connection: {e}")
            raise

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection from active connections"""
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            if websocket in self.connection_info:
                user_id = self.connection_info[websocket].get("user_id", "unknown")
                del self.connection_info[websocket]
                logging.info(f"WebSocket connection closed for user: {user_id}")
        except Exception as e:
            logging.error(f"Error during WebSocket disconnect: {e}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logging.error(f"Error sending personal message: {e}")
            # Remove disconnected websocket
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all active WebSocket connections"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected_websockets = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logging.error(f"Error broadcasting to connection: {e}")
                disconnected_websockets.append(connection)
        
        # Remove disconnected websockets
        for ws in disconnected_websockets:
            self.disconnect(ws)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

# Global connection manager instance
manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time communication
    
    Args:
        websocket (WebSocket): WebSocket connection object
    """
    user_id = "anonymous"  # In production, extract from auth token
    
    try:
        await manager.connect(websocket, user_id)
        
        # Start background task to send periodic updates
        update_task = asyncio.create_task(send_periodic_updates(websocket))
        
        while True:
            try:
                # Wait for message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await handle_websocket_message(websocket, message, user_id)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            except Exception as e:
                logging.error(f"Error in WebSocket message handling: {e}")
                await manager.send_personal_message({
                    "type": "error", 
                    "message": "Internal server error",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
                
    except Exception as e:
        logging.error(f"WebSocket connection error: {e}")
    finally:
        # Cleanup
        update_task.cancel()
        manager.disconnect(websocket)

async def handle_websocket_message(websocket: WebSocket, message: dict, user_id: str):
    """
    Handle incoming WebSocket messages
    
    Args:
        websocket (WebSocket): WebSocket connection
        message (dict): Parsed message from client
        user_id (str): User identifier
    """
    message_type = message.get("type", "unknown")
    
    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
    elif message_type == "subscribe":
        # Handle subscription to specific data feeds
        feed = message.get("feed", "")
        await manager.send_personal_message({
            "type": "subscription_confirmed",
            "feed": feed,
            "message": f"Subscribed to {feed} updates",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
    elif message_type == "get_status":
        # Send current bot and system status
        await manager.send_personal_message({
            "type": "status_update",
            "data": {
                "bot_status": "stopped",
                "active_orders": 3,
                "total_profit": 150.75,
                "ai_consensus": "ANALYZING",
                "connected_users": manager.get_connection_count()
            },
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
    else:
        # Unknown message type
        await manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

async def send_periodic_updates(websocket: WebSocket):
    """
    Send periodic updates to WebSocket client
    
    Args:
        websocket (WebSocket): WebSocket connection
    """
    try:
        while True:
            # Send portfolio update every 10 seconds
            await asyncio.sleep(10)
            
            # Mock real-time data - replace with actual data
            update_data = {
                "type": "portfolio_update",
                "data": {
                    "total_profit": 150.75 + (asyncio.get_event_loop().time() % 100),
                    "active_orders": 3,
                    "portfolio_value": 5000.00,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            await manager.send_personal_message(update_data, websocket)
            
    except asyncio.CancelledError:
        # Task was cancelled, cleanup
        pass
    except Exception as e:
        logging.error(f"Error in periodic updates: {e}")

@router.get("/ws/status")
async def websocket_status():
    """
    Get WebSocket service status
    
    Returns:
        dict: WebSocket status information
    """
    return {
        "service": "websocket",
        "status": "running",
        "active_connections": manager.get_connection_count(),
        "timestamp": datetime.utcnow().isoformat()
    }

# Broadcast functions for external use
async def broadcast_bot_status(status: str):
    """Broadcast bot status change to all connected clients"""
    await manager.broadcast({
        "type": "bot_status_update",
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    })

async def broadcast_order_update(order_data: dict):
    """Broadcast order update to all connected clients"""
    await manager.broadcast({
        "type": "order_update", 
        "data": order_data,
        "timestamp": datetime.utcnow().isoformat()
    })

async def broadcast_portfolio_update(portfolio_data: dict):
    """Broadcast portfolio update to all connected clients"""
    await manager.broadcast({
        "type": "portfolio_update",
        "data": portfolio_data,
        "timestamp": datetime.utcnow().isoformat()
    })
