#!/usr/bin/env python3
"""
scripts/init_db.py
Database Initialization Script for CryptoSDCA-AI

This script:
1. Creates all database tables
2. Initializes default user (admin/bot123)
3. Creates default system settings
4. Sets up sample data for testing
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

import bcrypt
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config import get_settings
from src.database import Base, sync_engine
from src.models.models import (
    User, Exchange, AIAgent, TradingPair, SystemSettings, 
    NewsSource, MarketSentiment, create_all_tables
)

def hash_password(password: str) -> str:
    """Hash a password with bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def init_database():
    """Initialize database with all tables"""
    
    print("🔧 Initializing CryptoSDCA-AI Database...")
    
    try:
        # Create all tables
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=sync_engine)
        print("✅ Database tables created successfully")
        
        # Create session
        Session = sessionmaker(bind=sync_engine)
        db = Session()
        
        try:
            # Create default admin user
            print("👤 Creating default admin user...")
            create_default_user(db)
            
            # Create system settings
            print("⚙️ Creating system settings...")
            create_system_settings(db)
            
            # Create default news sources
            print("📰 Creating news sources...")
            create_news_sources(db)
            
            # Create sample data for testing
            print("🧪 Creating sample data...")
            create_sample_data(db)
            
            # Commit all changes
            db.commit()
            print("✅ Database initialization completed successfully!")
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

def create_default_user(db):
    """Create default admin user"""
    
    # Check if admin user already exists
    existing_user = db.query(User).filter_by(username="admin").first()
    if existing_user:
        print("   ⚠️ Admin user already exists, skipping...")
        return
    
    # Create admin user
    admin_user = User(
        username="admin",
        email="admin@cryptosdca.ai",
        hashed_password=hash_password("bot123"),
        is_admin=True,
        is_active=True
    )
    
    db.add(admin_user)
    print("   ✅ Default admin user created (admin/bot123)")

def create_system_settings(db):
    """Create default system settings"""
    
    default_settings = [
        # Trading Settings
        ("daily_profit_target", "1.0", "float", "Meta de lucro diária (%)", "trading"),
        ("global_stop_loss", "-3.0", "float", "Stop loss global (%)", "trading"),
        ("max_operation_duration_hours", "72", "int", "Duração máxima da operação (horas)", "trading"),
        ("min_pairs_count", "3", "int", "Número mínimo de pares simultâneos", "trading"),
        ("paper_trading", "true", "bool", "Modo paper trading ativo", "trading"),
        ("max_position_size_usd", "1000.0", "float", "Tamanho máximo da posição (USD)", "trading"),
        ("base_currencies", "USDT,USDC,DAI", "string", "Moedas base aceitas", "trading"),
        
        # Risk Management
        ("max_drawdown_percent", "5.0", "float", "Drawdown máximo permitido (%)", "risk_management"),
        ("daily_loss_limit", "100.0", "float", "Limite de perda diária (USD)", "risk_management"),
        
        # Technical Indicators
        ("rsi_period", "14", "int", "Período RSI", "indicators"),
        ("rsi_oversold", "30", "int", "RSI oversold", "indicators"),
        ("rsi_overbought", "70", "int", "RSI overbought", "indicators"),
        ("macd_fast_period", "12", "int", "MACD período rápido", "indicators"),
        ("macd_slow_period", "26", "int", "MACD período lento", "indicators"),
        ("macd_signal_period", "9", "int", "MACD período do sinal", "indicators"),
        ("atr_period", "14", "int", "Período ATR", "indicators"),
        
        # Grid Trading
        ("grid_spacing_sideways_min", "1.0", "float", "Espaçamento mínimo grid lateral (%)", "grid"),
        ("grid_spacing_sideways_max", "3.0", "float", "Espaçamento máximo grid lateral (%)", "grid"),
        ("grid_spacing_trend_min", "2.0", "float", "Espaçamento mínimo grid tendência (%)", "grid"),
        ("grid_spacing_trend_max", "5.0", "float", "Espaçamento máximo grid tendência (%)", "grid"),
        
        # Sentiment Analysis
        ("sentiment_update_interval_minutes", "15", "int", "Intervalo de atualização sentimento (min)", "sentiment"),
        ("fear_greed_api_url", "https://api.alternative.me/fng/", "string", "URL API Fear & Greed", "sentiment"),
        
        # System
        ("app_version", "1.0.0", "string", "Versão da aplicação", "system"),
        ("last_backup", "", "string", "Data do último backup", "system"),
        ("maintenance_mode", "false", "bool", "Modo de manutenção", "system"),
    ]
    
    settings_created = 0
    for key, value, value_type, description, category in default_settings:
        # Check if setting already exists
        existing = db.query(SystemSettings).filter_by(key=key).first()
        if existing:
            continue
            
        setting = SystemSettings(
            key=key,
            value=value,
            value_type=value_type,
            description=description,
            category=category
        )
        db.add(setting)
        settings_created += 1
    
    print(f"   ✅ Created {settings_created} system settings")

