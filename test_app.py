#!/usr/bin/env python3
"""
test_app.py - Test script for CryptoSDCA-AI
This script tests the application startup and basic functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.config import get_settings
from src.database import init_database, check_database_connection
from src.core.exchange_manager import ExchangeManager
from src.core.ai_validator import AIValidator
from src.core.sentiment_analyzer import SentimentAnalyzer
from src.core.risk_manager import RiskManager
from src.core.indicators import TechnicalIndicators

async def test_database():
    """Test database connection and initialization"""
    logger.info("🧪 Testing database...")
    
    try:
        # Test database connection
        if check_database_connection():
            logger.success("✅ Database connection successful")
        else:
            logger.error("❌ Database connection failed")
            return False
        
        # Test database initialization
        if await init_database():
            logger.success("✅ Database initialization successful")
            return True
        else:
            logger.error("❌ Database initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

async def test_components():
    """Test core components initialization"""
    logger.info("🧪 Testing core components...")
    
    try:
        # Test Exchange Manager
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()
        logger.success("✅ Exchange Manager initialized")
        
        # Test AI Validator
        ai_validator = AIValidator()
        await ai_validator.initialize()
        logger.success("✅ AI Validator initialized")
        
        # Test Sentiment Analyzer
        sentiment_analyzer = SentimentAnalyzer()
        await sentiment_analyzer.initialize()
        logger.success("✅ Sentiment Analyzer initialized")
        
        # Test Risk Manager
        risk_manager = RiskManager(exchange_manager=exchange_manager)
        await risk_manager.initialize()
        logger.success("✅ Risk Manager initialized")
        
        # Test Technical Indicators
        indicators = TechnicalIndicators()
        await indicators.initialize()
        logger.success("✅ Technical Indicators initialized")
        
        # Clean up
        await exchange_manager.close()
        await ai_validator.close()
        await sentiment_analyzer.close()
        await risk_manager.close()
        await indicators.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Component test failed: {e}")
        return False

async def test_configuration():
    """Test configuration loading"""
    logger.info("🧪 Testing configuration...")
    
    try:
        settings = get_settings()
        
        # Test basic settings
        assert settings.app_name == "CryptoSDCA-AI"
        assert settings.debug is True
        assert settings.port == 8000
        
        logger.success("✅ Configuration loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🚀 Starting CryptoSDCA-AI tests...")
    
    tests = [
        ("Configuration", test_configuration),
        ("Database", test_database),
        ("Components", test_components),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} test...")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.success(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} test ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All tests passed! Application is ready to run.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)