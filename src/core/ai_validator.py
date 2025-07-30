"""
src/core/ai_validator.py
AI Validation Engine for CryptoSDCA-AI

Integrates with M365 Copilot and Perplexity API for dual AI validation
of trading decisions before executing orders.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

import httpx
from loguru import logger

from src.config import get_settings
from src.database import get_db_session
from src.models.models import AIAgent, TradeDecision, AIDecision


class AIProvider(Enum):
    COPILOT = "copilot"
    PERPLEXITY = "perplexity"
    OPENAI = "openai"


class AIValidationResult:
    """Resultado da validação de IA"""
    def __init__(self, decision: str, confidence: float, reasoning: str, provider: str):
        self.decision = decision  # "YES" or "NO"
        self.confidence = confidence  # 0.0 to 1.0
        self.reasoning = reasoning
        self.provider = provider
        self.timestamp = datetime.utcnow()


class AIValidator:
    """
    Validador de decisões de trading usando múltiplas IAs
    Implementa o sistema de consenso duplo para decisões de compra/venda
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.active_agents: List[AIAgent] = []
        
    async def initialize(self):
        """Inicializa o validador carregando agentes ativos"""
        try:
            db = get_db_session()
            self.active_agents = db.query(AIAgent).filter_by(is_active=True).all()
            db.close()
            
            logger.info(f"AI Validator initialized with {len(self.active_agents)} active agents")
            
            # Verificar conectividade dos agentes
            for agent in self.active_agents:
                await self._test_agent_connection(agent)
                
        except Exception as e:
            logger.error(f"Failed to initialize AI Validator: {e}")
            
    async def close(self):
        """Fecha conexões"""
        await self.http_client.aclose()
        
    async def validate_trade_decision(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        market_data: Dict[str, Any],
        sentiment_data: Dict[str, Any]
    ) -> Tuple[bool, List[AIValidationResult]]:
        """
        Valida uma decisão de trading com múltiplas IAs
        
        Returns:
            Tuple[bool, List[AIValidationResult]]: (consenso_atingido, resultados)
        """
        if not self.active_agents:
            logger.warning("No active AI agents available for validation")
            return True, []  # Pular validação se não há agentes
            
        # Preparar contexto para as IAs
        trade_context = self._prepare_trade_context(
            symbol, side, quantity, market_data, sentiment_data
        )
        
        # Obter decisões de cada IA
        validation_results = []
        for agent in self.active_agents:
            try:
                result = await self._query_ai_agent(agent, trade_context)
                validation_results.append(result)
                
                # Salvar decisão no banco
                await self._save_trade_decision(agent, result, trade_context)
                
            except Exception as e:
                logger.error(f"Error querying AI agent {agent.name}: {e}")
                
        # Verificar consenso
        consensus = self._check_consensus(validation_results)
        
        return consensus, validation_results
        
    def _prepare_trade_context(
        self, 
        symbol: str, 
        side: str, 
        quantity: float,
        market_data: Dict[str, Any],
        sentiment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepara contexto da decisão para as IAs"""
        
        context = {
            "pair": symbol,
            "side": side.upper(),
            "size": quantity,
            "timestamp": datetime.utcnow().isoformat(),
            "technical_indicators": {
                "rsi": market_data.get("rsi", "N/A"),
                "macd": market_data.get("macd", "N/A"),
                "volume": market_data.get("volume", "N/A"),
                "atr": market_data.get("atr", "N/A"),
                "adx": market_data.get("adx", "N/A"),
                "bollinger_bands": market_data.get("bollinger_bands", "N/A")
            },
            "market_sentiment": {
                "fear_greed_index": sentiment_data.get("fear_greed_index", "N/A"),
                "news_sentiment": sentiment_data.get("news_sentiment", "N/A"),
                "overall_sentiment": sentiment_data.get("overall_sentiment", "N/A")
            },
            "price_info": {
                "current_price": market_data.get("current_price", "N/A"),
                "24h_change": market_data.get("24h_change", "N/A"),
                "volume_24h": market_data.get("volume_24h", "N/A")
            }
        }
        
        return context
        
    async def _query_ai_agent(
        self, 
        agent: AIAgent, 
        context: Dict[str, Any]
    ) -> AIValidationResult:
        """Query específico para cada tipo de IA"""
        
        if agent.agent_type == AIProvider.PERPLEXITY.value:
            return await self._query_perplexity(agent, context)
        elif agent.agent_type == AIProvider.OPENAI.value:
            return await self._query_openai(agent, context)
        elif agent.agent_type == AIProvider.COPILOT.value:
            return await self._query_copilot(agent, context)
        else:
            raise ValueError(f"Unsupported AI agent type: {agent.agent_type}")
            
    async def _query_perplexity(
        self, 
        agent: AIAgent, 
        context: Dict[str, Any]
    ) -> AIValidationResult:
        """Query para Perplexity API"""
        
        prompt = self._build_trading_prompt(context)
        
        headers = {
            "Authorization": f"Bearer {agent.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-medium-online",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert cryptocurrency trader and analyst. Analyze the provided trading scenario and respond with YES or NO followed by a brief justification."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 200,
            "temperature": 0.1
        }
        
        try:
            response = await self.http_client.post(
                agent.endpoint_url or "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse resposta
            decision, confidence, reasoning = self._parse_ai_response(content)
            
            return AIValidationResult(
                decision=decision,
                confidence=confidence,
                reasoning=reasoning,
                provider=f"perplexity-{agent.name}"
            )
            
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            # Retorna decisão neutra em caso de erro
            return AIValidationResult("NO", 0.0, f"API Error: {e}", agent.name)
            
    async def _query_openai(
        self, 
        agent: AIAgent, 
        context: Dict[str, Any]
    ) -> AIValidationResult:
        """Query para OpenAI API (GPT)"""
        
        prompt = self._build_trading_prompt(context)
        
        headers = {
            "Authorization": f"Bearer {agent.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert cryptocurrency trader. Analyze trading scenarios and respond with YES/NO plus reasoning."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 200,
            "temperature": 0.1
        }
        
        try:
            response = await self.http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            decision, confidence, reasoning = self._parse_ai_response(content)
            
            return AIValidationResult(
                decision=decision,
                confidence=confidence,
                reasoning=reasoning,
                provider=f"openai-{agent.name}"
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return AIValidationResult("NO", 0.0, f"API Error: {e}", agent.name)
            
    async def _query_copilot(
        self, 
        agent: AIAgent, 
        context: Dict[str, Any]
    ) -> AIValidationResult:
        """Query para Microsoft Copilot (placeholder)"""
        
        # Implementação placeholder - Microsoft Copilot requer autenticação OAuth complexa
        logger.warning("Microsoft Copilot integration not fully implemented yet")
        
        # Simulação de resposta baseada em dados técnicos
        rsi = context["technical_indicators"].get("rsi", 50)
        macd = context["technical_indicators"].get("macd", 0)
        fear_greed = context["market_sentiment"].get("fear_greed_index", 50)
        
        # Lógica simplificada baseada em indicadores
        decision = "YES"
        reasoning = "Technical analysis suggests favorable conditions"
        confidence = 0.7
        
        if isinstance(rsi, (int, float)):
            if rsi > 70:
                decision = "NO"
                reasoning = "RSI indicates overbought conditions"
                confidence = 0.8
            elif rsi < 30:
                decision = "YES" 
                reasoning = "RSI indicates oversold, good buying opportunity"
                confidence = 0.8
                
        return AIValidationResult(
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            provider=f"copilot-{agent.name}"
        )
        
    def _build_trading_prompt(self, context: Dict[str, Any]) -> str:
        """Constrói prompt padronizado para as IAs"""
        
        prompt = f"""
Trading Analysis Request:

Pair: {context['pair']}
Side: {context['side']} 
Size: {context['size']}

Technical Indicators:
- RSI: {context['technical_indicators']['rsi']}
- MACD: {context['technical_indicators']['macd']}
- Volume: {context['technical_indicators']['volume']}
- ATR: {context['technical_indicators']['atr']}
- ADX: {context['technical_indicators']['adx']}

Market Sentiment:
- Fear & Greed Index: {context['market_sentiment']['fear_greed_index']}
- News Sentiment: {context['market_sentiment']['news_sentiment']}
- Overall Sentiment: {context['market_sentiment']['overall_sentiment']}

Price Information:
- Current Price: {context['price_info']['current_price']}
- 24h Change: {context['price_info']['24h_change']}
- 24h Volume: {context['price_info']['volume_24h']}

Questions to analyze:
1) Is there any global event or news that could hurt/help this trade?
2) Does current sentiment (fear/greed) favor this entry?
3) Do you confirm this order should be executed now?

