"""
src/core/risk_manager.py - Risk Manager for CryptoSDCA-AI
Implements comprehensive risk management and capital protection
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from loguru import logger

from src.config import get_settings
from src.exceptions import RiskManagementError
from src.core.exchange_manager import ExchangeManager
from src.database import get_db_session


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Risk metrics for portfolio"""
    total_exposure: float
    daily_drawdown: float
    max_drawdown: float
    sharpe_ratio: float
    volatility: float
    var_95: float  # Value at Risk 95%
    current_risk_level: RiskLevel
    timestamp: datetime


@dataclass
class PositionRisk:
    """Risk metrics for individual position"""
    pair: str
    exposure: float
    unrealized_pnl: float
    risk_score: float
    stop_loss_distance: float
    position_size_ratio: float
    timestamp: datetime


class RiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.settings = get_settings()
        self.exchange_manager = exchange_manager
        
        # Risk parameters
        self.max_portfolio_exposure = self.settings.max_portfolio_exposure
        self.max_daily_drawdown = self.settings.max_daily_drawdown
        self.max_position_size = self.settings.max_position_size
        self.max_correlation = self.settings.max_correlation
        self.var_limit = self.settings.var_limit
        self.volatility_limit = self.settings.volatility_limit
        
        # Risk tracking
        self.current_risk_level = RiskLevel.LOW
        self.daily_pnl_history: List[float] = []
        self.position_risks: Dict[str, PositionRisk] = {}
        self.risk_metrics: Optional[RiskMetrics] = None
        
        # Circuit breakers
        self.trading_suspended = False
        self.suspension_reason = ""
        self.suspension_time = None
        
    async def initialize(self):
        """Initialize risk manager"""
        try:
            logger.info("🔄 Initializing Risk Manager...")
            
            # Load historical data
            await self._load_historical_data()
            
            # Calculate initial risk metrics
            await self._calculate_risk_metrics()
            
            logger.info("✅ Risk Manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Risk Manager: {e}")
            raise RiskManagementError(f"Risk Manager initialization failed: {str(e)}")
    
    async def _load_historical_data(self):
        """Load historical P&L data"""
        try:
            # This would load from the database
            # For now, we'll start with empty history
            logger.info("📋 Loading historical risk data")
            
        except Exception as e:
            logger.error(f"❌ Failed to load historical data: {e}")
    
    async def check_trading_allowed(self) -> bool:
        """Check if trading is currently allowed"""
        try:
            # Check if trading is suspended
            if self.trading_suspended:
                logger.warning(f"⚠️ Trading suspended: {self.suspension_reason}")
                return False
            
            # Check risk level
            if self.current_risk_level == RiskLevel.CRITICAL:
                logger.warning("⚠️ Trading blocked due to critical risk level")
                return False
            
            # Check daily drawdown
            if self.risk_metrics and self.risk_metrics.daily_drawdown <= -self.max_daily_drawdown:
                logger.warning(f"⚠️ Trading blocked due to daily drawdown: {self.risk_metrics.daily_drawdown:.2f}%")
                return False
            
            # Check portfolio exposure
            if self.risk_metrics and self.risk_metrics.total_exposure >= self.max_portfolio_exposure:
                logger.warning(f"⚠️ Trading blocked due to high exposure: {self.risk_metrics.total_exposure:.2f}%")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Trading allowance check error: {e}")
            return False
    
    async def validate_trade(self, pair: str, side: str, quantity: float, price: float) -> Tuple[bool, str]:
        """Validate a proposed trade"""
        try:
            # Check basic parameters
            if quantity <= 0 or price <= 0:
                return False, "Invalid quantity or price"
            
            # Calculate position value
            position_value = quantity * price
            
            # Check position size limit
            if position_value > self.max_position_size:
                return False, f"Position size {position_value:.2f} exceeds limit {self.max_position_size:.2f}"
            
            # Check if we already have this pair
            if pair in self.position_risks:
                current_exposure = self.position_risks[pair].exposure
                if current_exposure + position_value > self.max_position_size:
                    return False, f"Total exposure for {pair} would exceed limit"
            
            # Check portfolio exposure
            total_exposure = await self._calculate_total_exposure()
            if total_exposure + position_value > self.max_portfolio_exposure:
                return False, f"Portfolio exposure would exceed {self.max_portfolio_exposure}%"
            
            # Check correlation risk
            if not await self._check_correlation_risk(pair):
                return False, f"High correlation risk for {pair}"
            
            # Check volatility risk
            if not await self._check_volatility_risk(pair):
                return False, f"High volatility risk for {pair}"
            
            return True, "Trade validated"
            
        except Exception as e:
            logger.error(f"❌ Trade validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    async def _calculate_total_exposure(self) -> float:
        """Calculate total portfolio exposure"""
        try:
            total_exposure = 0.0
            
            # Sum all position exposures
            for position_risk in self.position_risks.values():
                total_exposure += position_risk.exposure
            
            return total_exposure
            
        except Exception as e:
            logger.error(f"❌ Total exposure calculation error: {e}")
            return 0.0
    
    async def _check_correlation_risk(self, pair: str) -> bool:
        """Check correlation risk for a pair"""
        try:
            # This would calculate correlation with existing positions
            # For now, we'll use a simple check
            if len(self.position_risks) >= 5:
                # Limit number of positions to reduce correlation risk
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Correlation risk check error: {e}")
            return False
    
    async def _check_volatility_risk(self, pair: str) -> bool:
        """Check volatility risk for a pair"""
        try:
            # Get recent price data for volatility calculation
            market_data = await self.exchange_manager.get_market_data(1, pair)
            if not market_data:
                return True  # Allow if no data available
            
            # Calculate volatility (simplified)
            # In a real implementation, this would use historical data
            volatility = 0.05  # 5% volatility assumption
            
            if volatility > self.volatility_limit:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Volatility risk check error: {e}")
            return True  # Allow if calculation fails
    
    async def update_position_risk(self, pair: str, exposure: float, unrealized_pnl: float):
        """Update risk metrics for a position"""
        try:
            # Calculate risk score
            risk_score = self._calculate_position_risk_score(exposure, unrealized_pnl)
            
            # Calculate stop loss distance
            stop_loss_distance = self._calculate_stop_loss_distance(pair, unrealized_pnl)
            
            # Calculate position size ratio
            total_exposure = await self._calculate_total_exposure()
            position_size_ratio = exposure / total_exposure if total_exposure > 0 else 0
            
            # Update position risk
            self.position_risks[pair] = PositionRisk(
                pair=pair,
                exposure=exposure,
                unrealized_pnl=unrealized_pnl,
                risk_score=risk_score,
                stop_loss_distance=stop_loss_distance,
                position_size_ratio=position_size_ratio,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"📊 Updated risk for {pair}: exposure={exposure:.2f}, pnl={unrealized_pnl:.2f}, risk_score={risk_score:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Position risk update error: {e}")
    
    def _calculate_position_risk_score(self, exposure: float, unrealized_pnl: float) -> float:
        """Calculate risk score for a position"""
        try:
            # Base risk score on exposure
            base_score = min(exposure / self.max_position_size, 1.0)
            
            # Adjust for P&L
            if unrealized_pnl < 0:
                # Increase risk score for losing positions
                loss_factor = abs(unrealized_pnl) / exposure
                base_score *= (1 + loss_factor)
            
            return min(base_score, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Position risk score calculation error: {e}")
            return 0.5
    
    def _calculate_stop_loss_distance(self, pair: str, unrealized_pnl: float) -> float:
        """Calculate stop loss distance for a position"""
        try:
            # Base stop loss on volatility and position size
            base_stop_loss = 0.05  # 5% base stop loss
            
            # Adjust for P&L
            if unrealized_pnl < 0:
                # Tighten stop loss for losing positions
                loss_factor = abs(unrealized_pnl) / 1000  # Assuming $1000 base position
                base_stop_loss *= (1 - loss_factor)
            
            return max(base_stop_loss, 0.02)  # Minimum 2% stop loss
            
        except Exception as e:
            logger.error(f"❌ Stop loss distance calculation error: {e}")
            return 0.05
    
    async def update_daily_pnl(self, pnl: float):
        """Update daily P&L and check for circuit breakers"""
        try:
            # Add to history
            self.daily_pnl_history.append(pnl)
            
            # Keep only last 30 days
            if len(self.daily_pnl_history) > 30:
                self.daily_pnl_history = self.daily_pnl_history[-30:]
            
            # Check for circuit breakers
            await self._check_circuit_breakers()
            
            # Update risk metrics
            await self._calculate_risk_metrics()
            
        except Exception as e:
            logger.error(f"❌ Daily P&L update error: {e}")
    
    async def _check_circuit_breakers(self):
        """Check for circuit breaker conditions"""
        try:
            if not self.daily_pnl_history:
                return
            
            # Calculate daily drawdown
            daily_pnl = self.daily_pnl_history[-1]
            if daily_pnl < 0:
                drawdown = abs(daily_pnl)
                
                # Check for circuit breaker levels
                if drawdown >= self.max_daily_drawdown * 2:
                    await self._trigger_circuit_breaker("Critical daily drawdown", RiskLevel.CRITICAL)
                elif drawdown >= self.max_daily_drawdown:
                    await self._trigger_circuit_breaker("Daily drawdown limit reached", RiskLevel.HIGH)
            
            # Check for consecutive losses
            if len(self.daily_pnl_history) >= 3:
                recent_pnls = self.daily_pnl_history[-3:]
                if all(pnl < 0 for pnl in recent_pnls):
                    await self._trigger_circuit_breaker("Consecutive daily losses", RiskLevel.MEDIUM)
            
        except Exception as e:
            logger.error(f"❌ Circuit breaker check error: {e}")
    
    async def _trigger_circuit_breaker(self, reason: str, risk_level: RiskLevel):
        """Trigger circuit breaker"""
        try:
            self.trading_suspended = True
            self.suspension_reason = reason
            self.suspension_time = datetime.utcnow()
            self.current_risk_level = risk_level
            
            logger.warning(f"🚨 Circuit breaker triggered: {reason}")
            
            # Notify administrators (would implement notification system)
            await self._notify_administrators(reason, risk_level)
            
        except Exception as e:
            logger.error(f"❌ Circuit breaker trigger error: {e}")
    
    async def _notify_administrators(self, reason: str, risk_level: RiskLevel):
        """Notify administrators of risk events"""
        try:
            # This would send notifications via email, Slack, etc.
            logger.info(f"📧 Risk notification sent: {reason} - Level: {risk_level.value}")
            
        except Exception as e:
            logger.error(f"❌ Administrator notification error: {e}")
    
    async def _calculate_risk_metrics(self):
        """Calculate comprehensive risk metrics"""
        try:
            # Calculate total exposure
            total_exposure = await self._calculate_total_exposure()
            
            # Calculate daily drawdown
            daily_drawdown = 0.0
            if self.daily_pnl_history:
                daily_pnl = self.daily_pnl_history[-1]
                if daily_pnl < 0:
                    daily_drawdown = abs(daily_pnl)
            
            # Calculate max drawdown
            max_drawdown = self._calculate_max_drawdown()
            
            # Calculate Sharpe ratio
            sharpe_ratio = self._calculate_sharpe_ratio()
            
            # Calculate volatility
            volatility = self._calculate_volatility()
            
            # Calculate Value at Risk
            var_95 = self._calculate_var_95()
            
            # Determine risk level
            risk_level = self._determine_risk_level(total_exposure, daily_drawdown, volatility)
            
            # Update risk metrics
            self.risk_metrics = RiskMetrics(
                total_exposure=total_exposure,
                daily_drawdown=daily_drawdown,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                volatility=volatility,
                var_95=var_95,
                current_risk_level=risk_level,
                timestamp=datetime.utcnow()
            )
            
            # Update current risk level
            self.current_risk_level = risk_level
            
        except Exception as e:
            logger.error(f"❌ Risk metrics calculation error: {e}")
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from historical data"""
        try:
            if not self.daily_pnl_history:
                return 0.0
            
            peak = 0.0
            max_dd = 0.0
            
            for pnl in self.daily_pnl_history:
                if pnl > peak:
                    peak = pnl
                
                drawdown = (peak - pnl) / peak if peak > 0 else 0
                max_dd = max(max_dd, drawdown)
            
            return max_dd
            
        except Exception as e:
            logger.error(f"❌ Max drawdown calculation error: {e}")
            return 0.0
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(self.daily_pnl_history) < 2:
                return 0.0
            
            returns = np.diff(self.daily_pnl_history)
            if len(returns) == 0:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            # Annualized Sharpe ratio (assuming daily returns)
            sharpe = (mean_return / std_return) * np.sqrt(252)
            
            return float(sharpe)
            
        except Exception as e:
            logger.error(f"❌ Sharpe ratio calculation error: {e}")
            return 0.0
    
    def _calculate_volatility(self) -> float:
        """Calculate portfolio volatility"""
        try:
            if len(self.daily_pnl_history) < 2:
                return 0.0
            
            returns = np.diff(self.daily_pnl_history)
            volatility = np.std(returns)
            
            # Annualized volatility
            annualized_vol = volatility * np.sqrt(252)
            
            return float(annualized_vol)
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation error: {e}")
            return 0.0
    
    def _calculate_var_95(self) -> float:
        """Calculate 95% Value at Risk"""
        try:
            if len(self.daily_pnl_history) < 10:
                return 0.0
            
            returns = np.diff(self.daily_pnl_history)
            if len(returns) == 0:
                return 0.0
            
            # Calculate 5th percentile (95% VaR)
            var_95 = np.percentile(returns, 5)
            
            return float(abs(var_95))
            
        except Exception as e:
            logger.error(f"❌ VaR calculation error: {e}")
            return 0.0
    
    def _determine_risk_level(self, exposure: float, drawdown: float, volatility: float) -> RiskLevel:
        """Determine current risk level"""
        try:
            risk_score = 0.0
            
            # Exposure risk (30% weight)
            exposure_risk = min(exposure / self.max_portfolio_exposure, 1.0)
            risk_score += exposure_risk * 0.3
            
            # Drawdown risk (40% weight)
            drawdown_risk = min(drawdown / self.max_daily_drawdown, 1.0)
            risk_score += drawdown_risk * 0.4
            
            # Volatility risk (30% weight)
            volatility_risk = min(volatility / self.volatility_limit, 1.0)
            risk_score += volatility_risk * 0.3
            
            # Determine risk level
            if risk_score >= 0.8:
                return RiskLevel.CRITICAL
            elif risk_score >= 0.6:
                return RiskLevel.HIGH
            elif risk_score >= 0.4:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
                
        except Exception as e:
            logger.error(f"❌ Risk level determination error: {e}")
            return RiskLevel.MEDIUM
    
    async def resume_trading(self):
        """Resume trading after circuit breaker"""
        try:
            if not self.trading_suspended:
                return
            
            # Check if enough time has passed
            if self.suspension_time:
                time_since_suspension = datetime.utcnow() - self.suspension_time
                if time_since_suspension < timedelta(hours=1):
                    logger.info("⏳ Trading suspension still active")
                    return
            
            # Check if risk has decreased
            if self.current_risk_level == RiskLevel.CRITICAL:
                logger.info("⏳ Risk level still critical, trading remains suspended")
                return
            
            # Resume trading
            self.trading_suspended = False
            self.suspension_reason = ""
            self.suspension_time = None
            
            logger.info("✅ Trading resumed")
            
        except Exception as e:
            logger.error(f"❌ Trading resume error: {e}")
    
    async def get_risk_report(self) -> Dict[str, Any]:
        """Get comprehensive risk report"""
        try:
            report = {
                "current_risk_level": self.current_risk_level.value,
                "trading_suspended": self.trading_suspended,
                "suspension_reason": self.suspension_reason,
                "position_count": len(self.position_risks),
                "total_exposure": await self._calculate_total_exposure(),
                "daily_pnl": self.daily_pnl_history[-1] if self.daily_pnl_history else 0.0,
                "positions": [
                    {
                        "pair": pr.pair,
                        "exposure": pr.exposure,
                        "unrealized_pnl": pr.unrealized_pnl,
                        "risk_score": pr.risk_score,
                        "position_size_ratio": pr.position_size_ratio
                    }
                    for pr in self.position_risks.values()
                ]
            }
            
            if self.risk_metrics:
                report.update({
                    "daily_drawdown": self.risk_metrics.daily_drawdown,
                    "max_drawdown": self.risk_metrics.max_drawdown,
                    "sharpe_ratio": self.risk_metrics.sharpe_ratio,
                    "volatility": self.risk_metrics.volatility,
                    "var_95": self.risk_metrics.var_95
                })
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Risk report generation error: {e}")
            return {"error": str(e)}


# Export main class
__all__ = ["RiskManager", "RiskMetrics", "PositionRisk", "RiskLevel"]