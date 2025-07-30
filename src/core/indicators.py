"""
src/core/indicators.py
Technical Indicators Engine for CryptoSDCA-AI

Implements all technical indicators used by the trading bot:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- ATR (Average True Range)
- Bollinger Bands
- Moving Averages (SMA, EMA)
- ADX (Average Directional Index)
- Stochastic Oscillator
- OBV (On-Balance Volume)
- Fibonacci Retracements
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from src.config import get_settings


@dataclass
class IndicatorResult:
    """Resultado de um indicador técnico"""
    value: float
    signal: str  # "BUY", "SELL", "NEUTRAL"
    strength: float  # 0.0 to 1.0
    timestamp: datetime
    details: Dict[str, Any]


@dataclass
class MarketCondition:
    """Condições de mercado baseadas em múltiplos indicadores"""
    trend_direction: str  # "BULLISH", "BEARISH", "SIDEWAYS"
    trend_strength: float  # 0.0 to 1.0
    volatility: str  # "LOW", "MEDIUM", "HIGH"
    momentum: str  # "STRONG", "WEAK", "NEUTRAL"
    overall_signal: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 to 1.0


class TechnicalIndicators:
    """
    Engine para cálculo de indicadores técnicos
    Processa dados OHLCV e retorna sinais de trading
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.config = self._get_indicator_config()
        
    def _get_indicator_config(self) -> Dict[str, Dict]:
        """Get indicator configuration from settings"""
        return {
            "rsi": {
                "period": getattr(self.settings, 'rsi_period', 14),
                "oversold": getattr(self.settings, 'rsi_oversold', 30),
                "overbought": getattr(self.settings, 'rsi_overbought', 70)
            },
            "macd": {
                "fast": getattr(self.settings, 'macd_fast_period', 12),
                "slow": getattr(self.settings, 'macd_slow_period', 26),
                "signal": getattr(self.settings, 'macd_signal_period', 9)
            },
            "atr": {
                "period": getattr(self.settings, 'atr_period', 14),
                "multiplier": getattr(self.settings, 'atr_stop_multiplier', 2.0)
            },
            "bollinger": {
                "period": 20,
                "std_dev": 2.0
            },
            "adx": {
                "period": 14,
                "strong_trend": 25,
                "weak_trend": 20
            },
            "stochastic": {
                "k_period": 14,
                "d_period": 3,
                "overbought": 80,
                "oversold": 20
            }
        }
        
    def calculate_rsi(
        self, 
        prices: List[float], 
        period: Optional[int] = None
    ) -> IndicatorResult:
        """
        Calcula Relative Strength Index (RSI)
        
        Args:
            prices: Lista de preços de fechamento
            period: Período do RSI (default: configuração)
        
        Returns:
            IndicatorResult com valor RSI e sinal
        """
        if period is None:
            period = self.config["rsi"]["period"]
            
        if len(prices) < period + 1:
            return IndicatorResult(50.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        # Converter para pandas Series
        price_series = pd.Series(prices)
        
        # Calcular mudanças de preço
        delta = price_series.diff()
        
        # Separar ganhos e perdas
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        
        # Calcular médias móveis exponenciais
        avg_gains = gains.rolling(window=period, min_periods=period).mean()
        avg_losses = losses.rolling(window=period, min_periods=period).mean()
        
        # Calcular RS e RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        
        # Determinar sinal
        oversold = self.config["rsi"]["oversold"]
        overbought = self.config["rsi"]["overbought"]
        
        if current_rsi < oversold:
            signal = "BUY"
            strength = (oversold - current_rsi) / oversold
        elif current_rsi > overbought:
            signal = "SELL"
            strength = (current_rsi - overbought) / (100 - overbought)
        else:
            signal = "NEUTRAL"
            strength = 0.5
            
        return IndicatorResult(
            value=current_rsi,
            signal=signal,
            strength=min(strength, 1.0),
            timestamp=datetime.utcnow(),
            details={
                "oversold_level": oversold,
                "overbought_level": overbought,
                "period": period
            }
        )
        
    def calculate_macd(
        self, 
        prices: List[float],
        fast_period: Optional[int] = None,
        slow_period: Optional[int] = None,
        signal_period: Optional[int] = None
    ) -> IndicatorResult:
        """
        Calcula MACD (Moving Average Convergence Divergence)
        
        Returns:
            IndicatorResult com MACD line, signal line e histograma
        """
        if fast_period is None:
            fast_period = self.config["macd"]["fast"]
        if slow_period is None:
            slow_period = self.config["macd"]["slow"]
        if signal_period is None:
            signal_period = self.config["macd"]["signal"]
            
        if len(prices) < slow_period + signal_period:
            return IndicatorResult(0.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        price_series = pd.Series(prices)
        
        # Calcular EMAs
        ema_fast = price_series.ewm(span=fast_period).mean()
        ema_slow = price_series.ewm(span=slow_period).mean()
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line
        signal_line = macd_line.ewm(span=signal_period).mean()
        
        # Histograma
        histogram = macd_line - signal_line
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        
        # Determinar sinal baseado no cruzamento
        prev_histogram = histogram.iloc[-2] if len(histogram) > 1 else 0
        
        if current_histogram > 0 and prev_histogram <= 0:
            signal = "BUY"
            strength = min(abs(current_histogram) / abs(current_macd), 1.0)
        elif current_histogram < 0 and prev_histogram >= 0:
            signal = "SELL"
            strength = min(abs(current_histogram) / abs(current_macd), 1.0)
        else:
            signal = "NEUTRAL"
            strength = 0.5
            
        return IndicatorResult(
            value=current_macd,
            signal=signal,
            strength=strength,
            timestamp=datetime.utcnow(),
            details={
                "macd_line": current_macd,
                "signal_line": current_signal,
                "histogram": current_histogram,
                "fast_period": fast_period,
                "slow_period": slow_period,
                "signal_period": signal_period
            }
        )
        
    def calculate_atr(
        self, 
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: Optional[int] = None
    ) -> IndicatorResult:
        """
        Calcula Average True Range (ATR) para medir volatilidade
        
        Returns:
            IndicatorResult com valor ATR e nível de volatilidade
        """
        if period is None:
            period = self.config["atr"]["period"]
            
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return IndicatorResult(0.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        # Calcular True Range
        true_ranges = []
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            true_ranges.append(max(tr1, tr2, tr3))
        
        # Calcular ATR usando média móvel simples
        if len(true_ranges) < period:
            return IndicatorResult(0.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        atr_values = []
        for i in range(period-1, len(true_ranges)):
            atr = sum(true_ranges[i-period+1:i+1]) / period
            atr_values.append(atr)
        
        current_atr = atr_values[-1] if atr_values else 0.0
        current_price = closes[-1]
        
        # Determinar nível de volatilidade
        atr_percent = (current_atr / current_price) * 100
        
        if atr_percent < 1.0:
            volatility = "LOW"
            signal = "NEUTRAL"
            strength = 0.3
        elif atr_percent < 3.0:
            volatility = "MEDIUM"
            signal = "NEUTRAL" 
            strength = 0.6
        else:
            volatility = "HIGH"
            signal = "NEUTRAL"
            strength = 0.9
            
        return IndicatorResult(
            value=current_atr,
            signal=signal,
            strength=strength,
            timestamp=datetime.utcnow(),
            details={
                "atr_percent": atr_percent,
                "volatility": volatility,
                "period": period,
                "stop_loss_distance": current_atr * self.config["atr"]["multiplier"]
            }
        )
        
    def calculate_bollinger_bands(
        self,
        prices: List[float],
        period: Optional[int] = None,
        std_dev: Optional[float] = None
    ) -> IndicatorResult:
        """
        Calcula Bollinger Bands
        
        Returns:
            IndicatorResult com bandas superiores, inferiores e sinal
        """
        if period is None:
            period = self.config["bollinger"]["period"]
        if std_dev is None:
            std_dev = self.config["bollinger"]["std_dev"]
            
        if len(prices) < period:
            return IndicatorResult(0.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        price_series = pd.Series(prices)
        
        # Calcular SMA e desvio padrão
        sma = price_series.rolling(window=period).mean()
        std = price_series.rolling(window=period).std()
        
        # Calcular bandas
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        current_price = prices[-1]
        current_sma = sma.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        # Determinar sinal baseado na posição do preço
        band_width = current_upper - current_lower
        price_position = (current_price - current_lower) / band_width
        
        if current_price <= current_lower:
            signal = "BUY"
            strength = 1.0 - price_position
        elif current_price >= current_upper:
            signal = "SELL"
            strength = price_position
        else:
            signal = "NEUTRAL"
            strength = 0.5
            
        return IndicatorResult(
            value=current_sma,
            signal=signal,
            strength=min(max(strength, 0.0), 1.0),
            timestamp=datetime.utcnow(),
            details={
                "upper_band": current_upper,
                "lower_band": current_lower,
                "price_position": price_position,
                "band_width": band_width,
                "squeeze": band_width < (current_sma * 0.05)  # Band squeeze indicator
            }
        )
        
    def calculate_moving_averages(
        self,
        prices: List[float],
        short_period: int = 50,
        long_period: int = 200
    ) -> IndicatorResult:
        """
        Calcula médias móveis simples e exponenciais
        
        Returns:
            IndicatorResult com cruzamento de médias e tendência
        """
        if len(prices) < long_period:
            return IndicatorResult(0.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        price_series = pd.Series(prices)
        
        # SMAs
        sma_short = price_series.rolling(window=short_period).mean()
        sma_long = price_series.rolling(window=long_period).mean()
        
        # EMAs
        ema_short = price_series.ewm(span=short_period).mean()
        ema_long = price_series.ewm(span=long_period).mean()
        
        current_sma_short = sma_short.iloc[-1]
        current_sma_long = sma_long.iloc[-1]
        current_ema_short = ema_short.iloc[-1]
        current_ema_long = ema_long.iloc[-1]
        current_price = prices[-1]
        
        # Determinar tendência e sinal
        if current_sma_short > current_sma_long and current_ema_short > current_ema_long:
            if current_price > current_sma_short:
                signal = "BUY"
                strength = 0.8
            else:
                signal = "NEUTRAL"
                strength = 0.6
        elif current_sma_short < current_sma_long and current_ema_short < current_ema_long:
            if current_price < current_sma_short:
                signal = "SELL"
                strength = 0.8
            else:
                signal = "NEUTRAL"
                strength = 0.6
        else:
            signal = "NEUTRAL"
            strength = 0.4
            
        return IndicatorResult(
            value=current_sma_short,
            signal=signal,
            strength=strength,
            timestamp=datetime.utcnow(),
            details={
                "sma_short": current_sma_short,
                "sma_long": current_sma_long,
                "ema_short": current_ema_short,
                "ema_long": current_ema_long,
                "golden_cross": current_sma_short > current_sma_long,
                "death_cross": current_sma_short < current_sma_long
            }
        )
        
    def calculate_adx(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: Optional[int] = None
    ) -> IndicatorResult:
        """
        Calcula Average Directional Index (ADX)
        
        Returns:
            IndicatorResult com força da tendência
        """
        if period is None:
            period = self.config["adx"]["period"]
            
        if len(highs) < period * 2 or len(lows) < period * 2 or len(closes) < period * 2:
            return IndicatorResult(0.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        # Calcular True Range e Directional Movement
        tr_list = []
        dm_plus_list = []
        dm_minus_list = []
        
        for i in range(1, len(closes)):
            # True Range
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr = max(tr1, tr2, tr3)
            tr_list.append(tr)
            
            # Directional Movement
            dm_plus = max(highs[i] - highs[i-1], 0) if highs[i] - highs[i-1] > lows[i-1] - lows[i] else 0
            dm_minus = max(lows[i-1] - lows[i], 0) if lows[i-1] - lows[i] > highs[i] - highs[i-1] else 0
            
            dm_plus_list.append(dm_plus)
            dm_minus_list.append(dm_minus)
        
        if len(tr_list) < period:
            return IndicatorResult(0.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        # Calcular smoothed values
        tr_smooth = sum(tr_list[-period:]) / period
        dm_plus_smooth = sum(dm_plus_list[-period:]) / period
        dm_minus_smooth = sum(dm_minus_list[-period:]) / period
        
        # Calcular DI+ e DI-
        di_plus = (dm_plus_smooth / tr_smooth) * 100
        di_minus = (dm_minus_smooth / tr_smooth) * 100
        
        # Calcular DX e ADX
        dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100 if (di_plus + di_minus) != 0 else 0
        
        # Para simplificar, usaremos o DX como ADX (normalmente ADX é uma média móvel do DX)
        adx_value = dx
        
        # Determinar força da tendência
        strong_trend = self.config["adx"]["strong_trend"]
        weak_trend = self.config["adx"]["weak_trend"]
        
        if adx_value > strong_trend:
            if di_plus > di_minus:
                signal = "BUY"
                strength = 0.8
            else:
                signal = "SELL"
                strength = 0.8
        elif adx_value > weak_trend:
            signal = "NEUTRAL"
            strength = 0.5
        else:
            signal = "NEUTRAL"
            strength = 0.2
            
        return IndicatorResult(
            value=adx_value,
            signal=signal,
            strength=strength,
            timestamp=datetime.utcnow(),
            details={
                "di_plus": di_plus,
                "di_minus": di_minus,
                "trend_strength": "STRONG" if adx_value > strong_trend else "WEAK" if adx_value > weak_trend else "NO_TREND",
                "period": period
            }
        )
        
    def calculate_stochastic(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        k_period: Optional[int] = None,
        d_period: Optional[int] = None
    ) -> IndicatorResult:
        """
        Calcula Stochastic Oscillator
        
        Returns:
            IndicatorResult com %K, %D e sinal
        """
        if k_period is None:
            k_period = self.config["stochastic"]["k_period"]
        if d_period is None:
            d_period = self.config["stochastic"]["d_period"]
            
        if len(highs) < k_period or len(lows) < k_period or len(closes) < k_period:
            return IndicatorResult(50.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        # Calcular %K
        k_values = []
        for i in range(k_period-1, len(closes)):
            high_max = max(highs[i-k_period+1:i+1])
            low_min = min(lows[i-k_period+1:i+1])
            current_close = closes[i]
            
            if high_max == low_min:
                k_percent = 50.0
            else:
                k_percent = ((current_close - low_min) / (high_max - low_min)) * 100
                
            k_values.append(k_percent)
        
        if len(k_values) < d_period:
            return IndicatorResult(50.0, "NEUTRAL", 0.0, datetime.utcnow(), {})
            
        # Calcular %D (média móvel simples do %K)
        d_values = []
        for i in range(d_period-1, len(k_values)):
            d_percent = sum(k_values[i-d_period+1:i+1]) / d_period
            d_values.append(d_percent)
        
        current_k = k_values[-1]
        current_d = d_values[-1] if d_values else current_k
        
        # Determinar sinal
        overbought = self.config["stochastic"]["overbought"]
        oversold = self.config["stochastic"]["oversold"]
        
        if current_k < oversold and current_d < oversold:
            signal = "BUY"
            strength = (oversold - current_k) / oversold
        elif current_k > overbought and current_d > overbought:
            signal = "SELL"
            strength = (current_k - overbought) / (100 - overbought)
        else:
            signal = "NEUTRAL"
            strength = 0.5
            
        return IndicatorResult(
            value=current_k,
            signal=signal,
            strength=min(strength, 1.0),
            timestamp=datetime.utcnow(),
            details={
                "k_percent": current_k,
                "d_percent": current_d,
                "overbought_level": overbought,
                "oversold_level": oversold,
                "k_period": k_period,
                "d_period": d_period
            }
        )
        
    def calculate_fibonacci_retracements(
        self,
        high_price: float,
        low_price: float,
        trend_direction: str = "UP"
    ) -> Dict[str, float]:
        """
        Calcula níveis de retração de Fibonacci
        
        Args:
            high_price: Preço máximo do movimento
            low_price: Preço mínimo do movimento
            trend_direction: "UP" ou "DOWN"
        
        Returns:
            Dict com níveis de Fibonacci
        """
        price_range = high_price - low_price
        
        fib_levels = {
            "0.0": high_price if trend_direction == "UP" else low_price,
            "23.6": None,
            "38.2": None,
            "50.0": None,
            "61.8": None,
            "78.6": None,
            "100.0": low_price if trend_direction == "UP" else high_price
        }
        
        if trend_direction == "UP":
            # Retração de tendência de alta
            fib_levels["23.6"] = high_price - (price_range * 0.236)
            fib_levels["38.2"] = high_price - (price_range * 0.382)
            fib_levels["50.0"] = high_price - (price_range * 0.500)
            fib_levels["61.8"] = high_price - (price_range * 0.618)
            fib_levels["78.6"] = high_price - (price_range * 0.786)
        else:
            # Retração de tendência de baixa
            fib_levels["23.6"] = low_price + (price_range * 0.236)
            fib_levels["38.2"] = low_price + (price_range * 0.382)
            fib_levels["50.0"] = low_price + (price_range * 0.500)
            fib_levels["61.8"] = low_price + (price_range * 0.618)
            fib_levels["78.6"] = low_price + (price_range * 0.786)
            
        return fib_levels
        
    def analyze_market_conditions(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
    ) -> MarketCondition:
        """
        Analisa condições gerais do mercado usando múltiplos indicadores
        
        Returns:
            MarketCondition com análise consolidada
        """
        try:
            # Calcular indicadores principais
            rsi = self.calculate_rsi(closes)
            macd = self.calculate_macd(closes)
            atr = self.calculate_atr(highs, lows, closes)
            bollinger = self.calculate_bollinger_bands(closes)
            ma = self.calculate_moving_averages(closes)
            adx = self.calculate_adx(highs, lows, closes)
            stoch = self.calculate_stochastic(highs, lows, closes)
            
            # Analisar tendência
            trend_indicators = [ma.signal, adx.signal]
            bullish_count = trend_indicators.count("BUY")
            bearish_count = trend_indicators.count("SELL")
            
            if bullish_count > bearish_count:
                trend_direction = "BULLISH"
                trend_strength = (bullish_count / len(trend_indicators))
            elif bearish_count > bullish_count:
                trend_direction = "BEARISH"
                trend_strength = (bearish_count / len(trend_indicators))
            else:
                trend_direction = "SIDEWAYS"
                trend_strength = 0.5
                
            # Analisar volatilidade
            atr_details = atr.details
            volatility = atr_details.get("volatility", "MEDIUM")
            
            # Analisar momentum
            momentum_indicators = [rsi.signal, macd.signal, stoch.signal]
            momentum_bullish = momentum_indicators.count("BUY")
            momentum_bearish = momentum_indicators.count("SELL")
            
            if momentum_bullish > momentum_bearish:
                momentum = "STRONG"
            elif momentum_bearish > momentum_bullish:
                momentum = "WEAK"
            else:
                momentum = "NEUTRAL"
                
            # Determinar sinal geral
            all_signals = [rsi.signal, macd.signal, bollinger.signal, ma.signal, stoch.signal]
            buy_signals = all_signals.count("BUY")
            sell_signals = all_signals.count("SELL")
            
            if buy_signals >= 3:
                overall_signal = "BUY"
                confidence = buy_signals / len(all_signals)
            elif sell_signals >= 3:
                overall_signal = "SELL"
                confidence = sell_signals / len(all_signals)
            else:
                overall_signal = "HOLD"
                confidence = 0.5
                
            return MarketCondition(
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                volatility=volatility,
                momentum=momentum,
                overall_signal=overall_signal,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return MarketCondition(
                trend_direction="SIDEWAYS",
                trend_strength=0.5,
                volatility="MEDIUM",
                momentum="NEUTRAL",
                overall_signal="HOLD",
                confidence=0.0
            )
            
    def get_dynamic_grid_config(
        self,
        market_condition: MarketCondition,
        current_price: float,
        atr_value: float
    ) -> Dict[str, Any]:
        """
        Gera configuração dinâmica de grid baseada nas condições do mercado
        
        Returns:
            Dict com configuração do grid DCA
        """
        base_spacing = (atr_value / current_price) * 100  # ATR como % do preço
        
        if market_condition.trend_direction == "SIDEWAYS":
            # Grid lateral - espaçamento menor
            grid_spacing_min = max(base_spacing * 0.5, 1.0)
            grid_spacing_max = min(base_spacing * 1.5, 3.0)
            grid_width = 15.0  # ±15% do preço central
            
        elif market_condition.volatility == "HIGH":
            # Alta volatilidade - espaçamento maior
            grid_spacing_min = max(base_spacing * 1.0, 2.0)
            grid_spacing_max = min(base_spacing * 2.5, 5.0)
            grid_width = 25.0  # ±25% do preço central
            
        else:
            # Condições normais
            grid_spacing_min = max(base_spacing * 0.75, 1.5)
            grid_spacing_max = min(base_spacing * 2.0, 4.0)
            grid_width = 20.0  # ±20% do preço central
            
        # Níveis de grid
        num_levels = 5
        grid_levels = []
        
        for i in range(-num_levels, num_levels + 1):
            if i == 0:
                continue  # Pular o nível central
                
            level_spacing = grid_spacing_min + (abs(i) - 1) * (grid_spacing_max - grid_spacing_min) / (num_levels - 1)
            level_price = current_price * (1 + (i * level_spacing / 100))
            
            grid_levels.append({
                "level": i,
                "price": level_price,
                "spacing_percent": level_spacing,
                "side": "sell" if i > 0 else "buy"
            })
            
        return {
            "center_price": current_price,
            "grid_spacing_min": grid_spacing_min,
            "grid_spacing_max": grid_spacing_max,
            "grid_width": grid_width,
            "levels": grid_levels,
            "market_condition": market_condition.trend_direction,
            "volatility": market_condition.volatility,
            "recommended_position_size": min(1000.0, current_price * 0.01),  # 1% do preço ou $1000
            "stop_loss_distance": atr_value * 2.0  # 2x ATR para stop loss
        }