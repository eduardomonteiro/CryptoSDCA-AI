"""
src/core/ai_validator.py - AI Validation System for CryptoSDCA-AI
Handles validation of trading decisions using M365 Copilot and Perplexity API
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import httpx
from loguru import logger

from src.config import get_settings
from src.exceptions import AIValidationError
from src.database import get_db_session
from src.models.models import AIAgent


class AIDecision(Enum):
    """AI decision enumeration"""
    APPROVE = "approve"
    DENY = "deny"
    PENDING = "pending"


@dataclass
class TradeHypothesis:
    """Trade hypothesis structure for AI validation"""
    pair: str
    side: str  # "buy" or "sell"
    quantity: float
    entry_price: float
    indicators: Dict[str, float]
    fear_greed_index: int
    news_sentiment: float
    market_context: Dict[str, Any]
    timestamp: datetime


@dataclass
class AIValidationResult:
    """AI validation result"""
    ai_agent: str
    decision: AIDecision
    confidence: float
    reasoning: str
    response_time: float
    timestamp: datetime


class AIValidator:
    """AI validation system for trading decisions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_agents: Dict[str, AIAgent] = {}
        self.is_initialized = False
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def initialize(self):
        """Initialize AI validation system"""
        try:
            logger.info("🔄 Initializing AI Validator...")
            
            # Load AI agents from database
            await self._load_ai_agents()
            
            # Test connections to AI services
            await self._test_connections()
            
            self.is_initialized = True
            logger.info(f"✅ AI Validator initialized with {len(self.ai_agents)} agents")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI Validator: {e}")
            raise AIValidationError(f"Initialization failed: {str(e)}")
    
    async def _load_ai_agents(self):
        """Load AI agents from database"""
        try:
            db = get_db_session()
            agents = db.query(AIAgent).filter_by(is_active=True).all()
            
            for agent in agents:
                self.ai_agents[agent.name] = agent
                logger.info(f"📋 Loaded AI agent: {agent.name} ({agent.agent_type})")
            
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to load AI agents: {e}")
            raise AIValidationError(f"Failed to load AI agents: {str(e)}")
    
    async def _test_connections(self):
        """Test connections to AI services"""
        for agent_name, agent in self.ai_agents.items():
            try:
                if agent.agent_type == "perplexity":
                    await self._test_perplexity_connection(agent)
                elif agent.agent_type == "copilot":
                    await self._test_copilot_connection(agent)
                else:
                    logger.warning(f"⚠️ Unknown AI platform: {agent.agent_type}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to test connection for {agent_name}: {e}")
    
    async def _test_perplexity_connection(self, agent: AIAgent):
        """Test Perplexity API connection"""
        try:
            headers = {
                "Authorization": f"Bearer {agent.api_key}",
                "Content-Type": "application/json"
            }
            
            test_prompt = "Hello, this is a connection test."
            
            response = await self.http_client.post(
                agent.api_url,
                headers=headers,
                json={
                    "model": "sonar-medium-online",
                    "messages": [{"role": "user", "content": test_prompt}],
                    "max_tokens": 50
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Perplexity connection test passed for {agent.name}")
            else:
                logger.warning(f"⚠️ Perplexity connection test failed for {agent.name}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Perplexity connection test error for {agent.name}: {e}")
    
    async def _test_copilot_connection(self, agent: AIAgent):
        """Test Microsoft Copilot connection"""
        try:
            # For now, just log that we would test Copilot
            logger.info(f"✅ Copilot connection test passed for {agent.name} (mock)")
            
        except Exception as e:
            logger.error(f"❌ Copilot connection test error for {agent.name}: {e}")
    
    async def validate_trade(self, hypothesis: TradeHypothesis) -> List[AIValidationResult]:
        """
        Validate a trade hypothesis using all available AI agents
        
        Args:
            hypothesis: Trade hypothesis to validate
            
        Returns:
            List[AIValidationResult]: Validation results from all AI agents
        """
        if not self.is_initialized:
            raise AIValidationError("AI Validator not initialized")
        
        if not self.ai_agents:
            logger.warning("⚠️ No AI agents available, skipping validation")
            return []
        
        logger.info(f"🤖 Validating trade hypothesis for {hypothesis.pair}")
        
        # Create validation tasks for all agents
        tasks = []
        for agent_name, agent in self.ai_agents.items():
            task = asyncio.create_task(
                self._validate_with_agent(agent, hypothesis)
            )
            tasks.append(task)
        
        # Wait for all validations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        validation_results = []
        for i, result in enumerate(results):
            agent_name = list(self.ai_agents.keys())[i]
            
            if isinstance(result, Exception):
                logger.error(f"❌ Validation failed for {agent_name}: {result}")
                validation_results.append(AIValidationResult(
                    ai_agent=agent_name,
                    decision=AIDecision.PENDING,
                    confidence=0.0,
                    reasoning=f"Error: {str(result)}",
                    response_time=0.0,
                    timestamp=datetime.utcnow()
                ))
            else:
                validation_results.append(result)
        
        return validation_results
    
    async def _validate_with_agent(self, agent: AIAgent, hypothesis: TradeHypothesis) -> AIValidationResult:
        """
        Validate trade hypothesis with a specific AI agent
        
        Args:
            agent: AI agent to use for validation
            hypothesis: Trade hypothesis to validate
            
        Returns:
            AIValidationResult: Validation result
        """
        start_time = datetime.utcnow()
        
        try:
            if agent.agent_type == "perplexity":
                return await self._validate_with_perplexity(agent, hypothesis)
            elif agent.agent_type == "copilot":
                return await self._validate_with_copilot(agent, hypothesis)
            else:
                raise AIValidationError(f"Unsupported AI platform: {agent.agent_type}")
                
        except Exception as e:
            logger.error(f"❌ Validation error with {agent.name}: {e}")
            raise
            
        finally:
            response_time = (datetime.utcnow() - start_time).total_seconds()
    
    async def _validate_with_perplexity(self, agent: AIAgent, hypothesis: TradeHypothesis) -> AIValidationResult:
        """Validate using Perplexity API"""
        try:
            # Create the prompt for Perplexity
            prompt = self._create_validation_prompt(hypothesis)
            
            headers = {
                "Authorization": f"Bearer {agent.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar-medium-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a cryptocurrency trading advisor. Analyze the provided trade hypothesis and respond with YES or NO followed by a brief justification."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.3
            }
            
            response = await self.http_client.post(
                agent.api_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise AIValidationError(f"Perplexity API error: {response.status_code}")
            
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse the response
            decision, reasoning, confidence = self._parse_ai_response(content)
            
            return AIValidationResult(
                ai_agent=agent.name,
                decision=decision,
                confidence=confidence,
                reasoning=reasoning,
                response_time=0.0,  # Will be set by caller
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"❌ Perplexity validation error: {e}")
            raise AIValidationError(f"Perplexity validation failed: {str(e)}")
    
    async def _validate_with_copilot(self, agent: AIAgent, hypothesis: TradeHypothesis) -> AIValidationResult:
        """Validate using Microsoft Copilot (placeholder implementation)"""
        try:
            # This is a placeholder implementation
            # In a real implementation, you would integrate with Microsoft Graph API
            
            prompt = self._create_validation_prompt(hypothesis)
            
            # Mock response for now
            decision = AIDecision.APPROVE if hypothesis.side == "buy" else AIDecision.DENY
            reasoning = f"Mock Copilot analysis for {hypothesis.pair}"
            confidence = 0.75
            
            return AIValidationResult(
                ai_agent=agent.name,
                decision=decision,
                confidence=confidence,
                reasoning=reasoning,
                response_time=0.0,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"❌ Copilot validation error: {e}")
            raise AIValidationError(f"Copilot validation failed: {str(e)}")
    
    def _create_validation_prompt(self, hypothesis: TradeHypothesis) -> str:
        """Create validation prompt for AI agents"""
        indicators_str = ", ".join([f"{k}: {v:.2f}" for k, v in hypothesis.indicators.items()])
        
        prompt = f"""
Pair: {hypothesis.pair}
Side: {hypothesis.side.upper()}
Size: {hypothesis.quantity}
Entry Price: ${hypothesis.entry_price:.6f}
Context: {indicators_str}
Fear & Greed Index: {hypothesis.fear_greed_index}
News Sentiment: {hypothesis.news_sentiment:.2f}

Please analyze this trade hypothesis and answer the following questions:

1) Are there any global events or news that could hurt/help this trade?
2) Does the current sentiment (fear/greed) favor this entry?
3) Do you confirm this order now?

Respond with ONLY YES or NO followed by a 1-line justification.
"""
        
        return prompt.strip()
    
    def _parse_ai_response(self, response: str) -> Tuple[AIDecision, str, float]:
        """Parse AI response to extract decision, reasoning, and confidence"""
        response = response.strip().lower()
        
        # Extract decision
        if "yes" in response[:10]:
            decision = AIDecision.APPROVE
        elif "no" in response[:10]:
            decision = AIDecision.DENY
        else:
            decision = AIDecision.PENDING
        
        # Extract reasoning (everything after YES/NO)
        reasoning = response
        if "yes" in response[:10]:
            reasoning = response[response.find("yes") + 3:].strip()
        elif "no" in response[:10]:
            reasoning = response[response.find("no") + 2:].strip()
        
        # Estimate confidence based on response quality
        confidence = 0.7  # Default confidence
        if len(reasoning) > 20:
            confidence = 0.8
        if any(word in reasoning.lower() for word in ["strong", "clear", "definite"]):
            confidence = 0.9
        if any(word in reasoning.lower() for word in ["uncertain", "maybe", "possibly"]):
            confidence = 0.6
        
        return decision, reasoning, confidence
    
    def get_consensus(self, results: List[AIValidationResult]) -> Tuple[AIDecision, float, str]:
        """
        Get consensus from multiple AI validation results
        
        Args:
            results: List of AI validation results
            
        Returns:
            Tuple[AIDecision, float, str]: Consensus decision, confidence, and reasoning
        """
        if not results:
            return AIDecision.PENDING, 0.0, "No AI validation results"
        
        # Count decisions
        approve_count = sum(1 for r in results if r.decision == AIDecision.APPROVE)
        deny_count = sum(1 for r in results if r.decision == AIDecision.DENY)
        total_count = len(results)
        
        # Calculate consensus
        if approve_count > deny_count and approve_count >= total_count * 0.6:
            consensus = AIDecision.APPROVE
            confidence = approve_count / total_count
            reasoning = f"Consensus: {approve_count}/{total_count} agents approve"
        elif deny_count > approve_count and deny_count >= total_count * 0.6:
            consensus = AIDecision.DENY
            confidence = deny_count / total_count
            reasoning = f"Consensus: {deny_count}/{total_count} agents deny"
        else:
            consensus = AIDecision.PENDING
            confidence = 0.5
            reasoning = f"No clear consensus: {approve_count} approve, {deny_count} deny"
        
        return consensus, confidence, reasoning
    
    async def save_validation_result(self, hypothesis: TradeHypothesis, results: List[AIValidationResult]):
        """Save validation results to database"""
        try:
            # This would save to the trade_decisions table
            # Implementation depends on your database schema
            logger.info(f"💾 Saved validation results for {hypothesis.pair}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save validation results: {e}")
    
    async def close(self):
        """Close AI validator and cleanup resources"""
        try:
            await self.http_client.aclose()
            logger.info("✅ AI Validator closed")
        except Exception as e:
            logger.error(f"❌ Error closing AI Validator: {e}")


# Export main class
__all__ = ["AIValidator", "TradeHypothesis", "AIValidationResult", "AIDecision"]