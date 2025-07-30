"""
src/core/database.py
Database configuration and session management for CryptoSDCA-AI
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

from src.config import get_settings

# Get settings
settings = get_settings()

# Database URL configuration
DATABASE_URL = settings.get_database_url()

# Create engine with proper SQLite configuration
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        poolclass=StaticPool,
        echo=settings.debug
    )
else:
    # For PostgreSQL or other databases
    engine = create_engine(
        DATABASE_URL,
        echo=settings.debug
    )

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI
    Provides a database session for each request
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        raise


def drop_tables():
    """
    Drop all database tables (use with caution!)
    """
    try:
        Base.metadata.drop_all(bind=engine)
        print("✅ Database tables dropped successfully!")
    except Exception as e:
        print(f"❌ Error dropping database tables: {e}")
        raise


def get_database_info():
    """
    Get database connection information
    """
    return {
        "url": DATABASE_URL,
        "engine": str(engine),
        "tables": list(Base.metadata.tables.keys()) if Base.metadata.tables else []
    }


if __name__ == "__main__":
    print("🗄️ Database Configuration:")
    info = get_database_info()
    print(f"URL: {info['url']}")
    print(f"Engine: {info['engine']}")
    print(f"Tables: {info['tables']}")
    
    # Test connection
    try:
        with engine.connect() as conn:
            print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
