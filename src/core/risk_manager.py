"""
src/core/risk_manager.py
Risk Management Engine for CryptoSDCA-AI

Implements comprehensive risk management:
- Position sizing based on portfolio risk
- Stop-loss and take-profit management
- Maximum drawdown protection
- Equity guard and portfolio limits
- Emergency stop mechanisms
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from loguru import logger

from src.config import get_settings
from src.database import get_db_session
from src.models.models import SystemSettings, TradeHistory


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Métricas de risco do portfolio"""
    total_exposure_usd: float
    max_drawdown_percent: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    win_rate: float
    profit_factor: float
    risk_level: RiskLevel
    recommendations: List[str]


@dataclass
class PositionRisk:
    """Análise de risco de uma posição específica"""
    symbol: str
    size_usd: float
    risk_percent: float  # % do portfolio
    max_loss_usd: float
    recommended_stop_loss: float
    recommended_take_profit: float
    position_score: float  # 0-100


class RiskManager:
    """
    Gerenciador de risco principal
    Monitora e controla exposição ao risco em todas as operações
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.max_drawdown = self.settings.max_drawdown_percent
        self.daily_loss_limit = self.settings.daily_loss_limit
        self.max_position_size = self.settings.max_position_size_usd
        
        # Estado interno
        self.current_exposure = 0.0
        self.daily_pnl = 0.0
        self.emergency_stop_active = False
        self.last_risk_check = datetime.utcnow()
        
    async def initialize(self):
        """Inicializa o gerenciador de risco"""
        try:
            logger.info("Initializing Risk Manager...")
            
            # Carregar configurações de risco do banco
            await self._load_risk_settings()
            
            # Calcular exposição atual
            await self._calculate_current_exposure()
            
            # Calcular P&L do dia
            await self._calculate_daily_pnl()
            
            logger.info(f"Risk Manager initialized - Current exposure: ${self.current_exposure:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Risk Manager: {e}")
            raise
            
    async def close(self):
        """Fecha o gerenciador de risco"""
        logger.info("Risk Manager closed")
        
    async def validate_new_position(
        self, 
        symbol: str, 
        position_size_usd: float,
        current_price: float
    ) -> Tuple[bool, str, float]:
        """
        Valida se uma nova posição pode ser aberta
        
        Returns:
            Tuple[bool, str, float]: (aprovado, motivo, tamanho_ajustado)
        """
        
        # Verificar parada de emergência
        if self.emergency_stop_active:
            return False, "Emergency stop is active", 0.0
            
        # Verificar limite de perda diária
        if self.daily_pnl <= -self.daily_loss_limit:
            return False, f"Daily loss limit reached: ${self.daily_pnl:.2f}", 0.0
            
        # Verificar exposição máxima
        new_exposure = self.current_exposure + position_size_usd
        max_total_exposure = self.max_position_size * 10  # Máximo 10 posições
        
        if new_exposure > max_total_exposure:
            return False, f"Maximum exposure exceeded: ${new_exposure:.2f} > ${max_total_exposure:.2f}", 0.0
            
        # Verificar tamanho individual da posição
        if position_size_usd > self.max_position_size:
            adjusted_size = self.max_position_size
            return True, f"Position size adjusted: ${position_size_usd:.2f} → ${adjusted_size:.2f}", adjusted_size
            
        # Verificar correlação com posições existentes
        correlation_risk = await self._check_correlation_risk(symbol)
        if correlation_risk > 0.8:
            adjusted_size = position_size_usd * 0.5  # Reduzir 50%
            return True, f"High correlation risk - size reduced by 50%", adjusted_size
            
        # Verificar volatilidade do par
        volatility_adjustment = await self._get_volatility_adjustment(symbol)
        adjusted_size = position_size_usd * volatility_adjustment
        
        return True, "Position approved", adjusted_size
        
    async def calculate_stop_loss_take_profit(
        self, 
        symbol: str, 
        entry_price: float,
        position_size: float
    ) -> Tuple[float, float]:
        """
        Calcula níveis otimizados de stop-loss e take-profit
        
        Returns:
            Tuple[float, float]: (stop_loss_price, take_profit_price)
        """
        
        # Configurações padrão
        default_stop_loss_pct = abs(self.settings.default_stop_loss)
        default_take_profit_pct = self.settings.default_profit_target
        
        # Ajustar baseado na volatilidade
        volatility = await self._get_symbol_volatility(symbol)
        
        if volatility > 0.05:  # Alta volatilidade (>5%)
            stop_loss_pct = default_stop_loss_pct * 1.5
            take_profit_pct = default_take_profit_pct * 2.0
        elif volatility < 0.02:  # Baixa volatilidade (<2%)
            stop_loss_pct = default_stop_loss_pct * 0.7
            take_profit_pct = default_take_profit_pct * 0.8
        else:
            stop_loss_pct = default_stop_loss_pct
            take_profit_pct = default_take_profit_pct
            
        # Calcular preços
        stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        take_profit_price = entry_price * (1 + take_profit_pct / 100)
        
        return stop_loss_price, take_profit_price
        
    async def check_emergency_conditions(self) -> bool:
        """
        Verifica se condições de emergência foram atingidas
        
        Returns:
            bool: True se parada de emergência deve ser ativada
        """
        
        # Verificar drawdown máximo
        current_drawdown = await self._calculate_current_drawdown()
        if current_drawdown >= self.max_drawdown:
            logger.critical(f"Maximum drawdown reached: {current_drawdown:.2f}%")
            return True
            
        # Verificar perda diária extrema
        if self.daily_pnl <= -(self.daily_loss_limit * 2):
            logger.critical(f"Extreme daily loss: ${self.daily_pnl:.2f}")
            return True
            
        # Verificar múltiplas perdas consecutivas
        consecutive_losses = await self._count_consecutive_losses()
        if consecutive_losses >= 10:
            logger.critical(f"Too many consecutive losses: {consecutive_losses}")
            return True
            
        return False
        
    async def activate_emergency_stop(self, reason: str):
        """Ativa parada de emergência"""
        
        self.emergency_stop_active = True
        
        # Salvar evento no banco
        db = get_db_session()
        try:
            emergency_setting = SystemSettings(
                key="emergency_stop_activated",
                value=datetime.utcnow().isoformat(),
                value_type="string",
                description=f"Emergency stop reason: {reason}",
                category="risk_management"
            )
            db.add(emergency_setting)
            db.commit()
        finally:
            db.close()
            
        logger.critical(f"🚨 EMERGENCY STOP ACTIVATED: {reason}")
        
    async def deactivate_emergency_stop(self, reason: str):
        """Desativa parada de emergência"""
        
        self.emergency_stop_active = False
        
        logger.warning(f"Emergency stop deactivated: {reason}")
        
    def get_position_size_adjustment(self) -> float:
        """
        Retorna fator de ajuste para tamanho de posições baseado no risco atual
        
        Returns:
            float: Multiplicador (0.1 a 1.0)
        """
        
        # Fator base
        base_factor = 1.0
        
        # Ajustar baseado na performance recente
        if self.daily_pnl < -50:  # Perdendo mais de $50 hoje
            base_factor *= 0.7
        elif self.daily_pnl < -20:  # Perdendo mais de $20 hoje
            base_factor *= 0.8
        elif self.daily_pnl > 50:  # Ganhando mais de $50 hoje
            base_factor *= 1.2
            
        # Ajustar baseado na exposição atual
        exposure_ratio = self.current_exposure / (self.max_position_size * 5)  # Máximo 5 posições como referência
        if exposure_ratio > 0.8:
            base_factor *= 0.6
        elif exposure_ratio > 0.5:
            base_factor *= 0.8
            
        # Limitar entre 0.1 e 1.5
        return max(0.1, min(1.5, base_factor))
        
    async def get_risk_metrics(self) -> RiskMetrics:
        """Retorna métricas completas de risco"""
        
        # Calcular P&L periods
        daily_pnl = await self._calculate_period_pnl(1)
        weekly_pnl = await self._calculate_period_pnl(7)
        monthly_pnl = await self._calculate_period_pnl(30)
        
        # Calcular métricas de performance
        win_rate = await self._calculate_win_rate()
        profit_factor = await self._calculate_profit_factor()
        current_drawdown = await self._calculate_current_drawdown()
        
        # Determinar nível de risco
        risk_level = self._determine_risk_level(current_drawdown, daily_pnl)
        
        # Gerar recomendações
        recommendations = self._generate_risk_recommendations(
            current_drawdown, daily_pnl, win_rate
        )
        
        return RiskMetrics(
            total_exposure_usd=self.current_exposure,
            max_drawdown_percent=current_drawdown,
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
            monthly_pnl=monthly_pnl,
            win_rate=win_rate,
            profit_factor=profit_factor,
            risk_level=risk_level,
            recommendations=recommendations
        )
        
    async def analyze_position_risk(
        self, 
        symbol: str, 
        size_usd: float, 
        entry_price: float
    ) -> PositionRisk:
        """Analisa risco específico de uma posição"""
        
        # Calcular porcentagem do portfolio
        total_portfolio_value = self.current_exposure + size_usd
        risk_percent = (size_usd / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
        
        # Calcular stop-loss recomendado
        stop_loss, take_profit = await self.calculate_stop_loss_take_profit(
            symbol, entry_price, size_usd
        )
        
        # Calcular perda máxima
        max_loss_usd = size_usd * (abs(self.settings.default_stop_loss) / 100)
        
        # Calcular score da posição
        position_score = self._calculate_position_score(
            risk_percent, max_loss_usd, symbol
        )
        
        return PositionRisk(
            symbol=symbol,
            size_usd=size_usd,
            risk_percent=risk_percent,
            max_loss_usd=max_loss_usd,
            recommended_stop_loss=stop_loss,
            recommended_take_profit=take_profit,
            position_score=position_score
        )
        
    def _determine_risk_level(self, drawdown: float, daily_pnl: float) -> RiskLevel:
        """Determina nível de risco atual"""
        
        if drawdown >= self.max_drawdown * 0.8 or daily_pnl <= -self.daily_loss_limit * 0.8:
            return RiskLevel.CRITICAL
        elif drawdown >= self.max_drawdown * 0.5 or daily_pnl <= -self.daily_loss_limit * 0.5:
            return RiskLevel.HIGH
        elif drawdown >= self.max_drawdown * 0.25 or daily_pnl <= -self.daily_loss_limit * 0.25:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
            
    def _generate_risk_recommendations(
        self, 
        drawdown: float, 
        daily_pnl: float, 
        win_rate: float
    ) -> List[str]:
        """Gera recomendações baseadas no risco atual"""
        
        recommendations = []
        
        if drawdown > self.max_drawdown * 0.5:
            recommendations.append("Consider reducing position sizes")
            recommendations.append("Review and adjust stop-loss levels")
            
        if daily_pnl < -self.daily_loss_limit * 0.5:
            recommendations.append("Daily loss approaching limit - consider stopping trading")
            
        if win_rate < 40:
            recommendations.append("Low win rate - review trading strategy")
            
        if self.current_exposure > self.max_position_size * 8:
            recommendations.append("High exposure - consider closing some positions")
            
        if not recommendations:
            recommendations.append("Risk levels are within acceptable parameters")
            
        return recommendations
        
    def _calculate_position_score(
        self, 
        risk_percent: float, 
        max_loss_usd: float, 
        symbol: str
    ) -> float:
        """Calcula score de 0-100 para uma posição"""
        
        score = 100.0
        
        # Penalizar alta concentração
        if risk_percent > 20:
            score -= 30
        elif risk_percent > 10:
            score -= 15
            
        # Penalizar alta perda potencial
        if max_loss_usd > self.daily_loss_limit:
            score -= 25
        elif max_loss_usd > self.daily_loss_limit * 0.5:
            score -= 10
            
        # Bonificar diversificação
        if risk_percent < 5:
            score += 10
            
        return max(0, min(100, score))
        
    async def _load_risk_settings(self):
        """Carrega configurações de risco do banco"""
        
        db = get_db_session()
        try:
            # Carregar configurações customizadas
            settings = db.query(SystemSettings).filter_by(category="risk_management").all()
            
            for setting in settings:
                if setting.key == "max_drawdown_percent" and setting.value:
                    self.max_drawdown = float(setting.value)
                elif setting.key == "daily_loss_limit" and setting.value:
                    self.daily_loss_limit = float(setting.value)
                elif setting.key == "max_position_size_usd" and setting.value:
                    self.max_position_size = float(setting.value)
                    
        finally:
            db.close()
            
    async def _calculate_current_exposure(self):
        """Calcula exposição atual do portfolio"""
        # Implementar cálculo baseado em posições ativas
        self.current_exposure = 0.0  # Placeholder
        
    async def _calculate_daily_pnl(self):
        """Calcula P&L do dia atual"""
        # Implementar cálculo baseado em trades do dia
        self.daily_pnl = 0.0  # Placeholder
        
    async def _calculate_period_pnl(self, days: int) -> float:
        """Calcula P&L para um período específico"""
        
        db = get_db_session()
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            trades = db.query(TradeHistory).filter(
                TradeHistory.executed_at >= start_date
            ).all()
            
            total_pnl = sum(trade.profit_loss for trade in trades if trade.profit_loss)
            return total_pnl
            
        except Exception as e:
            logger.error(f"Error calculating {days}-day P&L: {e}")
            return 0.0
        finally:
            db.close()
            
    async def _calculate_win_rate(self) -> float:
        """Calcula taxa de vitória dos últimos 30 dias"""
        
        db = get_db_session()
        try:
            start_date = datetime.utcnow() - timedelta(days=30)
            
            trades = db.query(TradeHistory).filter(
                TradeHistory.executed_at >= start_date
            ).all()
            
            if not trades:
                return 0.0
                
            winning_trades = sum(1 for trade in trades if trade.profit_loss and trade.profit_loss > 0)
            return (winning_trades / len(trades)) * 100
            
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return 0.0
        finally:
            db.close()
            
    async def _calculate_profit_factor(self) -> float:
        """Calcula fator de lucro (lucros/perdas)"""
        
        db = get_db_session()
        try:
            start_date = datetime.utcnow() - timedelta(days=30)
            
            trades = db.query(TradeHistory).filter(
                TradeHistory.executed_at >= start_date
            ).all()
            
            profits = sum(trade.profit_loss for trade in trades if trade.profit_loss and trade.profit_loss > 0)
            losses = abs(sum(trade.profit_loss for trade in trades if trade.profit_loss and trade.profit_loss < 0))
            
            return profits / losses if losses > 0 else float('inf')
            
        except Exception as e:
            logger.error(f"Error calculating profit factor: {e}")
            return 0.0
        finally:
            db.close()
            
    async def _calculate_current_drawdown(self) -> float:
        """Calcula drawdown atual"""
        # Implementar cálculo de drawdown
        return 0.0  # Placeholder
        
    async def _count_consecutive_losses(self) -> int:
        """Conta perdas consecutivas recentes"""
        
        db = get_db_session()
        try:
            recent_trades = db.query(TradeHistory).order_by(
                TradeHistory.executed_at.desc()
            ).limit(20).all()
            
            consecutive_losses = 0
            for trade in recent_trades:
                if trade.profit_loss and trade.profit_loss < 0:
                    consecutive_losses += 1
                else:
                    break
                    
            return consecutive_losses
            
        except Exception as e:
            logger.error(f"Error counting consecutive losses: {e}")
            return 0
        finally:
            db.close()
            
    async def _check_correlation_risk(self, symbol: str) -> float:
        """Verifica risco de correlação com posições existentes"""
        # Implementar análise de correlação
        return 0.3  # Placeholder - baixa correlação
        
    async def _get_volatility_adjustment(self, symbol: str) -> float:
        """Retorna ajuste baseado na volatilidade do símbolo"""
        # Implementar análise de volatilidade
        return 1.0  # Placeholder - sem ajuste
        
    async def _get_symbol_volatility(self, symbol: str) -> float:
        """Obtém volatilidade histórica do símbolo"""
        # Implementar cálculo de volatilidade
        return 0.03  # Placeholder - 3% de volatilidade