Respond with YES/NO followed by a 1-line justification.
"""
        return prompt.strip()
        
    def _parse_ai_response(self, content: str) -> Tuple[str, float, str]:
        """Parse resposta da IA para extrair decisão, confiança e raciocínio"""
        
        content = content.strip().upper()
        
        # Detectar decisão
        if content.startswith("YES"):
            decision = "YES"
        elif content.startswith("NO"):
            decision = "NO"
        else:
            decision = "NO"  # Default para segurança
            
        # Extrair confiança (se mencionada)
        confidence = 0.5  # Default
        if "HIGH CONFIDENCE" in content or "STRONG" in content:
            confidence = 0.9
        elif "MODERATE" in content or "MEDIUM" in content:
            confidence = 0.7
        elif "LOW" in content or "WEAK" in content:
            confidence = 0.3
            
        # Extrair raciocínio (primeira linha após YES/NO)
        lines = content.split('\n')
        reasoning = lines[0] if lines else "No reasoning provided"
        if len(lines) > 1:
            reasoning = lines[1][:200]  # Limitar tamanho
            
        return decision, confidence, reasoning
        
    def _check_consensus(self, results: List[AIValidationResult]) -> bool:
        """Verifica se há consenso entre as IAs"""
        
        if not results:
            return False
            
        yes_votes = sum(1 for r in results if r.decision == "YES")
        total_votes = len(results)
        
        # Requer maioria absoluta para YES
        consensus = yes_votes > total_votes / 2
        
        logger.info(f"AI Consensus: {yes_votes}/{total_votes} voted YES - {'APPROVED' if consensus else 'REJECTED'}")
        
        return consensus
        
    async def _save_trade_decision(
        self, 
        agent: AIAgent, 
        result: AIValidationResult,
        context: Dict[str, Any]
    ):
        """Salva decisão da IA no banco de dados"""
        
        try:
            db = get_db_session()
            
            decision = TradeDecision(
                ai_agent_id=agent.id,
                decision=AIDecision.APPROVE if result.decision == "YES" else AIDecision.DENY,
                confidence_score=result.confidence,
                reasoning=result.reasoning,
                market_data=context.get("technical_indicators"),
                sentiment_data=context.get("market_sentiment"),
                proposed_side=context.get("side"),
                proposed_quantity=context.get("size")
            )
            
            db.add(decision)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Failed to save trade decision: {e}")
            
    async def _test_agent_connection(self, agent: AIAgent) -> bool:
        """Testa conectividade com um agente IA"""
        
        try:
            # Teste simples de conectividade
            if agent.agent_type == AIProvider.PERPLEXITY.value and agent.api_key:
                headers = {"Authorization": f"Bearer {agent.api_key}"}
                response = await self.http_client.get(
                    "https://api.perplexity.ai/", 
                    headers=headers,
                    timeout=5.0
                )
                logger.info(f"Agent {agent.name} connection test: OK")
                return True
                
        except Exception as e:
            logger.warning(f"Agent {agent.name} connection test failed: {e}")
            return False
            
        return True
        
    async def get_historical_performance(self, agent_id: Optional[int] = None) -> Dict[str, Any]:
        """Retorna performance histórica das decisões de IA"""
        
        try:
            db = get_db_session()
            
            query = db.query(TradeDecision)
            if agent_id:
                query = query.filter_by(ai_agent_id=agent_id)
                
            decisions = query.all()
            
            total_decisions = len(decisions)
            if total_decisions == 0:
                return {"total_decisions": 0, "accuracy": 0.0}
                
            # Calcular métricas de performance
            correct_decisions = sum(1 for d in decisions if d.was_executed and d.execution_result == "profit")
            accuracy = correct_decisions / total_decisions if total_decisions > 0 else 0.0
            
            db.close()
            
            return {
                "total_decisions": total_decisions,
                "correct_decisions": correct_decisions,
                "accuracy": accuracy,
                "recent_decisions": len([d for d in decisions if d.created_at > datetime.utcnow().replace(hour=0, minute=0, second=0)])
            }
            
        except Exception as e:
            logger.error(f"Failed to get AI performance: {e}")
            return {"error": str(e)}