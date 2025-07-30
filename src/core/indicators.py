"""
src/core/indicators.py - Technical Indicators for CryptoSDCA-AI
Implements various technical indicators for market analysis
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np
from loguru import logger

from src.config import get_settings
from src.exceptions import IndicatorError
from src.core.exchange_manager import MarketData


class IndicatorType(Enum):
    """Technical indicator types"""
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    MOVING_AVERAGE = "moving_average"
    VOLUME = "volume"
    STOCHASTIC = "stochastic"
    ADX = "adx"
    ATR = "atr"


@dataclass
class IndicatorResult:
    """Result of technical indicator calculation"""
    indicator_type: IndicatorType
    value: float
    signal: str  # "buy", "sell", "neutral"
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any]


class TechnicalIndicators:
    """Technical indicators calculator and analyzer"""
    
    def __init__(self):
        self.settings = get_settings()
        self.data_cache: Dict[str, List[MarketData]] = {}
        self.indicators_cache: Dict[str, Dict[str, IndicatorResult]] = {}
        self.cache_duration = timedelta(minutes=5)
        
        # Indicator parameters
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
        self.ma_periods = [20, 50, 200]
        self.stoch_k = 14
        self.stoch_d = 3
        self.adx_period = 14
        self.atr_period = 14
        
    async def initialize(self):
        """Initialize technical indicators"""
        try:
            logger.info("🔄 Initializing Technical Indicators...")
            
            # Clear caches
            self.data_cache.clear()
            self.indicators_cache.clear()
            
            logger.info("✅ Technical Indicators initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Technical Indicators: {e}")
            raise IndicatorError(f"Technical Indicators initialization failed: {str(e)}")
    
    async def update_data(self, pair: str, market_data: MarketData):
        """Update market data for a pair"""
        try:
            if pair not in self.data_cache:
                self.data_cache[pair] = []
            
            # Add new data point
            self.data_cache[pair].append(market_data)
            
            # Keep only last 1000 data points to prevent memory issues
            if len(self.data_cache[pair]) > 1000:
                self.data_cache[pair] = self.data_cache[pair][-1000:]
            
            # Clear indicators cache for this pair
            if pair in self.indicators_cache:
                del self.indicators_cache[pair]
                
        except Exception as e:
            logger.error(f"❌ Data update error for {pair}: {e}")
    
    async def get_indicators(self, pair: str) -> Dict[str, float]:
        """Get all technical indicators for a pair"""
        try:
            # Check cache first
            if pair in self.indicators_cache:
                cache_time = self.indicators_cache[pair].get("_cache_time", datetime.min)
                if datetime.utcnow() - cache_time < self.cache_duration:
                    return {k: v.value for k, v in self.indicators_cache[pair].items() if k != "_cache_time"}
            
            # Calculate indicators
            indicators = {}
            
            # Get price data
            prices = self._get_price_data(pair)
            if not prices or len(prices) < 50:
                return {}
            
            # Calculate RSI
            rsi_result = await self._calculate_rsi(prices)
            if rsi_result:
                indicators["rsi"] = rsi_result.value
                indicators["rsi_signal"] = 1 if rsi_result.signal == "buy" else -1 if rsi_result.signal == "sell" else 0
            
            # Calculate MACD
            macd_result = await self._calculate_macd(prices)
            if macd_result:
                indicators["macd"] = macd_result.value
                indicators["macd_signal"] = macd_result.metadata.get("signal_line", 0)
                indicators["macd_histogram"] = macd_result.metadata.get("histogram", 0)
            
            # Calculate Bollinger Bands
            bb_result = await self._calculate_bollinger_bands(prices)
            if bb_result:
                indicators["bb_upper"] = bb_result.metadata.get("upper", 0)
                indicators["bb_middle"] = bb_result.metadata.get("middle", 0)
                indicators["bb_lower"] = bb_result.metadata.get("lower", 0)
                indicators["bb_width"] = bb_result.metadata.get("width", 0)
            
            # Calculate Moving Averages
            ma_results = await self._calculate_moving_averages(prices)
            for period, result in ma_results.items():
                indicators[f"ma_{period}"] = result.value
            
            # Calculate Volume indicators
            volume_result = await self._calculate_volume_indicators(pair)
            if volume_result:
                indicators["volume"] = volume_result.value
                indicators["avg_volume"] = volume_result.metadata.get("avg_volume", 0)
                indicators["volume_ratio"] = volume_result.metadata.get("volume_ratio", 0)
            
            # Calculate Stochastic
            stoch_result = await self._calculate_stochastic(prices)
            if stoch_result:
                indicators["stoch_k"] = stoch_result.value
                indicators["stoch_d"] = stoch_result.metadata.get("stoch_d", 0)
            
            # Calculate ADX
            adx_result = await self._calculate_adx(prices)
            if adx_result:
                indicators["adx"] = adx_result.value
                indicators["di_plus"] = adx_result.metadata.get("di_plus", 0)
                indicators["di_minus"] = adx_result.metadata.get("di_minus", 0)
            
            # Calculate ATR
            atr_result = await self._calculate_atr(prices)
            if atr_result:
                indicators["atr"] = atr_result.value
            
            # Add current price
            if prices:
                indicators["price"] = prices[-1]
            
            # Cache results
            self.indicators_cache[pair] = {
                "_cache_time": datetime.utcnow(),
                **{k: IndicatorResult(
                    indicator_type=IndicatorType.RSI if "rsi" in k else IndicatorType.MACD if "macd" in k else IndicatorType.BOLLINGER_BANDS if "bb" in k else IndicatorType.MOVING_AVERAGE if "ma" in k else IndicatorType.VOLUME if "volume" in k else IndicatorType.STOCHASTIC if "stoch" in k else IndicatorType.ADX if "adx" in k else IndicatorType.ATR if "atr" in k else IndicatorType.RSI,
                    value=v,
                    signal="neutral",
                    confidence=0.5,
                    timestamp=datetime.utcnow(),
                    metadata={}
                ) for k, v in indicators.items() if k != "_cache_time"}
            }
            
            return indicators
            
        except Exception as e:
            logger.error(f"❌ Indicators calculation error for {pair}: {e}")
            return {}
    
    def _get_price_data(self, pair: str) -> List[float]:
        """Get price data for a pair"""
        try:
            if pair not in self.data_cache:
                return []
            
            # Extract closing prices
            prices = [data.close for data in self.data_cache[pair]]
            return prices
            
        except Exception as e:
            logger.error(f"❌ Price data extraction error: {e}")
            return []
    
    async def _calculate_rsi(self, prices: List[float]) -> Optional[IndicatorResult]:
        """Calculate Relative Strength Index (RSI)"""
        try:
            if len(prices) < self.rsi_period + 1:
                return None
            
            # Calculate price changes
            deltas = np.diff(prices)
            
            # Separate gains and losses
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            # Calculate average gains and losses
            avg_gains = self._calculate_ema(gains, self.rsi_period)
            avg_losses = self._calculate_ema(losses, self.rsi_period)
            
            # Calculate RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            # Determine signal
            signal = "neutral"
            if rsi < 30:
                signal = "buy"
            elif rsi > 70:
                signal = "sell"
            
            # Calculate confidence
            confidence = 0.5
            if rsi < 20 or rsi > 80:
                confidence = 0.8
            elif rsi < 30 or rsi > 70:
                confidence = 0.6
            
            return IndicatorResult(
                indicator_type=IndicatorType.RSI,
                value=float(rsi),
                signal=signal,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                metadata={"period": self.rsi_period}
            )
            
        except Exception as e:
            logger.error(f"❌ RSI calculation error: {e}")
            return None
    
    async def _calculate_macd(self, prices: List[float]) -> Optional[IndicatorResult]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            if len(prices) < self.macd_slow + self.macd_signal:
                return None
            
            # Calculate fast and slow EMAs
            ema_fast = self._calculate_ema(prices, self.macd_fast)
            ema_slow = self._calculate_ema(prices, self.macd_slow)
            
            # Calculate MACD line
            macd_line = ema_fast - ema_slow
            
            # Calculate signal line
            signal_line = self._calculate_ema([macd_line], self.macd_signal)
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            # Determine signal
            signal = "neutral"
            if macd_line > signal_line and histogram > 0:
                signal = "buy"
            elif macd_line < signal_line and histogram < 0:
                signal = "sell"
            
            # Calculate confidence
            confidence = 0.5
            if abs(histogram) > abs(macd_line) * 0.1:
                confidence = 0.7
            
            return IndicatorResult(
                indicator_type=IndicatorType.MACD,
                value=float(macd_line),
                signal=signal,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                metadata={
                    "signal_line": float(signal_line),
                    "histogram": float(histogram),
                    "fast_period": self.macd_fast,
                    "slow_period": self.macd_slow,
                    "signal_period": self.macd_signal
                }
            )
            
        except Exception as e:
            logger.error(f"❌ MACD calculation error: {e}")
            return None
    
    async def _calculate_bollinger_bands(self, prices: List[float]) -> Optional[IndicatorResult]:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < self.bb_period:
                return None
            
            # Calculate simple moving average
            sma = np.mean(prices[-self.bb_period:])
            
            # Calculate standard deviation
            std = np.std(prices[-self.bb_period:])
            
            # Calculate bands
            upper_band = sma + (self.bb_std * std)
            lower_band = sma - (self.bb_std * std)
            
            # Calculate bandwidth
            bandwidth = (upper_band - lower_band) / sma * 100
            
            # Determine signal based on current price position
            current_price = prices[-1]
            signal = "neutral"
            
            if current_price < lower_band:
                signal = "buy"
            elif current_price > upper_band:
                signal = "sell"
            
            # Calculate confidence
            confidence = 0.5
            if current_price < lower_band * 0.99 or current_price > upper_band * 1.01:
                confidence = 0.7
            
            return IndicatorResult(
                indicator_type=IndicatorType.BOLLINGER_BANDS,
                value=float(bandwidth),
                signal=signal,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                metadata={
                    "upper": float(upper_band),
                    "middle": float(sma),
                    "lower": float(lower_band),
                    "width": float(bandwidth),
                    "period": self.bb_period,
                    "std_dev": self.bb_std
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Bollinger Bands calculation error: {e}")
            return None
    
    async def _calculate_moving_averages(self, prices: List[float]) -> Dict[int, IndicatorResult]:
        """Calculate multiple moving averages"""
        try:
            results = {}
            
            for period in self.ma_periods:
                if len(prices) < period:
                    continue
                
                # Calculate simple moving average
                sma = np.mean(prices[-period:])
                
                # Determine signal based on price vs MA
                current_price = prices[-1]
                signal = "neutral"
                
                if current_price > sma:
                    signal = "buy"
                else:
                    signal = "sell"
                
                # Calculate confidence
                confidence = 0.5
                price_diff = abs(current_price - sma) / sma
                if price_diff > 0.05:  # 5% difference
                    confidence = 0.7
                
                results[period] = IndicatorResult(
                    indicator_type=IndicatorType.MOVING_AVERAGE,
                    value=float(sma),
                    signal=signal,
                    confidence=confidence,
                    timestamp=datetime.utcnow(),
                    metadata={"period": period}
                )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Moving Averages calculation error: {e}")
            return {}
    
    async def _calculate_volume_indicators(self, pair: str) -> Optional[IndicatorResult]:
        """Calculate volume-based indicators"""
        try:
            if pair not in self.data_cache or len(self.data_cache[pair]) < 20:
                return None
            
            # Get volume data
            volumes = [data.volume for data in self.data_cache[pair]]
            current_volume = volumes[-1]
            avg_volume = np.mean(volumes[-20:])
            
            # Calculate volume ratio
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Determine signal
            signal = "neutral"
            if volume_ratio > 1.5:
                signal = "buy"  # High volume often indicates strong moves
            elif volume_ratio < 0.5:
                signal = "sell"  # Low volume might indicate weak moves
            
            # Calculate confidence
            confidence = 0.5
            if volume_ratio > 2.0 or volume_ratio < 0.3:
                confidence = 0.7
            
            return IndicatorResult(
                indicator_type=IndicatorType.VOLUME,
                value=float(current_volume),
                signal=signal,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                metadata={
                    "avg_volume": float(avg_volume),
                    "volume_ratio": float(volume_ratio)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Volume indicators calculation error: {e}")
            return None
    
    async def _calculate_stochastic(self, prices: List[float]) -> Optional[IndicatorResult]:
        """Calculate Stochastic Oscillator"""
        try:
            if len(prices) < self.stoch_k + self.stoch_d:
                return None
            
            # Get high and low prices (using close price as approximation)
            highs = prices
            lows = prices
            
            # Calculate %K
            lowest_low = min(lows[-self.stoch_k:])
            highest_high = max(highs[-self.stoch_k:])
            
            if highest_high == lowest_low:
                k_percent = 50
            else:
                k_percent = ((prices[-1] - lowest_low) / (highest_high - lowest_low)) * 100
            
            # Calculate %D (SMA of %K)
            k_values = []
            for i in range(self.stoch_d):
                if len(prices) >= self.stoch_k + i:
                    period_low = min(lows[-(self.stoch_k + i):-i])
                    period_high = max(highs[-(self.stoch_k + i):-i])
                    if period_high == period_low:
                        k_val = 50
                    else:
                        k_val = ((prices[-(i + 1)] - period_low) / (period_high - period_low)) * 100
                    k_values.append(k_val)
            
            d_percent = np.mean(k_values) if k_values else k_percent
            
            # Determine signal
            signal = "neutral"
            if k_percent < 20 and d_percent < 20:
                signal = "buy"
            elif k_percent > 80 and d_percent > 80:
                signal = "sell"
            
            # Calculate confidence
            confidence = 0.5
            if (k_percent < 10 and d_percent < 10) or (k_percent > 90 and d_percent > 90):
                confidence = 0.8
            
            return IndicatorResult(
                indicator_type=IndicatorType.STOCHASTIC,
                value=float(k_percent),
                signal=signal,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                metadata={
                    "stoch_d": float(d_percent),
                    "k_period": self.stoch_k,
                    "d_period": self.stoch_d
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Stochastic calculation error: {e}")
            return None
    
    async def _calculate_adx(self, prices: List[float]) -> Optional[IndicatorResult]:
        """Calculate Average Directional Index (ADX)"""
        try:
            if len(prices) < self.adx_period * 2:
                return None
            
            # Calculate True Range and Directional Movement
            tr_values = []
            dm_plus_values = []
            dm_minus_values = []
            
            for i in range(1, len(prices)):
                # True Range
                high = prices[i]  # Using close as approximation
                low = prices[i]
                prev_close = prices[i - 1]
                
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                tr_values.append(tr)
                
                # Directional Movement
                up_move = high - prev_close
                down_move = prev_close - low
                
                if up_move > down_move and up_move > 0:
                    dm_plus = up_move
                    dm_minus = 0
                elif down_move > up_move and down_move > 0:
                    dm_plus = 0
                    dm_minus = down_move
                else:
                    dm_plus = 0
                    dm_minus = 0
                
                dm_plus_values.append(dm_plus)
                dm_minus_values.append(dm_minus)
            
            # Calculate smoothed values
            atr = self._calculate_ema(tr_values, self.adx_period)
            di_plus = self._calculate_ema(dm_plus_values, self.adx_period) / atr * 100
            di_minus = self._calculate_ema(dm_minus_values, self.adx_period) / atr * 100
            
            # Calculate ADX
            dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100
            adx = self._calculate_ema([dx], self.adx_period)
            
            # Determine signal
            signal = "neutral"
            if adx > 25:
                if di_plus > di_minus:
                    signal = "buy"
                else:
                    signal = "sell"
            
            # Calculate confidence
            confidence = 0.5
            if adx > 30:
                confidence = 0.7
            
            return IndicatorResult(
                indicator_type=IndicatorType.ADX,
                value=float(adx),
                signal=signal,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                metadata={
                    "di_plus": float(di_plus),
                    "di_minus": float(di_minus),
                    "period": self.adx_period
                }
            )
            
        except Exception as e:
            logger.error(f"❌ ADX calculation error: {e}")
            return None
    
    async def _calculate_atr(self, prices: List[float]) -> Optional[IndicatorResult]:
        """Calculate Average True Range (ATR)"""
        try:
            if len(prices) < self.atr_period + 1:
                return None
            
            # Calculate True Range
            tr_values = []
            for i in range(1, len(prices)):
                high = prices[i]  # Using close as approximation
                low = prices[i]
                prev_close = prices[i - 1]
                
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                tr_values.append(tr)
            
            # Calculate ATR using EMA
            atr = self._calculate_ema(tr_values, self.atr_period)
            
            return IndicatorResult(
                indicator_type=IndicatorType.ATR,
                value=float(atr),
                signal="neutral",  # ATR doesn't provide directional signals
                confidence=0.5,
                timestamp=datetime.utcnow(),
                metadata={"period": self.atr_period}
            )
            
        except Exception as e:
            logger.error(f"❌ ATR calculation error: {e}")
            return None
    
    def _calculate_ema(self, data: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        try:
            if not data:
                return 0.0
            
            # Convert to numpy array
            data_array = np.array(data)
            
            # Calculate EMA
            alpha = 2.0 / (period + 1)
            ema = data_array[0]
            
            for value in data_array[1:]:
                ema = alpha * value + (1 - alpha) * ema
            
            return float(ema)
            
        except Exception as e:
            logger.error(f"❌ EMA calculation error: {e}")
            return 0.0
    
    async def get_signal_strength(self, pair: str) -> Dict[str, float]:
        """Get overall signal strength for a pair"""
        try:
            indicators = await self.get_indicators(pair)
            if not indicators:
                return {"strength": 0.0, "signal": "neutral"}
            
            # Calculate weighted signal strength
            signals = {
                "rsi": indicators.get("rsi_signal", 0),
                "macd": 1 if indicators.get("macd", 0) > indicators.get("macd_signal", 0) else -1,
                "bb": 1 if indicators.get("price", 0) < indicators.get("bb_lower", 0) else -1 if indicators.get("price", 0) > indicators.get("bb_upper", 0) else 0,
                "volume": 1 if indicators.get("volume_ratio", 1) > 1.5 else -1 if indicators.get("volume_ratio", 1) < 0.5 else 0,
                "stoch": 1 if indicators.get("stoch_k", 50) < 20 and indicators.get("stoch_d", 50) < 20 else -1 if indicators.get("stoch_k", 50) > 80 and indicators.get("stoch_d", 50) > 80 else 0
            }
            
            # Calculate weighted average
            weights = {"rsi": 0.25, "macd": 0.25, "bb": 0.2, "volume": 0.15, "stoch": 0.15}
            total_weight = 0
            weighted_sum = 0
            
            for indicator, signal in signals.items():
                weight = weights.get(indicator, 0)
                total_weight += weight
                weighted_sum += signal * weight
            
            strength = weighted_sum / total_weight if total_weight > 0 else 0
            
            # Determine overall signal
            if strength > 0.3:
                signal = "buy"
            elif strength < -0.3:
                signal = "sell"
            else:
                signal = "neutral"
            
            return {
                "strength": strength,
                "signal": signal,
                "indicators": signals
            }
            
        except Exception as e:
            logger.error(f"❌ Signal strength calculation error: {e}")
            return {"strength": 0.0, "signal": "neutral"}
    
    def clear_cache(self, pair: Optional[str] = None):
        """Clear indicators cache"""
        try:
            if pair:
                if pair in self.indicators_cache:
                    del self.indicators_cache[pair]
                if pair in self.data_cache:
                    del self.data_cache[pair]
            else:
                self.indicators_cache.clear()
                self.data_cache.clear()
                
            logger.info(f"🗑️ Cleared indicators cache for {pair or 'all pairs'}")
            
        except Exception as e:
            logger.error(f"❌ Cache clear error: {e}")


# Export main class
__all__ = ["TechnicalIndicators", "IndicatorResult", "IndicatorType"]