def create_news_sources(db):
    """Create default news sources"""
    
    default_sources = [
        {
            "name": "CoinTelegraph",
            "url": "https://cointelegraph.com/rss",
            "source_type": "rss",
            "priority": 1,
            "update_interval_minutes": 15
        },
        {
            "name": "CoinDesk",
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "source_type": "rss",
            "priority": 2,
            "update_interval_minutes": 20
        },
        {
            "name": "CryptoNews",
            "url": "https://cryptonews.com/news/feed/",
            "source_type": "rss",
            "priority": 3,
            "update_interval_minutes": 30
        }
    ]
    
    sources_created = 0
    for source_data in default_sources:
        # Check if source already exists
        existing = db.query(NewsSource).filter_by(name=source_data["name"]).first()
        if existing:
            continue
            
        source = NewsSource(
            name=source_data["name"],
            url=source_data["url"],
            source_type=source_data["source_type"],
            priority=source_data["priority"],
            update_interval_minutes=source_data["update_interval_minutes"],
            is_active=True
        )
        db.add(source)
        sources_created += 1
    
    print(f"   ✅ Created {sources_created} news sources")

def create_sample_data(db):
    """Create sample data for testing"""
    
    # Get admin user
    admin_user = db.query(User).filter_by(username="admin").first()
    if not admin_user:
        print("   ⚠️ Admin user not found, skipping sample data...")
        return
    
    # Create sample exchanges (disabled by default for security)
    sample_exchanges = [
        {
            "name": "binance",
            "display_name": "Binance Testnet",
            "api_key": "sample_api_key_binance",
            "api_secret": "sample_secret_key_binance",
            "is_testnet": True,
            "is_active": False
        },
        {
            "name": "kucoin",
            "display_name": "KuCoin Sandbox",
            "api_key": "sample_api_key_kucoin",
            "api_secret": "sample_secret_key_kucoin",
            "api_passphrase": "sample_passphrase",
            "is_testnet": True,
            "is_active": False
        }
    ]
    
    exchanges_created = 0
    for exchange_data in sample_exchanges:
        # Check if exchange already exists
        existing = db.query(Exchange).filter_by(
            user_id=admin_user.id,
            name=exchange_data["name"]
        ).first()
        if existing:
            continue
            
        exchange = Exchange(
            user_id=admin_user.id,
            name=exchange_data["name"],
            display_name=exchange_data["display_name"],
            api_key=exchange_data["api_key"],
            api_secret=exchange_data["api_secret"],
            api_passphrase=exchange_data.get("api_passphrase"),
            is_testnet=exchange_data["is_testnet"],
            is_active=exchange_data["is_active"]
        )
        db.add(exchange)
        exchanges_created += 1
    
    # Create sample AI agents (disabled by default)
    sample_agents = [
        {
            "name": "Perplexity Analyst",
            "agent_type": "perplexity",
            "model_name": "sonar-medium-online",
            "role_description": "Market analysis and sentiment evaluation",
            "is_active": False
        },
        {
            "name": "OpenAI GPT-4",
            "agent_type": "openai",
            "model_name": "gpt-4",
            "endpoint_url": "https://api.openai.com/v1/chat/completions",
            "role_description": "Technical analysis and trade validation",
            "is_active": False
        }
    ]
    
    agents_created = 0
    for agent_data in sample_agents:
        # Check if agent already exists
        existing = db.query(AIAgent).filter_by(
            user_id=admin_user.id,
            name=agent_data["name"]
        ).first()
        if existing:
            continue
            
        agent = AIAgent(
            user_id=admin_user.id,
            name=agent_data["name"],
            agent_type=agent_data["agent_type"],
            model_name=agent_data.get("model_name"),
            endpoint_url=agent_data.get("endpoint_url"),
            role_description=agent_data.get("role_description"),
            is_active=agent_data["is_active"]
        )
        db.add(agent)
        agents_created += 1
    
    # Create sample trading pairs
    sample_pairs = [
        {
            "symbol": "BTC/USDT",
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "target_profit_percent": 1.0,
            "stop_loss_percent": -3.0,
            "max_position_size_usd": 1000.0
        },
        {
            "symbol": "ETH/USDT", 
            "base_asset": "ETH",
            "quote_asset": "USDT",
            "target_profit_percent": 1.2,
            "stop_loss_percent": -3.0,
            "max_position_size_usd": 800.0
        }
    ]
    
    pairs_created = 0
    if exchanges_created > 0:
        # Get first exchange for sample pairs
        first_exchange = db.query(Exchange).filter_by(user_id=admin_user.id).first()
        if first_exchange:
            for pair_data in sample_pairs:
                existing = db.query(TradingPair).filter_by(
                    exchange_id=first_exchange.id,
                    symbol=pair_data["symbol"]
                ).first()
                if existing:
                    continue
                    
                pair = TradingPair(
                    exchange_id=first_exchange.id,
                    symbol=pair_data["symbol"],
                    base_asset=pair_data["base_asset"],
                    quote_asset=pair_data["quote_asset"],
                    target_profit_percent=pair_data["target_profit_percent"],
                    stop_loss_percent=pair_data["stop_loss_percent"],
                    max_position_size_usd=pair_data["max_position_size_usd"]
                )
                db.add(pair)
                pairs_created += 1
    
    # Create sample market sentiment entry
    sample_sentiment = MarketSentiment(
        fear_greed_value=50,
        fear_greed_classification="Neutral",
        news_sentiment_score=0.0,
        overall_sentiment="neutral",
        sentiment_strength=0.5
    )
    
    # Check if any sentiment data exists
    existing_sentiment = db.query(MarketSentiment).first()
    if not existing_sentiment:
        db.add(sample_sentiment)
        print("   ✅ Created initial market sentiment data")
    
    print(f"   ✅ Created {exchanges_created} sample exchanges, {agents_created} AI agents, {pairs_created} trading pairs")

