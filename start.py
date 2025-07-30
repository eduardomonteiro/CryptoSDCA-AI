#!/usr/bin/env python3
"""
start.py - Simple startup script for CryptoSDCA-AI
This script initializes the database and starts the application.
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

async def setup_database():
    """Initialize database and create initial data"""
    try:
        logger.info("🔄 Initializing database...")
        
        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Initialize database
        success = await init_database()
        if not success:
            logger.error("❌ Database initialization failed")
            return False
        
        # Create initial data (admin user, etc.)
        await create_initial_data()
        
        logger.success("✅ Database setup complete")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        return False

def main():
    """Main startup function"""
    try:
        logger.info("🚀 Starting CryptoSDCA-AI setup...")
        
        # Setup database
        success = asyncio.run(setup_database())
        if not success:
            logger.error("❌ Setup failed. Exiting.")
            sys.exit(1)
        
        # Start the application
        logger.info("🎉 Setup complete! Starting application...")
        
        # Import and run the main application
        from src.main import run
        run()
        
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()