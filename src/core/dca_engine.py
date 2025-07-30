"""
src/core/dca_engine.py - DCA Engine for CryptoSDCA-AI
Implements intelligent multi-layer Dollar Cost Averaging strategy
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from loguru import logger

from src.config import get_settings
from src.exceptions import TradingError, RiskManagementError
from src.core.exchange_manager import ExchangeManager, MarketData
from src.core.ai_validator import AIValidator, TradeHypothesis, AIDecision
from src.core.sentiment_analyzer import SentimentAnalyzer
from src.core.risk_manager import RiskManager
from src.core.indicators import TechnicalIndicators
from src.database import get_db_session


class DCAStatus(Enum):
    """DCA strategy status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class DCAPosition:
    """DCA position information"""
    pair: str
    exchange_id: int
    total_quantity: float
    average_price: float
    total_invested: float
    current_value: float
    grid_levels: List[Dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class DCASignal:
    """DCA trading signal"""
    pair: str
    side: str  # "buy" or "sell"
    quantity: float
    price: float
    grid_level: int
    confidence: float
    indicators: Dict[str, float]
    timestamp: datetime


class DCAEngine:
    """Intelligent multi-layer DCA trading engine"""
    
    def __init__(
        self,
        exchange_manager: ExchangeManager,
        ai_validator: AIValidator,
        sentiment_analyzer: SentimentAnalyzer,
        risk_manager: RiskManager
    ):
        self.settings = get_settings()
        self.exchange_manager = exchange_manager
        self.ai_validator = ai_validator
        self.sentiment_analyzer = sentiment_analyzer
        self.risk_manager = risk_manager
        self.indicators = TechnicalIndicators()
        
        self.status = DCAStatus.IDLE
        self.positions: Dict[str, DCAPosition] = {}
        self.active_pairs: List[str] = []
        self.daily_profit = 0.0
        self.total_trades = 0
        
        # Grid configuration
        self.grid_config = {
            "sideways": {
                "spacing_min": 1.0,
                "spacing_max": 3.0,
                "width_min": 15.0,
                "width_max": 25.0
            },
            "trend": {
                "spacing_min": 2.0,
                "spacing_max": 5.0,
                "width_min": 25.0,
                "width_max": 40.0
            }
        }
        
        # Trading parameters
        self.profit_target = self.settings.default_profit_target
        self.stop_loss = self.settings.default_stop_loss
        self.max_duration = self.settings.max_operation_duration_hours
        self.min_pairs = self.settings.min_pairs_count
        
    async def initialize(self):
        """Initialize DCA engine"""
        try:
            logger.info("🔄 Initializing DCA Engine...")
            
            # Load existing positions from database
            await self._load_positions()
            
            # Initialize technical indicators
            await self.indicators.initialize()
            
            # Validate configuration
            self._validate_configuration()
            
            logger.info("✅ DCA Engine initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DCA Engine: {e}")
            raise TradingError(f"DCA Engine initialization failed: {str(e)}")
    
    async def _load_positions(self):
        """Load existing DCA positions from database"""
        try:
            # This would load from the database
            # For now, we'll start with empty positions
            logger.info("📋 Loading DCA positions from database")
            
        except Exception as e:
            logger.error(f"❌ Failed to load positions: {e}")
    
    def _validate_configuration(self):
        """Validate DCA configuration"""
        if self.profit_target <= 0:
            raise TradingError("Profit target must be positive")
        
        if self.stop_loss >= 0:
            raise TradingError("Stop loss must be negative")
        
        if self.max_duration <= 0:
            raise TradingError("Max duration must be positive")
        
        if self.min_pairs <= 0:
            raise TradingError("Min pairs must be positive")
    
    async def start_trading_loop(self):
        """Start the main DCA trading loop"""
        if self.status == DCAStatus.RUNNING:
            logger.warning("⚠️ DCA Engine already running")
            return
        
        self.status = DCAStatus.RUNNING
        logger.info("🚀 Starting DCA trading loop")
        
        try:
            while self.status == DCAStatus.RUNNING:
                await self._trading_cycle()
                await asyncio.sleep(60)  # Wait 1 minute between cycles
                
        except Exception as e:
            logger.error(f"❌ DCA trading loop error: {e}")
            self.status = DCAStatus.STOPPED
            raise
    
    async def _trading_cycle(self):
        """Execute one trading cycle"""
        try:
            # 1. Update market data
            await self._update_market_data()
            
            # 2. Analyze sentiment
            sentiment_data = await self.sentiment_analyzer.get_current_sentiment()
            
            # 3. Check risk management
            if not await self.risk_manager.check_trading_allowed():
                logger.warning("⚠️ Trading blocked by risk management")
                return
            
            # 4. Generate trading signals
            signals = await self._generate_signals(sentiment_data)
            
            # 5. Execute trades
            for signal in signals:
                await self._execute_signal(signal)
            
            # 6. Manage existing positions
            await self._manage_positions()
            
            # 7. Update daily statistics
            await self._update_statistics()
            
        except Exception as e:
            logger.error(f"❌ Trading cycle error: {e}")
    
    async def _update_market_data(self):
        """Update market data for all active pairs"""
        try:
            for pair in self.active_pairs:
                # Get market data from exchange
                market_data = await self.exchange_manager.get_market_data(1, pair)
                if market_data:
                    # Update indicators
                    await self.indicators.update_data(pair, market_data)
                    
        except Exception as e:
            logger.error(f"❌ Market data update error: {e}")
    
    async def _generate_signals(self, sentiment_data: Dict[str, Any]) -> List[DCASignal]:
        """Generate DCA trading signals"""
        signals = []
        
        try:
            # Get available pairs
            available_pairs = await self._get_available_pairs()
            
            for pair in available_pairs:
                # Skip if we already have max positions
                if len(self.positions) >= self.settings.min_pairs_count:
                    break
                
                # Skip if we already have this pair
                if pair in self.positions:
                    continue
                
                # Analyze pair for DCA opportunity
                signal = await self._analyze_pair_for_dca(pair, sentiment_data)
                if signal:
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Signal generation error: {e}")
            return []
    
    async def _get_available_pairs(self) -> List[str]:
        """Get list of available trading pairs"""
        try:
            # This would query the database for available pairs
            # For now, return a default list
            return ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "DOT/USDT"]
            
        except Exception as e:
            logger.error(f"❌ Failed to get available pairs: {e}")
            return []
    
    async def _analyze_pair_for_dca(self, pair: str, sentiment_data: Dict[str, Any]) -> Optional[DCASignal]:
        """Analyze a pair for DCA opportunity"""
        try:
            # Get technical indicators
            indicators = await self.indicators.get_indicators(pair)
            if not indicators:
                return None
            
            # Check if conditions are met for DCA entry
            if not self._check_dca_conditions(pair, indicators, sentiment_data):
                return None
            
            # Calculate entry parameters
            entry_price = await self._calculate_entry_price(pair)
            quantity = await self._calculate_position_size(pair, entry_price)
            
            # Create signal
            signal = DCASignal(
                pair=pair,
                side="buy",
                quantity=quantity,
                price=entry_price,
                grid_level=1,
                confidence=0.7,
                indicators=indicators,
                timestamp=datetime.utcnow()
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Pair analysis error for {pair}: {e}")
            return None
    
    def _check_dca_conditions(self, pair: str, indicators: Dict[str, float], sentiment_data: Dict[str, Any]) -> bool:
        """Check if conditions are met for DCA entry"""
        try:
            # RSI conditions
            rsi = indicators.get("rsi", 50)
            if rsi > 70 or rsi < 30:
                return False
            
            # MACD conditions
            macd = indicators.get("macd", 0)
            macd_signal = indicators.get("macd_signal", 0)
            if macd < macd_signal:  # Bearish MACD
                return False
            
            # Bollinger Bands conditions
            bb_upper = indicators.get("bb_upper", 0)
            bb_lower = indicators.get("bb_lower", 0)
            current_price = indicators.get("price", 0)
            
            if current_price > bb_upper or current_price < bb_lower:
                return False
            
            # Sentiment conditions
            fear_greed = sentiment_data.get("fear_greed_index", 50)
            if fear_greed < 20 or fear_greed > 80:
                return False
            
            # Volume conditions
            volume = indicators.get("volume", 0)
            avg_volume = indicators.get("avg_volume", 0)
            if volume < avg_volume * 0.5:  # Low volume
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ DCA conditions check error: {e}")
            return False
    
    async def _calculate_entry_price(self, pair: str) -> float:
        """Calculate optimal entry price"""
        try:
            # Get current market price
            market_data = await self.exchange_manager.get_market_data(1, pair)
            if not market_data:
                raise TradingError(f"Failed to get market data for {pair}")
            
            # Use current price as entry price
            return market_data.last
            
        except Exception as e:
            logger.error(f"❌ Entry price calculation error: {e}")
            raise
    
    async def _calculate_position_size(self, pair: str, entry_price: float) -> float:
        """Calculate position size based on risk management"""
        try:
            # Get account balance
            balances = await self.exchange_manager.get_balance(1)
            if not balances:
                raise TradingError("Failed to get account balance")
            
            # Calculate available balance for this pair
            quote_currency = pair.split('/')[1]  # e.g., USDT from BTC/USDT
            available_balance = balances.get(quote_currency, 0)
            
            if available_balance <= 0:
                raise TradingError(f"Insufficient {quote_currency} balance")
            
            # Calculate position size (1% of available balance)
            position_value = available_balance * 0.01
            quantity = position_value / entry_price
            
            # Apply minimum notional check
            min_notional = self.settings.min_notional
            if position_value < min_notional:
                raise TradingError(f"Position value {position_value} below minimum {min_notional}")
            
            return quantity
            
        except Exception as e:
            logger.error(f"❌ Position size calculation error: {e}")
            raise
    
    async def _execute_signal(self, signal: DCASignal):
        """Execute a DCA trading signal"""
        try:
            logger.info(f"📊 Executing DCA signal: {signal.pair} {signal.side} {signal.quantity}")
            
            # Create trade hypothesis for AI validation
            hypothesis = TradeHypothesis(
                pair=signal.pair,
                side=signal.side,
                quantity=signal.quantity,
                entry_price=signal.price,
                indicators=signal.indicators,
                fear_greed_index=0,  # Would get from sentiment data
                news_sentiment=0.0,  # Would get from sentiment data
                market_context={},
                timestamp=signal.timestamp
            )
            
            # Validate with AI
            ai_results = await self.ai_validator.validate_trade(hypothesis)
            consensus, confidence, reasoning = self.ai_validator.get_consensus(ai_results)
            
            if consensus != AIDecision.APPROVE:
                logger.info(f"❌ AI validation rejected: {reasoning}")
                return
            
            # Execute the trade
            order_result = await self.exchange_manager.place_order(
                exchange_id=1,  # Default exchange
                symbol=signal.pair,
                side=signal.side,
                amount=signal.quantity,
                price=signal.price,
                order_type="market"
            )
            
            if order_result.success:
                # Create DCA position
                await self._create_dca_position(signal, order_result)
                logger.info(f"✅ DCA trade executed: {signal.pair}")
            else:
                logger.error(f"❌ DCA trade failed: {order_result.error_message}")
            
        except Exception as e:
            logger.error(f"❌ Signal execution error: {e}")
    
    async def _create_dca_position(self, signal: DCASignal, order_result: Any):
        """Create a new DCA position"""
        try:
            # Calculate grid levels
            grid_levels = self._calculate_grid_levels(signal.pair, signal.price)
            
            # Create position
            position = DCAPosition(
                pair=signal.pair,
                exchange_id=1,
                total_quantity=signal.quantity,
                average_price=signal.price,
                total_invested=signal.quantity * signal.price,
                current_value=signal.quantity * signal.price,
                grid_levels=grid_levels,
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.positions[signal.pair] = position
            
            # Save to database
            await self._save_position(position)
            
        except Exception as e:
            logger.error(f"❌ Position creation error: {e}")
    
    def _calculate_grid_levels(self, pair: str, base_price: float) -> List[Dict[str, Any]]:
        """Calculate grid levels for DCA strategy"""
        try:
            grid_levels = []
            
            # Determine market type (sideways vs trend)
            market_type = "sideways"  # Would be determined by analysis
            grid_config = self.grid_config[market_type]
            
            # Calculate grid spacing
            spacing = (grid_config["spacing_min"] + grid_config["spacing_max"]) / 2
            
            # Create grid levels
            for level in range(1, 11):  # 10 grid levels
                price_offset = spacing * level
                
                # Buy levels (below current price)
                buy_price = base_price * (1 - price_offset / 100)
                buy_level = {
                    "level": level,
                    "type": "buy",
                    "price": buy_price,
                    "quantity": 0.0,
                    "filled": False
                }
                grid_levels.append(buy_level)
                
                # Sell levels (above current price)
                sell_price = base_price * (1 + price_offset / 100)
                sell_level = {
                    "level": level,
                    "type": "sell",
                    "price": sell_price,
                    "quantity": 0.0,
                    "filled": False
                }
                grid_levels.append(sell_level)
            
            return grid_levels
            
        except Exception as e:
            logger.error(f"❌ Grid level calculation error: {e}")
            return []
    
    async def _manage_positions(self):
        """Manage existing DCA positions"""
        try:
            for pair, position in self.positions.items():
                # Update position value
                await self._update_position_value(position)
                
                # Check profit target
                if await self._check_profit_target(position):
                    await self._close_position(position, "profit_target")
                
                # Check stop loss
                if await self._check_stop_loss(position):
                    await self._close_position(position, "stop_loss")
                
                # Check max duration
                if await self._check_max_duration(position):
                    await self._close_position(position, "max_duration")
                
                # Execute grid orders
                await self._execute_grid_orders(position)
                
        except Exception as e:
            logger.error(f"❌ Position management error: {e}")
    
    async def _update_position_value(self, position: DCAPosition):
        """Update current value of a position"""
        try:
            # Get current market price
            market_data = await self.exchange_manager.get_market_data(1, position.pair)
            if market_data:
                position.current_value = position.total_quantity * market_data.last
                position.updated_at = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"❌ Position value update error: {e}")
    
    async def _check_profit_target(self, position: DCAPosition) -> bool:
        """Check if profit target is reached"""
        try:
            profit_percent = ((position.current_value - position.total_invested) / position.total_invested) * 100
            return profit_percent >= self.profit_target
            
        except Exception as e:
            logger.error(f"❌ Profit target check error: {e}")
            return False
    
    async def _check_stop_loss(self, position: DCAPosition) -> bool:
        """Check if stop loss is triggered"""
        try:
            loss_percent = ((position.current_value - position.total_invested) / position.total_invested) * 100
            return loss_percent <= self.stop_loss
            
        except Exception as e:
            logger.error(f"❌ Stop loss check error: {e}")
            return False
    
    async def _check_max_duration(self, position: DCAPosition) -> bool:
        """Check if max duration is exceeded"""
        try:
            duration = datetime.utcnow() - position.created_at
            return duration.total_seconds() / 3600 >= self.max_duration
            
        except Exception as e:
            logger.error(f"❌ Max duration check error: {e}")
            return False
    
    async def _close_position(self, position: DCAPosition, reason: str):
        """Close a DCA position"""
        try:
            logger.info(f"🔚 Closing position {position.pair} - Reason: {reason}")
            
            # Execute sell order
            order_result = await self.exchange_manager.place_order(
                exchange_id=position.exchange_id,
                symbol=position.pair,
                side="sell",
                amount=position.total_quantity,
                order_type="market"
            )
            
            if order_result.success:
                # Calculate final P&L
                final_value = position.total_quantity * order_result.exchange_response.get("price", position.average_price)
                pnl = final_value - position.total_invested
                
                logger.info(f"✅ Position closed: P&L = ${pnl:.2f}")
                
                # Remove from active positions
                del self.positions[position.pair]
                
                # Save trade history
                await self._save_trade_history(position, pnl, reason)
                
            else:
                logger.error(f"❌ Failed to close position: {order_result.error_message}")
                
        except Exception as e:
            logger.error(f"❌ Position close error: {e}")
    
    async def _execute_grid_orders(self, position: DCAPosition):
        """Execute grid orders for a position"""
        try:
            # Get current market price
            market_data = await self.exchange_manager.get_market_data(1, position.pair)
            if not market_data:
                return
            
            current_price = market_data.last
            
            # Check each grid level
            for level in position.grid_levels:
                if level["filled"]:
                    continue
                
                # Check if price hit grid level
                if level["type"] == "buy" and current_price <= level["price"]:
                    await self._execute_grid_buy(position, level)
                elif level["type"] == "sell" and current_price >= level["price"]:
                    await self._execute_grid_sell(position, level)
                    
        except Exception as e:
            logger.error(f"❌ Grid order execution error: {e}")
    
    async def _execute_grid_buy(self, position: DCAPosition, level: Dict[str, Any]):
        """Execute grid buy order"""
        try:
            # Calculate buy quantity (same as initial position)
            quantity = position.total_quantity / len([l for l in position.grid_levels if l["type"] == "buy"])
            
            # Execute buy order
            order_result = await self.exchange_manager.place_order(
                exchange_id=position.exchange_id,
                symbol=position.pair,
                side="buy",
                amount=quantity,
                price=level["price"],
                order_type="limit"
            )
            
            if order_result.success:
                level["filled"] = True
                level["quantity"] = quantity
                
                # Update position
                position.total_quantity += quantity
                position.total_invested += quantity * level["price"]
                position.average_price = position.total_invested / position.total_quantity
                
                logger.info(f"✅ Grid buy executed: {position.pair} at {level['price']}")
                
        except Exception as e:
            logger.error(f"❌ Grid buy execution error: {e}")
    
    async def _execute_grid_sell(self, position: DCAPosition, level: Dict[str, Any]):
        """Execute grid sell order"""
        try:
            # Calculate sell quantity
            quantity = position.total_quantity / len([l for l in position.grid_levels if l["type"] == "sell"])
            
            # Execute sell order
            order_result = await self.exchange_manager.place_order(
                exchange_id=position.exchange_id,
                symbol=position.pair,
                side="sell",
                amount=quantity,
                price=level["price"],
                order_type="limit"
            )
            
            if order_result.success:
                level["filled"] = True
                level["quantity"] = quantity
                
                # Update position
                position.total_quantity -= quantity
                
                logger.info(f"✅ Grid sell executed: {position.pair} at {level['price']}")
                
        except Exception as e:
            logger.error(f"❌ Grid sell execution error: {e}")
    
    async def _update_statistics(self):
        """Update daily trading statistics"""
        try:
            # Calculate daily profit
            total_invested = sum(p.total_invested for p in self.positions.values())
            total_value = sum(p.current_value for p in self.positions.values())
            self.daily_profit = total_value - total_invested
            
            # Log statistics
            logger.info(f"📊 Daily P&L: ${self.daily_profit:.2f}, Active positions: {len(self.positions)}")
            
        except Exception as e:
            logger.error(f"❌ Statistics update error: {e}")
    
    async def _save_position(self, position: DCAPosition):
        """Save position to database"""
        try:
            # This would save to the database
            logger.info(f"💾 Saved position: {position.pair}")
            
        except Exception as e:
            logger.error(f"❌ Position save error: {e}")
    
    async def _save_trade_history(self, position: DCAPosition, pnl: float, reason: str):
        """Save trade history to database"""
        try:
            # This would save to the trade_history table
            logger.info(f"💾 Saved trade history: {position.pair}, P&L: ${pnl:.2f}, Reason: {reason}")
            
        except Exception as e:
            logger.error(f"❌ Trade history save error: {e}")
    
    async def stop(self):
        """Stop DCA engine"""
        self.status = DCAStatus.STOPPED
        logger.info("🛑 DCA Engine stopped")
    
    async def pause(self):
        """Pause DCA engine"""
        self.status = DCAStatus.PAUSED
        logger.info("⏸️ DCA Engine paused")
    
    async def resume(self):
        """Resume DCA engine"""
        self.status = DCAStatus.RUNNING
        logger.info("▶️ DCA Engine resumed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get DCA engine status"""
        return {
            "status": self.status.value,
            "active_positions": len(self.positions),
            "daily_profit": self.daily_profit,
            "total_trades": self.total_trades,
            "positions": [
                {
                    "pair": p.pair,
                    "quantity": p.total_quantity,
                    "average_price": p.average_price,
                    "current_value": p.current_value,
                    "pnl": p.current_value - p.total_invested
                }
                for p in self.positions.values()
            ]
        }
    
    async def close(self):
        """Close DCA engine"""
        try:
            # Stop the engine
            await self.stop()
            
            # Close all positions if needed
            for position in list(self.positions.values()):
                await self._close_position(position, "engine_shutdown")
            
            logger.info("✅ DCA Engine closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing DCA Engine: {e}")


# Export main class
__all__ = ["DCAEngine", "DCAPosition", "DCASignal", "DCAStatus"]