def check_database_health():
    """Check database health and show statistics"""
    
    print("\n📊 Database Health Check:")
    
    try:
        Session = sessionmaker(bind=sync_engine)
        db = Session()
        
        try:
            # Count records in each table
            users_count = db.query(User).count()
            exchanges_count = db.query(Exchange).count()
            agents_count = db.query(AIAgent).count()
            settings_count = db.query(SystemSettings).count()
            sources_count = db.query(NewsSource).count()
            pairs_count = db.query(TradingPair).count()
            sentiment_count = db.query(MarketSentiment).count()
            
            print(f"   👥 Users: {users_count}")
            print(f"   💱 Exchanges: {exchanges_count}")
            print(f"   🤖 AI Agents: {agents_count}")
            print(f"   ⚙️ Settings: {settings_count}")
            print(f"   📰 News Sources: {sources_count}")
            print(f"   💰 Trading Pairs: {pairs_count}")
            print(f"   📈 Sentiment Records: {sentiment_count}")
            
            # Test basic queries
            admin_user = db.query(User).filter_by(username="admin").first()
            if admin_user:
                print(f"   ✅ Admin user found: {admin_user.username}")
                print(f"   📧 Email: {admin_user.email}")
                print(f"   🔐 Admin privileges: {admin_user.is_admin}")
            else:
                print("   ❌ Admin user not found!")
            
            print("   ✅ Database health check passed")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"   ❌ Database health check failed: {e}")

def reset_database():
    """Reset database (drop all tables and recreate)"""
    
    print("⚠️ RESETTING DATABASE - ALL DATA WILL BE LOST!")
    
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=sync_engine)
        print("   🗑️ All tables dropped")
        
        # Recreate tables
        Base.metadata.create_all(bind=sync_engine)
        print("   📋 Tables recreated")
        
        print("✅ Database reset completed")
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        raise

def main():
    """Main function with command line options"""
    
    print("=" * 60)
    print("🚀 CryptoSDCA-AI Database Initialization")
    print("=" * 60)
    
    # Get settings
    settings = get_settings()
    print(f"📁 Database URL: {settings.database_url}")
    print(f"🐛 Debug Mode: {settings.debug}")
    print(f"📄 Paper Trading: {settings.paper_trading}")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "reset":
            print("\n🔄 Resetting database...")
            reset_database()
            print("\n🔧 Initializing fresh database...")
            init_database()
        elif command == "check":
            print("\n🔍 Checking database health...")
            check_database_health()
        elif command == "help":
            print("\nAvailable commands:")
            print("  python scripts/init_db.py          - Initialize database")
            print("  python scripts/init_db.py reset    - Reset and reinitialize")
            print("  python scripts/init_db.py check    - Check database health")
            print("  python scripts/init_db.py help     - Show this help")
            return
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'python scripts/init_db.py help' for available commands")
            return
    else:
        # Default: initialize database
        init_database()
    
    # Always run health check at the end
    check_database_health()
    
    print("\n" + "=" * 60)
    print("🎉 Database setup completed successfully!")
    print("🌐 You can now start the application:")
    print("   python -m uvicorn api.main:app --reload")
    print("   or")
    print("   .\run.ps1")
    print("=" * 60)

if __name__ == "__main__":
    main()
