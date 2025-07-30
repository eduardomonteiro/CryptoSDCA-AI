"""
src/database.py - Configuração do banco de dados SQLite/PostgreSQL
Configurado para trabalhar com as novas configurações Pydantic v2
"""

import os
from typing import Generator, Optional
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, event, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from loguru import logger

# Import corrigido das configurações
from src.config import get_settings

# Configurações
settings = get_settings()

# Base para todos os modelos SQLAlchemy - usar a mesma base em todo projeto
Base = declarative_base()

# Configuração do engine baseada no tipo de banco
if settings.database_url.startswith("sqlite"):
    # Configuração específica para SQLite
    engine = create_engine(
        settings.database_url,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        poolclass=StaticPool,
        pool_pre_ping=True,
        echo=settings.debug  # Log SQL queries em modo debug
    )
    
    # Configurar SQLite para suportar foreign keys
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Ativa foreign keys no SQLite"""
        if 'sqlite' in settings.database_url:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")  # Melhor performance
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=memory")
            cursor.close()

else:
    # Configuração para PostgreSQL ou outros bancos
    engine = create_engine(
        settings.database_url,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,
        echo=settings.debug
    )

# Session factory - exportar para uso direto
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Engine síncrono para operações diretas
sync_engine = engine

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obter sessão do banco de dados
    
    Yields:
        Session: Sessão SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def init_database() -> bool:
    """
    Inicializa o banco de dados criando todas as tabelas
    
    Returns:
        bool: True se inicialização foi bem-sucedida
    """
    try:
        # Importar todos os modelos para garantir que sejam registrados
        from src.models.models import (
            User, Exchange, AIAgent, TradingPair, Order, TradeDecision,
            TradeHistory, SystemSettings, NewsSource, MarketSentiment, SystemHealth
        )
        
        logger.info("Creating database tables...")
        
        # Criar todas as tabelas
        Base.metadata.create_all(bind=engine)
        
        # Verificar se as tabelas foram criadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Database initialized with {len(tables)} tables: {', '.join(tables)}")
        
        # Inserir dados iniciais se necessário
        await create_initial_data()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


async def create_initial_data():
    """Cria dados iniciais necessários"""
    try:
        db = SessionLocal()
        
        # Importar modelos necessários
        from src.models.models import User, SystemSettings
        import bcrypt
        
        # Criar usuário admin padrão se não existir
        existing_user = db.query(User).filter_by(username="admin").first()
        if not existing_user:
            password_hash = bcrypt.hashpw("bot123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin_user = User(
                username="admin",
                email="admin@cryptosdca.ai",
                hashed_password=password_hash,
                is_admin=True,
                is_active=True
            )
            db.add(admin_user)
            logger.info("Created default admin user")

        # Criar configurações padrão do sistema se não existirem
        default_settings = [
            ("daily_profit_target", "1.0", "float", "Meta de lucro diária (%)", "trading"),
            ("global_stop_loss", "-3.0", "float", "Stop loss global (%)", "trading"),
            ("max_operation_duration_hours", "72", "int", "Duração máxima da operação (horas)", "trading"),
            ("min_pairs_count", "3", "int", "Número mínimo de pares simultâneos", "trading"),
            ("paper_trading", "true", "bool", "Modo paper trading ativo", "trading"),
        ]
        
        for key, value, value_type, description, category in default_settings:
            existing_setting = db.query(SystemSettings).filter_by(key=key).first()
            if not existing_setting:
                setting = SystemSettings(
                    key=key,
                    value=value,
                    value_type=value_type,
                    description=description,
                    category=category
                )
                db.add(setting)
        
        db.commit()
        db.close()
        logger.info("Initial data created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create initial data: {e}")


async def close_database():
    """Fecha conexões do banco de dados"""
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


def get_db_session() -> Session:
    """
    Retorna uma nova sessão do banco de dados
    
    Returns:
        Session: Nova sessão SQLAlchemy
    """
    return SessionLocal()


@asynccontextmanager
async def get_async_db_session():
    """
    Context manager assíncrono para sessão do banco
    
    Yields:
        Session: Sessão SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Async database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Verifica se a conexão com o banco está funcionando
    
    Returns:
        bool: True se conexão está ok
    """
    try:
        db = SessionLocal()
        # Executar query simples para testar conexão
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Retorna informações sobre o banco de dados
    
    Returns:
        dict: Informações do banco
    """
    try:
        db = SessionLocal()
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        info = {
            "url": str(engine.url).replace(str(engine.url.password) if engine.url.password else '', '***'),
            "dialect": engine.dialect.name,
            "driver": engine.dialect.driver,
            "tables": inspector.get_table_names(),
            "connection_pool_size": engine.pool.size(),
            "checked_out_connections": engine.pool.checkedout()
        }
        
        db.close()
        return info
        
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}


# Health check para API
async def database_health_check() -> dict:
    """
    Health check do banco de dados para API
    
    Returns:
        dict: Status do banco
    """
    try:
        is_connected = check_database_connection()
        db_info = get_database_info()
        
        return {
            "status": "healthy" if is_connected else "unhealthy",
            "connected": is_connected,
            "info": db_info
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }


if __name__ == "__main__":
    """Teste das configurações do banco"""
    import asyncio
    
    async def test_database():
        print("🔧 Testando configuração do banco de dados...")
        
        # Testar conexão
        print(f"Conectando em: {settings.database_url}")
        is_connected = check_database_connection()
        print(f"Conexão: {'✅ OK' if is_connected else '❌ FALHOU'}")
        
        # Obter informações
        info = get_database_info()
        print(f"Dialect: {info.get('dialect', 'N/A')}")
        print(f"Driver: {info.get('driver', 'N/A')}")
        
        # Inicializar se possível
        if is_connected:
            success = await init_database()
            print(f"Inicialização: {'✅ OK' if success else '❌ FALHOU'}")
            
            # Health check
            health = await database_health_check()
            print(f"Health check: {health['status']}")
    
    asyncio.run(test_database())
