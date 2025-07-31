#!/usr/bin/env python3
"""
run.py - Simple run script for CryptoSDCA-AI
This script starts the application with proper error handling.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.database import init_database, create_initial_data
from src.config import get_settings

def setup_logging():
    """Setup logging configuration"""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "data/crypto_dca_bot.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )

async def initialize_application():
    """Initialize the application"""
    try:
        logger.info("🚀 Initializing CryptoSDCA-AI...")
        
        # Create data directory
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Initialize database
        logger.info("🔄 Setting up database...")
        if not await init_database():
            logger.error("❌ Database initialization failed")
            return False
        
        # Create initial data (admin user only)
        logger.info("🔄 Creating initial data...")
        await create_initial_data()
        
        logger.success("✅ Application initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return False

def main():
    """Main function"""
    try:
        # Setup logging
        setup_logging()
        
        # Get settings
        settings = get_settings()
        
        logger.info("=" * 60)
        logger.info("🤖 CryptoSDCA-AI Trading Bot")
        logger.info("=" * 60)
        logger.info(f"Version: {settings.version}")
        logger.info(f"Debug Mode: {settings.debug}")
        logger.info(f"Paper Trading: {settings.paper_trading}")
        logger.info(f"Host: {settings.host}:{settings.port}")
        logger.info("=" * 60)
        
        # Initialize application
        success = asyncio.run(initialize_application())
        if not success:
            logger.error("❌ Failed to initialize application")
            sys.exit(1)
        
        # Start the application
        logger.info("🎉 Starting CryptoSDCA-AI server...")
        logger.info(f"🌐 Access the application at: http://{settings.host}:{settings.port}")
        logger.info("👤 Default login: admin / bot123")
        logger.info("📚 API docs: http://localhost:8000/docs")
        logger.info("=" * 60)
        
        # Import and run the main application
        from src.main import run
        run()
        
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()