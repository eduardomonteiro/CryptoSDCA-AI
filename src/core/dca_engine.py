"""
src/core/dca_engine.py
DCA (Dollar Cost Averaging) Engine for CryptoSDCA-AI

Implements intelligent multi-layer DCA strategy:
- Dynamic grid trading based on market conditions
- AI validation for each trade decision
- Risk management and position sizing
- Automatic recalibration based on volatility
- Integration with technical indicators and sentiment analysis
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

from loguru import logger
import ccxt.async_support as ccxt

from src.config import get_settings
from src.database import get_db_session
from src.models.models import TradingPair, Order, OrderSide, OrderType, OrderStatus, TradeHistory
from src.core.indicators import TechnicalIndicators, MarketCondition
from src.core.ai_validator import AIValidator
from src.core.sentiment_analyzer import SentimentAnalyzer
from src.core.risk_manager import RiskManager
from src.core.exchange_manager import ExchangeManager


class GridLevel(Enum):
    BUY = "buy"
    SELL = "sell"
    TAKE_PROFIT = "take_profit"


@dataclass
class GridOrder:
    """Ordem individual do grid"""
    level: int
    price: float
    quantity: float
    side: GridLevel
    executed: bool = False
    order_id: Optional[str] = None
    parent_order_id: Optional[int] = None


@dataclass
class DCAPosition:
    """Posição DCA ativa"""
    symbol: str
    exchange: str
    entry_price: float
    total_quantity: float
    total_cost: float
    average_price: float
    current_profit_loss: float
    profit_percentage: float
    grid_orders: List[GridOrder]
    max_duration_hours: int
    created_at: datetime
    target_profit_percent: float
    stop_loss_percent: float
    
    
class DCAEngine:
    """
    Engine principal de DCA inteligente
    Gerencia múltiplas posições simultaneamente com grid dinâmico
    """
    
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
        
        # Estado interno
        self.active_positions: Dict[str, DCAPosition] = {}
        self.is_running = False
        self.last_recalibration = datetime.utcnow()
        
        # Configurações
        self.base_currencies = self.settings.get_base_currencies_list()  # DAI, USDC, USDT
        self.min_pairs_count = self.settings.min_pairs_count
        self.max_operation_duration = self.settings.max_operation_duration_hours
        
    async def initialize(self):
        """Inicializa o engine DCA"""
        try:
            logger.info("Initializing DCA Engine...")
            
            # Carregar posições ativas do banco de dados
            await self._load_active_positions()
            
            # Verificar pares de trading disponíveis
            await self._update_available_pairs()
            
            logger.info(f"DCA Engine initialized with {len(self.active_positions)} active positions")
            
        except Exception as e:
            logger.error(f"Failed to initialize DCA Engine: {e}")
            raise
            
    async def close(self):
        """Fecha o engine DCA"""
        self.is_running = False
        logger.info("DCA Engine closed")
        
    async def start_trading_loop(self):
        """Inicia o loop principal de trading"""
        
        if self.is_running:
            logger.warning("DCA Engine is already running")
            return
            
        self.is_running = True
        logger.info("Starting DCA trading loop...")
        
        while self.is_running:
            try:
                # Verificar se está em modo paper trading
                if self.settings.paper_trading:
                    logger.debug("Running in paper trading mode")
                
                # 1. Monitorar posições ativas
                await self._monitor_active_positions()
                
                # 2. Verificar oportunidades de novas posições
                await self._scan_new_opportunities()
                
                # 3. Rebalancear grid se necessário
                await self._rebalance_grids()
                
                # 4. Verificar condições de saída
                await self._check_exit_conditions()
                
                # Aguardar antes da próxima iteração
                await asyncio.sleep(30)  # 30 segundos entre verificações
                
            except Exception as e:
                logger.error(f"Error in DCA trading loop: {e}")
                await asyncio.sleep(60)  # Aguardar mais tempo em caso de erro
                
    async def _monitor_active_positions(self):
        """Monitora posições ativas e atualiza status"""
        
        for symbol, position in list(self.active_positions.items()):
            try:
                # Obter preço atual
                current_price = await self.exchange_manager.get_current_price(symbol, position.exchange)
                
                if current_price:
                    # Atualizar P&L da posição
                    self._update_position_pnl(position, current_price)
                    
                    # Verificar ordens do grid
                    await self._check_grid_orders(position, current_price)
                    
                    # Verificar condições de take profit / stop loss
                    await self._check_profit_loss_conditions(position, current_price)
                    
            except Exception as e:
                logger.error(f"Error monitoring position {symbol}: {e}")
                
    async def _scan_new_opportunities(self):
        """Escaneia o mercado por novas oportunidades de DCA"""
        
        # Verificar se já temos o número mínimo de posições
        if len(self.active_positions) >= self.min_pairs_count:
            return
            
        try:
            # Obter pares disponíveis
            available_pairs = await self._get_available_pairs()
            
            for pair_info in available_pairs:
                symbol = pair_info["symbol"]
                exchange = pair_info["exchange"]
                
                # Pular se já temos posição neste par
                if symbol in self.active_positions:
                    continue
                    
                # Analisar condições de mercado
                market_data = await self._get_market_data(symbol, exchange)
                if not market_data:
                    continue
                    
                # Obter análise de sentimento
                sentiment_data = await self.sentiment_analyzer.get_current_sentiment()
                
                # Analisar indicadores técnicos
                market_condition = self.indicators.analyze_market_conditions(market_data["ohlcv"])
                
                # Verificar se é um bom momento para entrar
                if await self._should_enter_position(symbol, market_condition, sentiment_data):
                    # Validar com IA
                    quantity = self._calculate_position_size(symbol, market_data["current_price"])
                    
                    ai_approved, ai_results = await self.ai_validator.validate_trade_decision(
                        symbol, "BUY", quantity, market_data, sentiment_data
                    )
                    
                    if ai_approved:
                        await self._create_new_position(symbol, exchange, market_data, market_condition)
                        
        except Exception as e:
            logger.error(f"Error scanning new opportunities: {e}")
            
    async def _should_enter_position(
        self, 
        symbol: str, 
        market_condition: MarketCondition,
        sentiment_data: Dict[str, Any]
    ) -> bool:
        """Determina se deve entrar em uma nova posição"""
        
        # Verificar condições básicas
        if market_condition.overall_signal not in ["BUY", "HOLD"]:
            return False
            
        # Verificar sentimento geral
        fear_greed = sentiment_data.get("fear_greed_index", 50)
        if fear_greed > 80:  # Extrema ganância
            return False
            
        # Verificar volatilidade (preferir média/alta para DCA)
        if market_condition.volatility == "LOW":
            return False
            
        # Verificar força da tendência
        if market_condition.trend_strength < 0.3:
            return False
            
        return True
        
    async def _create_new_position(
        self,
        symbol: str,
        exchange: str,
        market_data: Dict[str, Any],
        market_condition: MarketCondition
    ):
        """Cria uma nova posição DCA"""
        
        try:
            current_price = market_data["current_price"]
            
            # Calcular tamanho da posição
            position_size = self._calculate_position_size(symbol, current_price)
            
            # Gerar grid de ordens
            grid_config = self.indicators.get_dynamic_grid_config(market_condition)
            grid_orders = self._generate_grid_orders(current_price, position_size, grid_config)
            
            # Executar primeira ordem de compra
            first_order = await self._execute_grid_order(symbol, exchange, grid_orders[0])
            
            if first_order:
                # Criar posição
                position = DCAPosition(
                    symbol=symbol,
                    exchange=exchange,
                    entry_price=current_price,
                    total_quantity=position_size,
                    total_cost=current_price * position_size,
                    average_price=current_price,
                    current_profit_loss=0.0,
                    profit_percentage=0.0,
                    grid_orders=grid_orders,
                    max_duration_hours=self.max_operation_duration,
                    created_at=datetime.utcnow(),
                    target_profit_percent=self.settings.default_profit_target,
                    stop_loss_percent=self.settings.default_stop_loss
                )
                
                self.active_positions[symbol] = position
                
                # Salvar no banco de dados
                await self._save_position_to_db(position, first_order)
                
                logger.info(f"Created new DCA position for {symbol} at ${current_price:.4f}")
                
        except Exception as e:
            logger.error(f"Error creating new position for {symbol}: {e}")
            
    def _generate_grid_orders(
        self, 
        entry_price: float, 
        total_size: float, 
        grid_config: Dict[str, float]
    ) -> List[GridOrder]:
        """Gera ordens do grid baseado na configuração dinâmica"""
        
        grid_orders = []
        
        # Parâmetros do grid
        spacing_min = grid_config["spacing_min"] / 100  # Converter % para decimal
        spacing_max = grid_config["spacing_max"] / 100
        grid_levels = 5  # Número de níveis do grid
        
        # Calcular espaçamento médio
        avg_spacing = (spacing_min + spacing_max) / 2
        
        # Quantidade por ordem (dividir igualmente)
        quantity_per_order = total_size / grid_levels
        
        # Gerar ordens de compra (abaixo do preço atual)
        for i in range(1, grid_levels + 1):
            buy_price = entry_price * (1 - (avg_spacing * i))
            
            grid_orders.append(GridOrder(
                level=-i,  # Níveis negativos para compra
                price=buy_price,
                quantity=quantity_per_order,
                side=GridLevel.BUY
            ))
            
        # Gerar ordens de venda (acima do preço atual)
        for i in range(1, grid_levels + 1):
            sell_price = entry_price * (1 + (avg_spacing * i))
            
            grid_orders.append(GridOrder(
                level=i,  # Níveis positivos para venda
                price=sell_price,
                quantity=quantity_per_order,
                side=GridLevel.SELL
            ))
            
        return grid_orders
        
    async def _execute_grid_order(
        self, 
        symbol: str, 
        exchange: str, 
        grid_order: GridOrder
    ) -> Optional[Dict[str, Any]]:
        """Executa uma ordem do grid"""
        
        try:
            if self.settings.paper_trading:
                # Simulação em paper trading
                order_id = f"paper_{datetime.utcnow().timestamp()}"
                grid_order.order_id = order_id
                grid_order.executed = True
                
                logger.info(f"Paper trading: {grid_order.side.value} {grid_order.quantity:.6f} {symbol} at ${grid_order.price:.4f}")
                
                return {
                    "id": order_id,
                    "symbol": symbol,
                    "side": grid_order.side.value,
                    "amount": grid_order.quantity,
                    "price": grid_order.price,
                    "status": "filled"
                }
            else:
                # Execução real
                order = await self.exchange_manager.place_order(
                    symbol=symbol,
                    side=grid_order.side.value,
                    amount=grid_order.quantity,
                    price=grid_order.price,
                    order_type="limit"
                )
                
                if order:
                    grid_order.order_id = order["id"]
                    return order
                    
        except Exception as e:
            logger.error(f"Error executing grid order: {e}")
            
        return None
        
    async def _check_grid_orders(self, position: DCAPosition, current_price: float):
        """Verifica e executa ordens do grid baseado no preço atual"""
        
        for grid_order in position.grid_orders:
            if grid_order.executed:
                continue
                
            # Verificar se a ordem deve ser executada
            should_execute = False
            
            if grid_order.side == GridLevel.BUY and current_price <= grid_order.price:
                should_execute = True
            elif grid_order.side == GridLevel.SELL and current_price >= grid_order.price:
                should_execute = True
                
            if should_execute:
                executed_order = await self._execute_grid_order(
                    position.symbol, position.exchange, grid_order
                )
                
                if executed_order:
                    # Atualizar posição
                    if grid_order.side == GridLevel.BUY:
                        self._update_position_after_buy(position, grid_order)
                    else:
                        self._update_position_after_sell(position, grid_order)
                        
    def _update_position_after_buy(self, position: DCAPosition, grid_order: GridOrder):
        """Atualiza posição após compra adicional"""
        
        # Recalcular preço médio
        total_cost = position.total_cost + (grid_order.price * grid_order.quantity)
        total_quantity = position.total_quantity + grid_order.quantity
        
        position.average_price = total_cost / total_quantity
        position.total_cost = total_cost
        position.total_quantity = total_quantity
        
        logger.info(f"Added to position {position.symbol}: {grid_order.quantity:.6f} at ${grid_order.price:.4f}")
        
    def _update_position_after_sell(self, position: DCAPosition, grid_order: GridOrder):
        """Atualiza posição após venda parcial"""
        
        position.total_quantity -= grid_order.quantity
        # Manter total_cost para cálculo correto do P&L
        
        logger.info(f"Sold from position {position.symbol}: {grid_order.quantity:.6f} at ${grid_order.price:.4f}")
        
    def _update_position_pnl(self, position: DCAPosition, current_price: float):
        """Atualiza P&L da posição"""
        
        current_value = position.total_quantity * current_price
        position.current_profit_loss = current_value - position.total_cost
        position.profit_percentage = (position.current_profit_loss / position.total_cost) * 100
        
    async def _check_profit_loss_conditions(self, position: DCAPosition, current_price: float):
        """Verifica condições de take profit e stop loss"""
        
        # Verificar take profit
        if position.profit_percentage >= position.target_profit_percent:
            await self._close_position(position, "TAKE_PROFIT", current_price)
            return
            
        # Verificar stop loss
        if position.profit_percentage <= position.stop_loss_percent:
            await self._close_position(position, "STOP_LOSS", current_price)
            return
            
        # Verificar tempo máximo
        duration = datetime.utcnow() - position.created_at
        if duration.total_seconds() / 3600 >= position.max_duration_hours:
            await self._close_position(position, "MAX_TIME", current_price)
            return
            
    async def _close_position(self, position: DCAPosition, reason: str, current_price: float):
        """Fecha uma posição completamente"""
        
        try:
            # Cancelar ordens pendentes
            await self._cancel_pending_orders(position)
            
            # Vender toda a quantidade restante
            if position.total_quantity > 0:
                sell_order = await self.exchange_manager.place_order(
                    symbol=position.symbol,
                    side="sell",
                    amount=position.total_quantity,
                    price=current_price,
                    order_type="market"
                )
                
            # Salvar histórico
            await self._save_trade_history(position, reason, current_price)
            
            # Remover da lista ativa
            del self.active_positions[position.symbol]
            
            logger.info(f"Closed position {position.symbol}: {reason}, P&L: {position.profit_percentage:.2f}%")
            
        except Exception as e:
            logger.error(f"Error closing position {position.symbol}: {e}")
            
    async def _rebalance_grids(self):
        """Rebalanceia grids baseado em mudanças nas condições de mercado"""
        
        # Verificar se já passou tempo suficiente desde a última recalibração
        if datetime.utcnow() - self.last_recalibration < timedelta(hours=4):
            return
            
        for position in self.active_positions.values():
            try:
                # Obter dados atuais do mercado
                market_data = await self._get_market_data(position.symbol, position.exchange)
                if not market_data:
                    continue
                    
                # Analisar condições atuais
                market_condition = self.indicators.analyze_market_conditions(market_data["ohlcv"])
                
                # Gerar nova configuração de grid
                new_grid_config = self.indicators.get_dynamic_grid_config(market_condition)
                
                # Verificar se há mudanças significativas
                if self._should_recalibrate_grid(position, new_grid_config):
                    await self._recalibrate_position_grid(position, new_grid_config, market_data["current_price"])
                    
            except Exception as e:
                logger.error(f"Error rebalancing grid for {position.symbol}: {e}")
                
        self.last_recalibration = datetime.utcnow()
        
    def _calculate_position_size(self, symbol: str, current_price: float) -> float:
        """Calcula tamanho da posição baseado na configuração de risco"""
        
        # Usar 1% do saldo disponível por padrão
        max_position_value = self.settings.max_position_size_usd
        
        # Calcular quantidade baseada no preço atual
        quantity = max_position_value / current_price
        
        # Aplicar ajustes de risco se necessário
        risk_adjustment = self.risk_manager.get_position_size_adjustment()
        quantity *= risk_adjustment
        
        return quantity
        
    async def _get_market_data(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """Obtém dados de mercado para análise"""
        
        try:
            # Obter dados OHLCV
            ohlcv = await self.exchange_manager.get_ohlcv(symbol, "1h", 200)
            current_price = await self.exchange_manager.get_current_price(symbol, exchange)
            
            if not ohlcv or not current_price:
                return None
                
            return {
                "current_price": current_price,
                "ohlcv": ohlcv,
                "24h_change": self._calculate_24h_change(ohlcv),
                "volume_24h": sum(candle["volume"] for candle in ohlcv[-24:]),
                "volatility": self._calculate_volatility(ohlcv)
            }
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
            
    def _calculate_24h_change(self, ohlcv: List[Dict]) -> float:
        """Calcula mudança de preço em 24h"""
        if len(ohlcv) < 24:
            return 0.0
            
        current_price = ohlcv[-1]["close"]
        price_24h_ago = ohlcv[-24]["close"]
        
        return ((current_price - price_24h_ago) / price_24h_ago) * 100
        
    def _calculate_volatility(self, ohlcv: List[Dict]) -> float:
        """Calcula volatilidade baseada nos últimos dados"""
        if len(ohlcv) < 20:
            return 0.0
            
        closes = [candle["close"] for candle in ohlcv[-20:]]
        mean_price = sum(closes) / len(closes)
        variance = sum((price - mean_price) ** 2 for price in closes) / len(closes)
        
        return (variance ** 0.5) / mean_price
        
    async def _load_active_positions(self):
        """Carrega posições ativas do banco de dados"""
        # Implementar carregamento do banco
        pass
        
    async def _update_available_pairs(self):
        """Atualiza lista de pares disponíveis"""
        # Implementar atualização de pares
        pass
        
    async def _get_available_pairs(self) -> List[Dict[str, str]]:
        """Retorna pares disponíveis para trading"""
        # Implementar busca de pares
        return [
            {"symbol": "BTC/USDT", "exchange": "binance"},
            {"symbol": "ETH/USDT", "exchange": "binance"},
        ]
        
    async def get_status(self) -> Dict[str, Any]:
        """Retorna status atual do DCA Engine"""
        
        total_positions = len(self.active_positions)
        total_pnl = sum(pos.current_profit_loss for pos in self.active_positions.values())
        avg_profit_pct = sum(pos.profit_percentage for pos in self.active_positions.values()) / total_positions if total_positions > 0 else 0
        
        return {
            "is_running": self.is_running,
            "active_positions": total_positions,
            "total_pnl_usd": round(total_pnl, 2),
            "average_profit_percent": round(avg_profit_pct, 2),
            "last_recalibration": self.last_recalibration.isoformat(),
            "paper_trading": self.settings.paper_trading,
            "positions": [
                {
                    "symbol": pos.symbol,
                    "profit_percentage": round(pos.profit_percentage, 2),
                    "current_pnl": round(pos.current_profit_loss, 2),
                    "duration_hours": (datetime.utcnow() - pos.created_at).total_seconds() / 3600
                }
                for pos in self.active_positions.values()
            ]
        }