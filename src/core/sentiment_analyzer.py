"""
src/core/sentiment_analyzer.py
Sentiment Analysis Engine for CryptoSDCA-AI

Collects and analyzes market sentiment from multiple sources:
- Crypto Fear & Greed Index (alternative.me)
- News sentiment from RSS feeds (CoinTelegraph, CoinDesk)
- Social media sentiment (if available)
- Custom news source management
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import httpx
import feedparser
from bs4 import BeautifulSoup
from loguru import logger

from src.config import get_settings
from src.database import get_db_session
from src.models.models import NewsSource, MarketSentiment


@dataclass
class NewsItem:
    """Item de notícia coletado"""
    title: str
    summary: str
    url: str
    published_date: datetime
    source: str
    sentiment_score: float  # -1 to 1
    keywords: List[str]


@dataclass
class SentimentData:
    """Dados consolidados de sentimento"""
    fear_greed_index: int  # 0-100
    fear_greed_classification: str
    news_sentiment_score: float  # -1 to 1
    overall_sentiment: str  # "bullish", "bearish", "neutral"
    sentiment_strength: float  # 0-1
    confidence: float  # 0-1
    last_updated: datetime


class SentimentAnalyzer:
    """
    Analisador de sentimento de mercado
    Coleta dados de múltiplas fontes e fornece análise consolidada
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Cache de dados
        self.current_sentiment: Optional[SentimentData] = None
        self.last_update = datetime.utcnow()
        self.update_interval = timedelta(minutes=self.settings.sentiment_update_interval_minutes)
        
        # Keywords para análise
        self.positive_keywords = self.settings.get_positive_keywords_list()
        self.negative_keywords = self.settings.get_negative_keywords_list()
        
        # Fontes de notícias
        self.news_sources = []
        
    async def initialize(self):
        """Inicializa o analisador de sentimento"""
        try:
            logger.info("Initializing Sentiment Analyzer...")
            
            # Carregar fontes de notícias do banco
            await self._load_news_sources()
            
            # Fazer primeira coleta de dados
            await self._update_sentiment_data()
            
            logger.info(f"Sentiment Analyzer initialized with {len(self.news_sources)} news sources")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentiment Analyzer: {e}")
            raise
            
    async def close(self):
        """Fecha o analisador"""
        await self.http_client.aclose()
        logger.info("Sentiment Analyzer closed")
        
    async def start_monitoring(self):
        """Inicia monitoramento contínuo de sentimento"""
        
        logger.info("Starting sentiment monitoring loop...")
        
        while True:
            try:
                # Verificar se é hora de atualizar
                if datetime.utcnow() - self.last_update >= self.update_interval:
                    await self._update_sentiment_data()
                    
                # Aguardar antes da próxima verificação
                await asyncio.sleep(300)  # 5 minutos
                
            except Exception as e:
                logger.error(f"Error in sentiment monitoring loop: {e}")
                await asyncio.sleep(600)  # Aguardar mais tempo em caso de erro
                
    async def get_current_sentiment(self) -> Dict[str, Any]:
        """Retorna dados atuais de sentimento"""
        
        if not self.current_sentiment:
            await self._update_sentiment_data()
            
        if self.current_sentiment:
            return {
                "fear_greed_index": self.current_sentiment.fear_greed_index,
                "fear_greed_classification": self.current_sentiment.fear_greed_classification,
                "news_sentiment": self.current_sentiment.news_sentiment_score,
                "overall_sentiment": self.current_sentiment.overall_sentiment,
                "sentiment_strength": self.current_sentiment.sentiment_strength,
                "confidence": self.current_sentiment.confidence,
                "last_updated": self.current_sentiment.last_updated.isoformat()
            }
        else:
            # Retornar dados neutros se não há dados
            return {
                "fear_greed_index": 50,
                "fear_greed_classification": "Neutral",
                "news_sentiment": 0.0,
                "overall_sentiment": "neutral",
                "sentiment_strength": 0.5,
                "confidence": 0.3,
                "last_updated": datetime.utcnow().isoformat()
            }
            
    async def analyze_news_impact(self, symbol: str) -> Dict[str, Any]:
        """Analisa impacto específico de notícias para um símbolo"""
        
        try:
            # Buscar notícias recentes relacionadas ao símbolo
            relevant_news = await self._get_symbol_related_news(symbol)
            
            if not relevant_news:
                return {
                    "impact_score": 0.0,
                    "news_count": 0,
                    "sentiment": "neutral",
                    "key_topics": []
                }
                
            # Analisar sentimento das notícias
            positive_count = sum(1 for news in relevant_news if news.sentiment_score > 0.2)
            negative_count = sum(1 for news in relevant_news if news.sentiment_score < -0.2)
            
            # Calcular score de impacto
            total_sentiment = sum(news.sentiment_score for news in relevant_news)
            avg_sentiment = total_sentiment / len(relevant_news)
            
            # Determinar impacto geral
            if avg_sentiment > 0.3:
                impact_sentiment = "bullish"
                impact_score = min(avg_sentiment * 2, 1.0)
            elif avg_sentiment < -0.3:
                impact_sentiment = "bearish"
                impact_score = max(avg_sentiment * 2, -1.0)
            else:
                impact_sentiment = "neutral"
                impact_score = avg_sentiment
                
            # Extrair tópicos principais
            key_topics = self._extract_key_topics(relevant_news)
            
            return {
                "impact_score": impact_score,
                "news_count": len(relevant_news),
                "positive_news": positive_count,
                "negative_news": negative_count,
                "sentiment": impact_sentiment,
                "key_topics": key_topics,
                "recent_headlines": [news.title for news in relevant_news[:3]]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing news impact for {symbol}: {e}")
            return {"impact_score": 0.0, "news_count": 0, "sentiment": "neutral", "key_topics": []}
            
    async def _update_sentiment_data(self):
        """Atualiza todos os dados de sentimento"""
        
        logger.debug("Updating sentiment data...")
        
        try:
            # Coletar Fear & Greed Index
            fear_greed_data = await self._fetch_fear_greed_index()
            
            # Coletar notícias de todas as fontes
            news_items = await self._fetch_all_news()
            
            # Analisar sentimento das notícias
            news_sentiment = self._analyze_news_sentiment(news_items)
            
            # Consolidar dados
            self.current_sentiment = self._consolidate_sentiment_data(
                fear_greed_data, news_sentiment, news_items
            )
            
            # Salvar no banco de dados
            await self._save_sentiment_to_db(self.current_sentiment)
            
            self.last_update = datetime.utcnow()
            
            logger.debug(f"Sentiment updated: FG={self.current_sentiment.fear_greed_index}, "
                        f"News={self.current_sentiment.news_sentiment_score:.2f}, "
                        f"Overall={self.current_sentiment.overall_sentiment}")
            
        except Exception as e:
            logger.error(f"Error updating sentiment data: {e}")
            
    async def _fetch_fear_greed_index(self) -> Dict[str, Any]:
        """Busca Fear & Greed Index da API"""
        
        try:
            response = await self.http_client.get(self.settings.fear_greed_api_url)
            response.raise_for_status()
            
            data = response.json()
            
            if data and "data" in data and len(data["data"]) > 0:
                latest = data["data"][0]
                return {
                    "value": int(latest["value"]),
                    "classification": latest["value_classification"],
                    "timestamp": latest["timestamp"]
                }
                
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            
        # Retornar valor neutro em caso de erro
        return {
            "value": 50,
            "classification": "Neutral",
            "timestamp": str(int(datetime.utcnow().timestamp()))
        }
        
    async def _fetch_all_news(self) -> List[NewsItem]:
        """Busca notícias de todas as fontes configuradas"""
        
        all_news = []
        
        # Fontes padrão se não há configuração no banco
        if not self.news_sources:
            default_sources = [
                {"name": "CoinTelegraph", "url": self.settings.cointelegraph_rss, "type": "rss"},
                {"name": "CoinDesk", "url": self.settings.coindesk_rss, "type": "rss"}
            ]
        else:
            default_sources = [
                {"name": source.name, "url": source.url, "type": source.source_type}
                for source in self.news_sources if source.is_active
            ]
            
        for source in default_sources:
            try:
                if source["type"] == "rss":
                    news_items = await self._fetch_rss_news(source["name"], source["url"])
                    all_news.extend(news_items)
                    
            except Exception as e:
                logger.error(f"Error fetching news from {source['name']}: {e}")
                
        return all_news
        
    async def _fetch_rss_news(self, source_name: str, rss_url: str) -> List[NewsItem]:
        """Busca notícias de feed RSS"""
        
        try:
            response = await self.http_client.get(rss_url)
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.text)
            
            news_items = []
            
            # Processar apenas artigos recentes (últimas 24 horas)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            for entry in feed.entries[:20]:  # Limitar a 20 artigos mais recentes
                try:
                    # Parse data de publicação
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    else:
                        pub_date = datetime.utcnow()
                        
                    # Pular artigos antigos
                    if pub_date < cutoff_time:
                        continue
                        
                    # Extrair título e resumo
                    title = entry.title if hasattr(entry, 'title') else "No title"
                    summary = entry.summary if hasattr(entry, 'summary') else ""
                    url = entry.link if hasattr(entry, 'link') else ""
                    
                    # Limpar HTML do resumo
                    if summary:
                        summary = BeautifulSoup(summary, 'html.parser').get_text()
                        
                    # Analisar sentimento do título e resumo
                    sentiment_score = self._analyze_text_sentiment(title + " " + summary)
                    
                    # Extrair keywords
                    keywords = self._extract_keywords(title + " " + summary)
                    
                    news_item = NewsItem(
                        title=title,
                        summary=summary[:500],  # Limitar tamanho
                        url=url,
                        published_date=pub_date,
                        source=source_name,
                        sentiment_score=sentiment_score,
                        keywords=keywords
                    )
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    logger.debug(f"Error processing RSS entry: {e}")
                    continue
                    
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching RSS from {rss_url}: {e}")
            return []
            
    def _analyze_text_sentiment(self, text: str) -> float:
        """Analisa sentimento de um texto usando palavras-chave"""
        
        text_lower = text.lower()
        
        positive_score = 0
        negative_score = 0
        
        # Contar palavras positivas
        for keyword in self.positive_keywords:
            positive_score += text_lower.count(keyword.lower())
            
        # Contar palavras negativas
        for keyword in self.negative_keywords:
            negative_score += text_lower.count(keyword.lower())
            
        # Calcular score final
        total_words = len(text.split())
        if total_words == 0:
            return 0.0
            
        # Normalizar por número de palavras
        positive_ratio = positive_score / max(total_words, 1)
        negative_ratio = negative_score / max(total_words, 1)
        
        # Calcular score final (-1 a 1)
        sentiment_score = (positive_ratio - negative_ratio) * 10
        
        # Limitar entre -1 e 1
        return max(-1.0, min(1.0, sentiment_score))
        
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave relevantes do texto"""
        
        # Lista de palavras-chave cripto relevantes
        crypto_keywords = [
            "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
            "blockchain", "defi", "nft", "altcoin", "trading", "investment",
            "regulation", "adoption", "institutional", "etf", "mining"
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in crypto_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
                
        return found_keywords[:5]  # Retornar no máximo 5 keywords
        
    def _analyze_news_sentiment(self, news_items: List[NewsItem]) -> Dict[str, Any]:
        """Analisa sentimento consolidado das notícias"""
        
        if not news_items:
            return {
                "average_sentiment": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "total_articles": 0
            }
            
        # Contar sentimentos
        positive_count = sum(1 for item in news_items if item.sentiment_score > 0.2)
        negative_count = sum(1 for item in news_items if item.sentiment_score < -0.2)
        neutral_count = len(news_items) - positive_count - negative_count
        
        # Calcular sentimento médio
        total_sentiment = sum(item.sentiment_score for item in news_items)
        average_sentiment = total_sentiment / len(news_items)
        
        return {
            "average_sentiment": average_sentiment,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_articles": len(news_items)
        }
        
    def _consolidate_sentiment_data(
        self, 
        fear_greed_data: Dict[str, Any],
        news_sentiment: Dict[str, Any],
        news_items: List[NewsItem]
    ) -> SentimentData:
        """Consolida todos os dados de sentimento"""
        
        # Fear & Greed Index
        fgi_value = fear_greed_data["value"]
        fgi_classification = fear_greed_data["classification"]
        
        # Normalizar FGI para escala -1 a 1 (0 = extreme fear, 100 = extreme greed)
        fgi_normalized = (fgi_value - 50) / 50
        
        # Sentimento das notícias
        news_sentiment_score = news_sentiment["average_sentiment"]
        
        # Peso dos componentes
        fgi_weight = 0.6  # Fear & Greed tem mais peso
        news_weight = 0.4
        
        # Calcular sentimento geral
        overall_sentiment_score = (fgi_normalized * fgi_weight) + (news_sentiment_score * news_weight)
        
        # Determinar classificação geral
        if overall_sentiment_score > 0.3:
            overall_sentiment = "bullish"
            sentiment_strength = min(overall_sentiment_score, 1.0)
        elif overall_sentiment_score < -0.3:
            overall_sentiment = "bearish"
            sentiment_strength = min(abs(overall_sentiment_score), 1.0)
        else:
            overall_sentiment = "neutral"
            sentiment_strength = 0.5
            
        # Calcular confiança baseada na quantidade de dados
        confidence = 0.7  # Base
        if news_sentiment["total_articles"] > 10:
            confidence += 0.2
        if abs(fgi_normalized) > 0.5:  # FGI extremo
            confidence += 0.1
            
        confidence = min(confidence, 1.0)
        
        return SentimentData(
            fear_greed_index=fgi_value,
            fear_greed_classification=fgi_classification,
            news_sentiment_score=news_sentiment_score,
            overall_sentiment=overall_sentiment,
            sentiment_strength=sentiment_strength,
            confidence=confidence,
            last_updated=datetime.utcnow()
        )
        
    async def _get_symbol_related_news(self, symbol: str) -> List[NewsItem]:
        """Busca notícias relacionadas a um símbolo específico"""
        
        # Fazer fetch recente se necessário
        if datetime.utcnow() - self.last_update > timedelta(hours=1):
            await self._update_sentiment_data()
            
        # Para simplificar, retornar algumas notícias gerais
        # Em implementação completa, seria feita busca específica por símbolo
        recent_news = await self._fetch_all_news()
        
        # Filtrar notícias relevantes para o símbolo
        symbol_base = symbol.split('/')[0].lower()  # BTC de BTC/USDT
        
        relevant_news = []
        for news in recent_news:
            text_content = (news.title + " " + news.summary).lower()
            if symbol_base in text_content or symbol_base in news.keywords:
                relevant_news.append(news)
                
        return relevant_news[:5]  # Retornar no máximo 5 notícias
        
    def _extract_key_topics(self, news_items: List[NewsItem]) -> List[str]:
        """Extrai tópicos principais das notícias"""
        
        topic_counts = {}
        
        for news in news_items:
            for keyword in news.keywords:
                topic_counts[keyword] = topic_counts.get(keyword, 0) + 1
                
        # Ordenar por frequência e retornar top 5
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic[0] for topic in sorted_topics[:5]]
        
    async def _load_news_sources(self):
        """Carrega fontes de notícias do banco de dados"""
        
        db = get_db_session()
        try:
            self.news_sources = db.query(NewsSource).filter_by(is_active=True).all()
        finally:
            db.close()
            
    async def _save_sentiment_to_db(self, sentiment_data: SentimentData):
        """Salva dados de sentimento no banco"""
        
        try:
            db = get_db_session()
            
            market_sentiment = MarketSentiment(
                fear_greed_value=sentiment_data.fear_greed_index,
                fear_greed_classification=sentiment_data.fear_greed_classification,
                news_sentiment_score=sentiment_data.news_sentiment_score,
                overall_sentiment=sentiment_data.overall_sentiment,
                sentiment_strength=sentiment_data.sentiment_strength
            )
            
            db.add(market_sentiment)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving sentiment to database: {e}")
        finally:
            db.close()
            
    async def get_sentiment_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Retorna histórico de sentimento"""
        
        db = get_db_session()
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            sentiments = db.query(MarketSentiment).filter(
                MarketSentiment.created_at >= start_date
            ).order_by(MarketSentiment.created_at.desc()).all()
            
            return [
                {
                    "timestamp": s.created_at.isoformat(),
                    "fear_greed_index": s.fear_greed_value,
                    "news_sentiment": s.news_sentiment_score,
                    "overall_sentiment": s.overall_sentiment
                }
                for s in sentiments
            ]
            
        finally:
            db.close()