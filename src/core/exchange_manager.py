"""
Exchange Manager for CryptoSDCA-AI Trading Bot

This module handles connections to multiple cryptocurrency exchanges,
manages API rate limits, handles reconnection, and provides a unified
interface for trading operations across different exchanges.

Supported Exchanges:
- Binance (spot + margin)
- KuCoin (spot + futures) 
- BingX (spot + futures)
- Kraken (spot + margin)
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import ccxt
import ccxt.async_support as ccxt_async
from loguru import logger
import json

from src.config import get_settings
from src.database import async_db_session
from src.models import Exchange, Order, TradingPair, OrderStatus, OrderSide, OrderType, ExchangeStatus
from src.exceptions import CryptoBotException
from sqlalchemy import text


class ExchangeError(CryptoBotException):
    """Exchange-specific errors"""
    pass


@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    change: float
    timestamp: datetime


@dataclass
class Balance:
    """Account balance structure"""
    currency: str
    free: float
    used: float
    total: float


@dataclass
class OrderResult:
    """Order execution result"""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    exchange_response: Optional[Dict] = None


class ExchangeConnector:
    """Individual exchange connection handler"""

    def __init__(self, exchange_config: Exchange):
        self.config = exchange_config
        self.exchange = None
        self.last_request_time = 0
        self.rate_limit_delay = 1.0  # seconds between requests
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def initialize(self):
        """Initialize exchange connection"""
        try:
            # Configure exchange based on type
            exchange_class = getattr(ccxt_async, self.config.name)

            config = {
                'apiKey': self.config.api_key,
                'secret': self.config.api_secret,
                'enableRateLimit': True,
                'rateLimit': self.config.rate_limit,
                'timeout': 30000,
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000,
                }
            }

            # Add passphrase if needed (KuCoin)
            if self.config.api_passphrase:
                config['password'] = self.config.api_passphrase

            # Set sandbox/testnet if enabled
            if self.config.is_testnet:
                config['sandbox'] = True

            self.exchange = exchange_class(config)

            # Test connection
            await self._test_connection()
            self.is_connected = True
            self.reconnect_attempts = 0

            logger.info(f"✅ {self.config.display_name} connected successfully")

        except Exception as e:
            self.is_connected = False
            logger.error(f"❌ Failed to connect to {self.config.display_name}: {e}")
            raise ExchangeError(f"Connection failed: {str(e)}")

    async def _test_connection(self):
        """Test exchange connection"""
        try:
            await self.exchange.load_markets()
            balance = await self.exchange.fetch_balance()
            logger.info(f"✅ Connection test passed for {self.config.display_name}")
        except Exception as e:
            logger.error(f"❌ Connection test failed for {self.config.display_name}: {e}")
            raise

    async def _rate_limit_check(self):
        """Check and enforce rate limits"""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()

    async def _execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                await self._rate_limit_check()
                result = await func(*args, **kwargs)

                # Reset reconnect attempts on successful request
                self.reconnect_attempts = 0
                return result

            except ccxt.NetworkError as e:
                logger.warning(f"Network error on {self.config.display_name} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                raise ExchangeError(f"Network error after {max_retries} attempts: {str(e)}")

            except ccxt.RateLimitExceeded as e:
                logger.warning(f"Rate limit exceeded on {self.config.display_name}")
                await asyncio.sleep(retry_delay * (2 ** attempt))
                continue

            except ccxt.AuthenticationError as e:
                logger.error(f"Authentication error on {self.config.display_name}: {e}")
                self.is_connected = False
                raise ExchangeError(f"Authentication failed: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error on {self.config.display_name}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                raise ExchangeError(f"Request failed: {str(e)}")

        raise ExchangeError(f"Request failed after {max_retries} attempts")

    async def reconnect(self):
        """Attempt to reconnect to exchange"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"❌ Max reconnection attempts reached for {self.config.display_name}")
            return False

        self.reconnect_attempts += 1
        logger.info(f"🔄 Reconnecting to {self.config.display_name} (attempt {self.reconnect_attempts})")

        try:
            await self.close()
            await asyncio.sleep(2 ** self.reconnect_attempts)  # Exponential backoff
            await self.initialize()
            return True
        except Exception as e:
            logger.error(f"❌ Reconnection failed for {self.config.display_name}: {e}")
            return False

    async def get_market_data(self, symbol: str) -> MarketData:
        """Get market data for a symbol"""
        try:
            ticker = await self._execute_with_retry(self.exchange.fetch_ticker, symbol)

            return MarketData(
                symbol=symbol,
                bid=ticker.get('bid', 0),
                ask=ticker.get('ask', 0),
                last=ticker.get('last', 0),
                volume=ticker.get('baseVolume', 0),
                change=ticker.get('percentage', 0),
                timestamp=datetime.fromtimestamp(ticker.get('timestamp', 0) / 1000)
            )
        except Exception as e:
            logger.error(f"❌ Error fetching market data for {symbol} on {self.config.display_name}: {e}")
            raise ExchangeError(f"Market data fetch failed: {str(e)}")

    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List]:
        """Get OHLCV data for technical analysis"""
        try:
            ohlcv = await self._execute_with_retry(
                self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit
            )
            return ohlcv
        except Exception as e:
            logger.error(f"❌ Error fetching OHLCV for {symbol} on {self.config.display_name}: {e}")
            raise ExchangeError(f"OHLCV fetch failed: {str(e)}")

    async def get_balance(self) -> Dict[str, Balance]:
        """Get account balances"""
        try:
            balance_data = await self._execute_with_retry(self.exchange.fetch_balance)

            balances = {}
            for currency, data in balance_data.items():
                if currency not in ['info', 'free', 'used', 'total'] and isinstance(data, dict):
                    balances[currency] = Balance(
                        currency=currency,
                        free=data.get('free', 0),
                        used=data.get('used', 0),
                        total=data.get('total', 0)
                    )

            return balances
        except Exception as e:
            logger.error(f"❌ Error fetching balance on {self.config.display_name}: {e}")
            raise ExchangeError(f"Balance fetch failed: {str(e)}")

    async def place_order(self, symbol: str, side: str, amount: float, 
                         price: Optional[float] = None, order_type: str = 'market') -> OrderResult:
        """Place an order on the exchange"""
        try:
            logger.info(f"📋 Placing {side} order: {amount} {symbol} @ {price} on {self.config.display_name}")

            # Prepare order parameters
            order_params = {}

            if order_type == 'limit' and price is None:
                raise ValueError("Price required for limit orders")

            # Place the order
            if order_type == 'market':
                order_response = await self._execute_with_retry(
                    self.exchange.create_market_order, symbol, side, amount, None, None, order_params
                )
            else:  # limit order
                order_response = await self._execute_with_retry(
                    self.exchange.create_limit_order, symbol, side, amount, price, None, order_params
                )

            logger.info(f"✅ Order placed successfully: {order_response.get('id')}")

            return OrderResult(
                success=True,
                order_id=order_response.get('id'),
                exchange_response=order_response
            )

        except Exception as e:
            logger.error(f"❌ Error placing order on {self.config.display_name}: {e}")
            return OrderResult(
                success=False,
                error_message=str(e)
            )

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            await self._execute_with_retry(self.exchange.cancel_order, order_id, symbol)
            logger.info(f"✅ Order {order_id} canceled successfully on {self.config.display_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error canceling order {order_id} on {self.config.display_name}: {e}")
            return False

    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Get order status"""
        try:
            order = await self._execute_with_retry(self.exchange.fetch_order, order_id, symbol)
            return order
        except Exception as e:
            logger.error(f"❌ Error fetching order {order_id} status on {self.config.display_name}: {e}")
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders"""
        try:
            orders = await self._execute_with_retry(self.exchange.fetch_open_orders, symbol)
            return orders
        except Exception as e:
            logger.error(f"❌ Error fetching open orders on {self.config.display_name}: {e}")
            return []

    async def close(self):
        """Close exchange connection"""
        try:
            if self.exchange:
                await self.exchange.close()
                self.is_connected = False
                logger.info(f"✅ {self.config.display_name} connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing {self.config.display_name} connection: {e}")


