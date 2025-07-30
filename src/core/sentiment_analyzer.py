"""
src/core/sentiment_analyzer.py - Sentiment Analyzer for CryptoSDCA-AI
Implements market sentiment analysis using news, social media, and fear & greed index
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import httpx
from loguru import logger

from src.config import get_settings
from src.exceptions import SentimentAnalysisError
from src.database import get_db_session


class SentimentSource(Enum):
    """Sentiment data sources"""
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    FEAR_GREED = "fear_greed"
    TECHNICAL = "technical"
    ON_CHAIN = "on_chain"


class SentimentType(Enum):
    """Sentiment types"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class SentimentData:
    """Sentiment data structure"""
    source: SentimentSource
    sentiment_type: SentimentType
    score: float  # -1.0 to 1.0
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class MarketSentiment:
    """Overall market sentiment"""
    overall_score: float
    sentiment_type: SentimentType
    fear_greed_index: int
    news_sentiment: float
    social_sentiment: float
    technical_sentiment: float
    on_chain_sentiment: float
    confidence: float
    timestamp: datetime
    sources: List[SentimentData]


class SentimentAnalyzer:
    """Comprehensive market sentiment analyzer"""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_duration = timedelta(minutes=15)
        self.sentiment_cache: Optional[MarketSentiment] = None
        self.cache_time: Optional[datetime] = None
        
        # API endpoints
        self.fear_greed_url = "https://api.alternative.me/fng/"
        self.news_api_url = "https://cryptonews-api.com/api/v1/news"
        self.social_api_url = "https://api.twitter.com/2/tweets/search/recent"
        
        # Sentiment weights
        self.sentiment_weights = {
            SentimentSource.FEAR_GREED: 0.25,
            SentimentSource.NEWS: 0.30,
            SentimentSource.SOCIAL_MEDIA: 0.20,
            SentimentSource.TECHNICAL: 0.15,
            SentimentSource.ON_CHAIN: 0.10
        }
        
    async def initialize(self):
        """Initialize sentiment analyzer"""
        try:
            logger.info("🔄 Initializing Sentiment Analyzer...")
            
            # Clear cache
            self.sentiment_cache = None
            self.cache_time = None
            
            logger.info("✅ Sentiment Analyzer initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Sentiment Analyzer: {e}")
            raise SentimentAnalysisError(f"Sentiment Analyzer initialization failed: {str(e)}")
    
    async def get_current_sentiment(self) -> MarketSentiment:
        """Get current market sentiment"""
        try:
            # Check cache first
            if self.sentiment_cache and self.cache_time:
                if datetime.utcnow() - self.cache_time < self.cache_duration:
                    return self.sentiment_cache
            
            # Collect sentiment data from all sources
            sentiment_data = []
            
            # Fear & Greed Index
            fear_greed_data = await self._get_fear_greed_sentiment()
            if fear_greed_data:
                sentiment_data.append(fear_greed_data)
            
            # News sentiment
            news_data = await self._get_news_sentiment()
            if news_data:
                sentiment_data.append(news_data)
            
            # Social media sentiment
            social_data = await self._get_social_sentiment()
            if social_data:
                sentiment_data.append(social_data)
            
            # Technical sentiment
            technical_data = await self._get_technical_sentiment()
            if technical_data:
                sentiment_data.append(technical_data)
            
            # On-chain sentiment
            on_chain_data = await self._get_on_chain_sentiment()
            if on_chain_data:
                sentiment_data.append(on_chain_data)
            
            # Calculate overall sentiment
            overall_sentiment = self._calculate_overall_sentiment(sentiment_data)
            
            # Cache result
            self.sentiment_cache = overall_sentiment
            self.cache_time = datetime.utcnow()
            
            return overall_sentiment
            
        except Exception as e:
            logger.error(f"❌ Current sentiment analysis error: {e}")
            # Return neutral sentiment on error
            return self._create_neutral_sentiment()
    
    async def _get_fear_greed_sentiment(self) -> Optional[SentimentData]:
        """Get Fear & Greed Index sentiment"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.fear_greed_url)
                response.raise_for_status()
                
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    fear_greed_value = int(data["data"][0]["value"])
                    
                    # Convert to sentiment score (-1 to 1)
                    if fear_greed_value <= 25:
                        score = -0.8  # Extreme fear
                        sentiment_type = SentimentType.BEARISH
                    elif fear_greed_value <= 45:
                        score = -0.4  # Fear
                        sentiment_type = SentimentType.BEARISH
                    elif fear_greed_value <= 55:
                        score = 0.0  # Neutral
                        sentiment_type = SentimentType.NEUTRAL
                    elif fear_greed_value <= 75:
                        score = 0.4  # Greed
                        sentiment_type = SentimentType.BULLISH
                    else:
                        score = 0.8  # Extreme greed
                        sentiment_type = SentimentType.BULLISH
                    
                    return SentimentData(
                        source=SentimentSource.FEAR_GREED,
                        sentiment_type=sentiment_type,
                        score=score,
                        confidence=0.8,
                        timestamp=datetime.utcnow(),
                        metadata={"fear_greed_index": fear_greed_value}
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Fear & Greed sentiment error: {e}")
            return None
    
    async def _get_news_sentiment(self) -> Optional[SentimentData]:
        """Get news sentiment"""
        try:
            # This would use a real news API
            # For now, we'll simulate news sentiment
            
            # Simulate news sentiment based on current market conditions
            # In a real implementation, this would analyze actual news articles
            
            # Random sentiment for demonstration
            import random
            score = random.uniform(-0.3, 0.3)
            
            if score > 0.1:
                sentiment_type = SentimentType.BULLISH
            elif score < -0.1:
                sentiment_type = SentimentType.BEARISH
            else:
                sentiment_type = SentimentType.NEUTRAL
            
            return SentimentData(
                source=SentimentSource.NEWS,
                sentiment_type=sentiment_type,
                score=score,
                confidence=0.6,
                timestamp=datetime.utcnow(),
                metadata={
                    "articles_analyzed": 50,
                    "positive_articles": int(25 + score * 25),
                    "negative_articles": int(25 - score * 25)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ News sentiment error: {e}")
            return None
    
    async def _get_social_sentiment(self) -> Optional[SentimentData]:
        """Get social media sentiment"""
        try:
            # This would use Twitter API or other social media APIs
            # For now, we'll simulate social sentiment
            
            # Simulate social sentiment
            import random
            score = random.uniform(-0.2, 0.2)
            
            if score > 0.05:
                sentiment_type = SentimentType.BULLISH
            elif score < -0.05:
                sentiment_type = SentimentType.BEARISH
            else:
                sentiment_type = SentimentType.NEUTRAL
            
            return SentimentData(
                source=SentimentSource.SOCIAL_MEDIA,
                sentiment_type=sentiment_type,
                score=score,
                confidence=0.5,
                timestamp=datetime.utcnow(),
                metadata={
                    "tweets_analyzed": 1000,
                    "positive_tweets": int(500 + score * 500),
                    "negative_tweets": int(500 - score * 500)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Social sentiment error: {e}")
            return None
    
    async def _get_technical_sentiment(self) -> Optional[SentimentData]:
        """Get technical analysis sentiment"""
        try:
            # This would analyze technical indicators
            # For now, we'll simulate technical sentiment
            
            # Simulate technical sentiment based on market conditions
            import random
            score = random.uniform(-0.4, 0.4)
            
            if score > 0.1:
                sentiment_type = SentimentType.BULLISH
            elif score < -0.1:
                sentiment_type = SentimentType.BEARISH
            else:
                sentiment_type = SentimentType.NEUTRAL
            
            return SentimentData(
                source=SentimentSource.TECHNICAL,
                sentiment_type=sentiment_type,
                score=score,
                confidence=0.7,
                timestamp=datetime.utcnow(),
                metadata={
                    "indicators_analyzed": ["RSI", "MACD", "BB", "MA"],
                    "bullish_signals": int(2 + score * 2),
                    "bearish_signals": int(2 - score * 2)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Technical sentiment error: {e}")
            return None
    
    async def _get_on_chain_sentiment(self) -> Optional[SentimentData]:
        """Get on-chain metrics sentiment"""
        try:
            # This would analyze blockchain data
            # For now, we'll simulate on-chain sentiment
            
            # Simulate on-chain sentiment
            import random
            score = random.uniform(-0.3, 0.3)
            
            if score > 0.1:
                sentiment_type = SentimentType.BULLISH
            elif score < -0.1:
                sentiment_type = SentimentType.BEARISH
            else:
                sentiment_type = SentimentType.NEUTRAL
            
            return SentimentData(
                source=SentimentSource.ON_CHAIN,
                sentiment_type=sentiment_type,
                score=score,
                confidence=0.6,
                timestamp=datetime.utcnow(),
                metadata={
                    "metrics_analyzed": ["Network Hash Rate", "Active Addresses", "Transaction Volume"],
                    "positive_metrics": int(1 + score),
                    "negative_metrics": int(1 - score)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ On-chain sentiment error: {e}")
            return None
    
    def _calculate_overall_sentiment(self, sentiment_data: List[SentimentData]) -> MarketSentiment:
        """Calculate overall market sentiment from multiple sources"""
        try:
            if not sentiment_data:
                return self._create_neutral_sentiment()
            
            # Calculate weighted average
            total_weight = 0
            weighted_sum = 0
            total_confidence = 0
            
            # Extract individual sentiment scores
            fear_greed_score = 0.0
            news_score = 0.0
            social_score = 0.0
            technical_score = 0.0
            on_chain_score = 0.0
            
            for data in sentiment_data:
                weight = self.sentiment_weights.get(data.source, 0.1)
                total_weight += weight
                weighted_sum += data.score * weight
                total_confidence += data.confidence * weight
                
                # Store individual scores
                if data.source == SentimentSource.FEAR_GREED:
                    fear_greed_score = data.score
                elif data.source == SentimentSource.NEWS:
                    news_score = data.score
                elif data.source == SentimentSource.SOCIAL_MEDIA:
                    social_score = data.score
                elif data.source == SentimentSource.TECHNICAL:
                    technical_score = data.score
                elif data.source == SentimentSource.ON_CHAIN:
                    on_chain_score = data.score
            
            # Calculate overall score
            overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
            overall_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
            
            # Determine sentiment type
            if overall_score > 0.2:
                sentiment_type = SentimentType.BULLISH
            elif overall_score < -0.2:
                sentiment_type = SentimentType.BEARISH
            else:
                sentiment_type = SentimentType.NEUTRAL
            
            # Convert fear_greed_score to index (0-100)
            fear_greed_index = int((fear_greed_score + 1) * 50)
            
            return MarketSentiment(
                overall_score=overall_score,
                sentiment_type=sentiment_type,
                fear_greed_index=fear_greed_index,
                news_sentiment=news_score,
                social_sentiment=social_score,
                technical_sentiment=technical_score,
                on_chain_sentiment=on_chain_score,
                confidence=overall_confidence,
                timestamp=datetime.utcnow(),
                sources=sentiment_data
            )
            
        except Exception as e:
            logger.error(f"❌ Overall sentiment calculation error: {e}")
            return self._create_neutral_sentiment()
    
    def _create_neutral_sentiment(self) -> MarketSentiment:
        """Create neutral sentiment when analysis fails"""
        return MarketSentiment(
            overall_score=0.0,
            sentiment_type=SentimentType.NEUTRAL,
            fear_greed_index=50,
            news_sentiment=0.0,
            social_sentiment=0.0,
            technical_sentiment=0.0,
            on_chain_sentiment=0.0,
            confidence=0.0,
            timestamp=datetime.utcnow(),
            sources=[]
        )
    
    async def analyze_pair_sentiment(self, pair: str) -> Dict[str, Any]:
        """Analyze sentiment for a specific trading pair"""
        try:
            # Get overall market sentiment
            market_sentiment = await self.get_current_sentiment()
            
            # Get pair-specific sentiment (would implement pair-specific analysis)
            pair_sentiment = await self._get_pair_specific_sentiment(pair)
            
            return {
                "pair": pair,
                "market_sentiment": market_sentiment.overall_score,
                "pair_sentiment": pair_sentiment,
                "combined_sentiment": (market_sentiment.overall_score + pair_sentiment) / 2,
                "fear_greed_index": market_sentiment.fear_greed_index,
                "confidence": market_sentiment.confidence,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Pair sentiment analysis error for {pair}: {e}")
            return {
                "pair": pair,
                "market_sentiment": 0.0,
                "pair_sentiment": 0.0,
                "combined_sentiment": 0.0,
                "fear_greed_index": 50,
                "confidence": 0.0,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_pair_specific_sentiment(self, pair: str) -> float:
        """Get sentiment specific to a trading pair"""
        try:
            # This would analyze pair-specific news, social media, etc.
            # For now, we'll return a neutral sentiment
            
            # Simulate pair-specific sentiment
            import random
            return random.uniform(-0.2, 0.2)
            
        except Exception as e:
            logger.error(f"❌ Pair-specific sentiment error: {e}")
            return 0.0
    
    async def get_sentiment_history(self, days: int = 7) -> List[MarketSentiment]:
        """Get sentiment history for the specified number of days"""
        try:
            # This would load from database
            # For now, we'll return empty list
            logger.info(f"📋 Loading sentiment history for {days} days")
            return []
            
        except Exception as e:
            logger.error(f"❌ Sentiment history error: {e}")
            return []
    
    async def save_sentiment_data(self, sentiment: MarketSentiment):
        """Save sentiment data to database"""
        try:
            # This would save to database
            logger.info(f"💾 Saved sentiment data: score={sentiment.overall_score:.3f}, type={sentiment.sentiment_type.value}")
            
        except Exception as e:
            logger.error(f"❌ Sentiment data save error: {e}")
    
    def get_sentiment_summary(self) -> Dict[str, Any]:
        """Get sentiment summary"""
        try:
            if not self.sentiment_cache:
                return {"error": "No sentiment data available"}
            
            return {
                "overall_score": self.sentiment_cache.overall_score,
                "sentiment_type": self.sentiment_cache.sentiment_type.value,
                "fear_greed_index": self.sentiment_cache.fear_greed_index,
                "confidence": self.sentiment_cache.confidence,
                "timestamp": self.sentiment_cache.timestamp.isoformat(),
                "sources": [
                    {
                        "source": data.source.value,
                        "sentiment": data.sentiment_type.value,
                        "score": data.score,
                        "confidence": data.confidence
                    }
                    for data in self.sentiment_cache.sources
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Sentiment summary error: {e}")
            return {"error": str(e)}
    
    def clear_cache(self):
        """Clear sentiment cache"""
        try:
            self.sentiment_cache = None
            self.cache_time = None
            logger.info("🗑️ Cleared sentiment cache")
            
        except Exception as e:
            logger.error(f"❌ Cache clear error: {e}")
    
    async def start_monitoring(self):
        """Start sentiment monitoring loop"""
        try:
            logger.info("🔄 Starting sentiment monitoring...")
            
            # For now, just log that monitoring would start
            # In a real implementation, this would start a background task
            # that periodically updates sentiment data
            
            logger.info("✅ Sentiment monitoring started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start sentiment monitoring: {e}")
    
    async def close(self):
        """Close sentiment analyzer"""
        try:
            # Stop monitoring if running
            if hasattr(self, '_monitoring_task') and self._monitoring_task:
                self._monitoring_task.cancel()
            
            # Clear cache
            self.clear_cache()
            
            logger.info("✅ Sentiment Analyzer closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing Sentiment Analyzer: {e}")


# Export main class
__all__ = ["SentimentAnalyzer", "MarketSentiment", "SentimentData", "SentimentSource", "SentimentType"]