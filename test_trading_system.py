#!/usr/bin/env python3
"""
Test script for the CryptoSDCA-AI trading system
Tests CRUD operations, AI validation, and 5-minute intervals
"""

import asyncio
import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": "testuser",
    "password": "testpass123"
}

def test_health():
    """Test if the application is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Application is running")
            return True
        else:
            print("❌ Application health check failed")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to application: {e}")
        return False

def test_login():
    """Test user login"""
    try:
        response = requests.post(f"{BASE_URL}/auth/login", data=TEST_USER)
        if response.status_code == 200:
            print("✅ Login successful")
            return response.cookies
        else:
            print("❌ Login failed")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_create_session(cookies):
    """Test creating a trading session"""
    try:
        session_data = {
            "session_name": "Test Session",
            "max_trades_per_session": 50,
            "min_interval_minutes": 5,
            "max_daily_loss": 100.0,
            "target_profit": 5.0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/trading/sessions",
            json=session_data,
            cookies=cookies
        )
        
        if response.status_code == 200:
            session = response.json()
            print(f"✅ Trading session created: {session['session_name']}")
            return session['id']
        else:
            print(f"❌ Failed to create session: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        return None

def test_create_trade(cookies, session_id=None):
    """Test creating a trade with AI validation"""
    try:
        trade_data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 0.001,
            "order_type": "market",
            "exchange_id": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/trading/trades",
            json=trade_data,
            cookies=cookies
        )
        
        if response.status_code == 200:
            trade = response.json()
            print(f"✅ Trade created: {trade['symbol']} {trade['side']}")
            print(f"   AI Validation: {trade['ai_validation_passed']}")
            print(f"   AI Consensus: {trade['ai_consensus']}")
            return trade['id']
        else:
            print(f"❌ Failed to create trade: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Trade creation error: {e}")
        return None

def test_5_minute_interval(cookies):
    """Test the 5-minute interval restriction"""
    print("\n🕐 Testing 5-minute interval restriction...")
    
    # Create first trade
    trade1_id = test_create_trade(cookies)
    if not trade1_id:
        return False
    
    # Try to create another trade immediately (should fail)
    print("⏰ Attempting to create another trade immediately...")
    trade2_id = test_create_trade(cookies)
    
    if trade2_id is None:
        print("✅ 5-minute interval restriction working correctly")
        return True
    else:
        print("❌ 5-minute interval restriction failed")
        return False

def test_get_statistics(cookies):
    """Test getting trading statistics"""
    try:
        response = requests.get(f"{BASE_URL}/api/trading/statistics", cookies=cookies)
        
        if response.status_code == 200:
            stats = response.json()
            print("\n📊 Trading Statistics:")
            print(f"   Total Trades: {stats['total_trades']}")
            print(f"   Success Rate: {stats['success_rate']:.1f}%")
            print(f"   AI Validation Rate: {stats['ai_validation_rate']:.1f}%")
            print(f"   Recent Trades (24h): {stats['recent_trades_24h']}")
            return True
        else:
            print(f"❌ Failed to get statistics: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Statistics error: {e}")
        return False

def test_get_sessions(cookies):
    """Test getting trading sessions"""
    try:
        response = requests.get(f"{BASE_URL}/api/trading/sessions", cookies=cookies)
        
        if response.status_code == 200:
            sessions = response.json()
            print(f"\n📋 Found {len(sessions)} trading sessions")
            for session in sessions:
                print(f"   - {session['session_name']} ({session['status']})")
            return True
        else:
            print(f"❌ Failed to get sessions: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Sessions error: {e}")
        return False

def test_get_trades(cookies):
    """Test getting trades"""
    try:
        response = requests.get(f"{BASE_URL}/api/trading/trades", cookies=cookies)
        
        if response.status_code == 200:
            trades = response.json()
            print(f"\n📈 Found {len(trades)} trades")
            for trade in trades[:5]:  # Show first 5 trades
                print(f"   - {trade['symbol']} {trade['side']} ({trade['status']})")
            return True
        else:
            print(f"❌ Failed to get trades: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Trades error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting CryptoSDCA-AI Trading System Tests")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health():
        return
    
    # Test 2: Login
    cookies = test_login()
    if not cookies:
        print("❌ Cannot proceed without login")
        return
    
    # Test 3: Create trading session
    session_id = test_create_session(cookies)
    
    # Test 4: Create trade with AI validation
    trade_id = test_create_trade(cookies, session_id)
    
    # Test 5: 5-minute interval restriction
    test_5_minute_interval(cookies)
    
    # Test 6: Get statistics
    test_get_statistics(cookies)
    
    # Test 7: Get sessions
    test_get_sessions(cookies)
    
    # Test 8: Get trades
    test_get_trades(cookies)
    
    print("\n" + "=" * 50)
    print("✅ Trading system tests completed!")
    print("\nTo access the web interface:")
    print(f"   🌐 Open: {BASE_URL}/trading")
    print(f"   📊 Dashboard: {BASE_URL}/dashboard")
    print(f"   🔧 Admin: {BASE_URL}/admin")

if __name__ == "__main__":
    main()