class ExchangeManager:
    """Main exchange manager class"""

    def __init__(self):
        self.settings = get_settings()
        self.connectors: Dict[int, ExchangeConnector] = {}
        self.is_initialized = False

    async def initialize(self):
        """Initialize all exchange connections"""
        try:
            logger.info("🔄 Initializing Exchange Manager...")

            # Load exchange configurations from database
            await self._load_exchange_configs()

            # Initialize all connectors
            initialization_tasks = []
            for exchange_id, connector in self.connectors.items():
                task = asyncio.create_task(self._initialize_connector(exchange_id, connector))
                initialization_tasks.append(task)

            # Wait for all initializations to complete
            results = await asyncio.gather(*initialization_tasks, return_exceptions=True)

            # Log results
            successful = sum(1 for result in results if result is True)
            total = len(results)

            logger.info(f"✅ Exchange Manager initialized: {successful}/{total} exchanges connected")
            self.is_initialized = True

        except Exception as e:
            logger.error(f"❌ Exchange Manager initialization failed: {e}")
            raise ExchangeError(f"Initialization failed: {str(e)}")

    async def _load_exchange_configs(self):
        """Load exchange configurations from database"""
        from src.database import get_db_session
        
        db = get_db_session()
        try:
            # Get all active exchanges
            exchanges = db.execute(
                text("SELECT * FROM exchanges WHERE is_active = 1")
            )
            exchange_configs = exchanges.fetchall()

            for config in exchange_configs:
                exchange = Exchange(**dict(config))
                connector = ExchangeConnector(exchange)
                self.connectors[exchange.id] = connector

                logger.info(f"📋 Loaded configuration for {exchange.display_name}")
        finally:
            db.close()

    async def _initialize_connector(self, exchange_id: int, connector: ExchangeConnector) -> bool:
        """Initialize a single connector"""
        try:
            await connector.initialize()

            # Update database status
            from src.database import get_db_session
            
            db = get_db_session()
            try:
                db.execute(
                    text("UPDATE exchanges SET status = :status, last_connected = :last_connected WHERE id = :id"),
                    {"status": ExchangeStatus.CONNECTED.value, "last_connected": datetime.utcnow(), "id": exchange_id}
                )
                db.commit()
            finally:
                db.close()

            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize exchange {exchange_id}: {e}")

            # Update database status
            from src.database import get_db_session
            
            db = get_db_session()
            try:
                db.execute(
                    text("UPDATE exchanges SET status = :status WHERE id = :id"),
                    {"status": ExchangeStatus.ERROR.value, "id": exchange_id}
                )
                db.commit()
            finally:
                db.close()

            return False

    async def get_connector(self, exchange_id: int) -> Optional[ExchangeConnector]:
        """Get exchange connector by ID"""
        connector = self.connectors.get(exchange_id)

        if connector and not connector.is_connected:
            # Try to reconnect
            await connector.reconnect()

        return connector if connector and connector.is_connected else None

    async def get_market_data(self, exchange_id: int, symbol: str) -> Optional[MarketData]:
        """Get market data from specific exchange"""
        connector = await self.get_connector(exchange_id)
        if not connector:
            return None

        try:
            return await connector.get_market_data(symbol)
        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return None

    async def get_best_price(self, symbol: str, side: str) -> Tuple[Optional[float], Optional[int]]:
        """Get best price across all exchanges"""
        best_price = None
        best_exchange_id = None

        tasks = []
        for exchange_id, connector in self.connectors.items():
            if connector.is_connected:
                task = asyncio.create_task(connector.get_market_data(symbol))
                tasks.append((exchange_id, task))

        if not tasks:
            return None, None

        # Wait for all market data
        for exchange_id, task in tasks:
            try:
                market_data = await task
                if not market_data:
                    continue

                price = market_data.ask if side == 'buy' else market_data.bid

                if best_price is None:
                    best_price = price
                    best_exchange_id = exchange_id
                elif (side == 'buy' and price < best_price) or (side == 'sell' and price > best_price):
                    best_price = price
                    best_exchange_id = exchange_id

            except Exception as e:
                logger.error(f"❌ Error getting price from exchange {exchange_id}: {e}")
                continue

        return best_price, best_exchange_id

    async def place_order(self, exchange_id: int, symbol: str, side: str, 
                         amount: float, price: Optional[float] = None, 
                         order_type: str = 'market') -> OrderResult:
        """Place order on specific exchange"""
        connector = await self.get_connector(exchange_id)
        if not connector:
            return OrderResult(success=False, error_message="Exchange not available")

        return await connector.place_order(symbol, side, amount, price, order_type)

    async def cancel_all_orders(self) -> Dict[int, int]:
        """Cancel all open orders across all exchanges"""
        results = {}

        for exchange_id, connector in self.connectors.items():
            if not connector.is_connected:
                continue

            try:
                open_orders = await connector.get_open_orders()
                canceled_count = 0

                for order in open_orders:
                    success = await connector.cancel_order(order['id'], order['symbol'])
                    if success:
                        canceled_count += 1

                results[exchange_id] = canceled_count
                logger.info(f"✅ Canceled {canceled_count} orders on exchange {exchange_id}")

            except Exception as e:
                logger.error(f"❌ Error canceling orders on exchange {exchange_id}: {e}")
                results[exchange_id] = 0

        return results

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all exchange connections"""
        health_status = {
            "status": "healthy",
            "exchanges": {},
            "summary": {
                "total": len(self.connectors),
                "connected": 0,
                "disconnected": 0,
                "error": 0
            }
        }

        for exchange_id, connector in self.connectors.items():
            exchange_health = {
                "name": connector.config.display_name,
                "connected": connector.is_connected,
                "reconnect_attempts": connector.reconnect_attempts,
                "last_request": connector.last_request_time,
                "status": "healthy" if connector.is_connected else "unhealthy"
            }

            if connector.is_connected:
                health_status["summary"]["connected"] += 1
            else:
                health_status["summary"]["disconnected"] += 1
                if connector.reconnect_attempts >= connector.max_reconnect_attempts:
                    health_status["summary"]["error"] += 1
                    exchange_health["status"] = "error"

            health_status["exchanges"][str(exchange_id)] = exchange_health

        # Determine overall status
        if health_status["summary"]["error"] > 0:
            health_status["status"] = "unhealthy"
        elif health_status["summary"]["disconnected"] > 0:
            health_status["status"] = "degraded"

        return health_status

    async def close(self):
        """Close all exchange connections"""
        logger.info("🔄 Closing all exchange connections...")

        close_tasks = []
        for connector in self.connectors.values():
            task = asyncio.create_task(connector.close())
            close_tasks.append(task)

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        self.connectors.clear()
        self.is_initialized = False
        logger.info("✅ All exchange connections closed")


# Export main class
__all__ = ["ExchangeManager", "ExchangeConnector", "MarketData", "Balance", "OrderResult", "ExchangeError"]
