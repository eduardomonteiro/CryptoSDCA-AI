#!/usr/bin/env python3
"""
quick_start.py - Simple startup script for CryptoSDCA-AI
This script starts the application with minimal dependencies.
"""

import os
import sys
import subprocess
from pathlib import Path

def install_minimal_deps():
    """Install minimal dependencies"""
    try:
        # Install only essential packages
        packages = [
            "fastapi",
            "uvicorn[standard]",
            "sqlalchemy",
            "pydantic",
            "pydantic-settings",
            "python-multipart",
            "jinja2",
            "loguru",
            "bcrypt",
            "python-jose[cryptography]",
            "passlib[bcrypt]",
            "ccxt",
            "httpx",
            "python-dotenv"
        ]
        
        for package in packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--break-system-packages"])
                print(f"✅ Installed {package}")
            except subprocess.CalledProcessError:
                print(f"⚠️  Failed to install {package} - continuing...")
                
    except Exception as e:
        print(f"⚠️  Dependency installation failed: {e}")
        print("Continuing with basic functionality...")

def create_data_directory():
    """Create data directory"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print("✅ Data directory created")

def create_simple_database():
    """Create a simple SQLite database"""
    try:
        import sqlite3
        
        db_path = Path("data/cryptosdca.sqlite3")
        
        # Create database with basic tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                hashed_password TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create exchanges table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchanges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                api_key TEXT NOT NULL,
                api_secret TEXT NOT NULL,
                api_passphrase TEXT,
                is_testnet BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                status TEXT DEFAULT 'disconnected',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create ai_agents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                api_key TEXT,
                api_secret TEXT,
                endpoint_url TEXT,
                model_name TEXT,
                role_description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create trading_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                total_trades INTEGER DEFAULT 0,
                successful_trades INTEGER DEFAULT 0,
                total_profit_loss REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                exchange_id INTEGER,
                session_id INTEGER,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                total_cost REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                profit_loss REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (exchange_id) REFERENCES exchanges (id),
                FOREIGN KEY (session_id) REFERENCES trading_sessions (id)
            )
        ''')
        
        # Create system_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                value_type TEXT DEFAULT 'string',
                description TEXT,
                category TEXT DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default admin user
        import bcrypt
        password_hash = bcrypt.hashpw("bot123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, email, hashed_password, is_admin, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'admin@cryptosdca.ai', password_hash, True, True))
        
        # Insert default settings
        default_settings = [
            ('paper_trading', 'true', 'bool', 'Paper trading mode', 'trading'),
            ('default_profit_target', '1.0', 'float', 'Default profit target (%)', 'trading'),
            ('default_stop_loss', '-3.0', 'float', 'Default stop loss (%)', 'trading'),
            ('max_operation_duration_hours', '72', 'int', 'Maximum operation duration (hours)', 'trading'),
            ('min_pairs_count', '3', 'int', 'Minimum simultaneous pairs', 'trading'),
        ]
        
        for key, value, value_type, description, category in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO system_settings (key, value, value_type, description, category)
                VALUES (?, ?, ?, ?, ?)
            ''', (key, value, value_type, description, category))
        
        conn.commit()
        conn.close()
        
        print("✅ Database created with default data")
        
    except Exception as e:
        print(f"❌ Database creation failed: {e}")

def start_simple_server():
    """Start a simple FastAPI server"""
    try:
        # Create a simple FastAPI app
        app_code = '''
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pathlib import Path

app = FastAPI(title="CryptoSDCA-AI", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CryptoSDCA-AI - Welcome</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-body text-center">
                            <h1 class="card-title text-primary">
                                <i class="fas fa-robot me-2"></i>CryptoSDCA-AI
                            </h1>
                            <p class="card-text">Intelligent Multi-Layer DCA Trading Bot</p>
                            
                            <div class="row mt-4">
                                <div class="col-md-6">
                                    <div class="card bg-success text-white">
                                        <div class="card-body">
                                            <h5><i class="fas fa-check-circle me-2"></i>System Ready</h5>
                                            <p>Database initialized successfully</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card bg-info text-white">
                                        <div class="card-body">
                                            <h5><i class="fas fa-user me-2"></i>Default Login</h5>
                                            <p>Username: admin<br>Password: bot123</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="mt-4">
                                <a href="/dashboard" class="btn btn-primary btn-lg me-2">
                                    <i class="fas fa-tachometer-alt me-2"></i>Go to Dashboard
                                </a>
                                <a href="/admin/exchanges" class="btn btn-outline-primary btn-lg">
                                    <i class="fas fa-exchange-alt me-2"></i>Manage Exchanges
                                </a>
                            </div>
                            
                            <div class="mt-4">
                                <h6>Quick Start Guide:</h6>
                                <ol class="text-start">
                                    <li>Add your exchange API keys in the Exchange Management</li>
                                    <li>Configure AI agents (optional)</li>
                                    <li>Start the trading bot from the Dashboard</li>
                                    <li>Monitor your trades in real-time</li>
                                </ol>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - CryptoSDCA-AI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="fas fa-robot me-2"></i>CryptoSDCA-AI
                </a>
                <div class="navbar-nav">
                    <a class="nav-link" href="/admin/exchanges">Exchanges</a>
                    <a class="nav-link" href="/admin/ai-agents">AI Agents</a>
                    <a class="nav-link" href="/admin/settings">Settings</a>
                </div>
            </div>
        </nav>
        
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-tachometer-alt me-2"></i>Trading Dashboard</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-3">
                                    <div class="card bg-success text-white">
                                        <div class="card-body text-center">
                                            <h4>Total Profit</h4>
                                            <h2>+$0.00</h2>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-primary text-white">
                                        <div class="card-body text-center">
                                            <h4>Active Orders</h4>
                                            <h2>0</h2>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-warning text-white">
                                        <div class="card-body text-center">
                                            <h4>Bot Status</h4>
                                            <h2>STOPPED</h2>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-info text-white">
                                        <div class="card-body text-center">
                                            <h4>AI Consensus</h4>
                                            <h2>READY</h2>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="mt-4">
                                <button class="btn btn-success btn-lg me-2">
                                    <i class="fas fa-play me-2"></i>Start Bot
                                </button>
                                <button class="btn btn-danger btn-lg">
                                    <i class="fas fa-exclamation-triangle me-2"></i>Emergency Sell
                                </button>
                            </div>
                            
                            <div class="mt-4">
                                <h6>Next Steps:</h6>
                                <ul>
                                    <li>Configure your exchange API keys</li>
                                    <li>Set up AI agents for validation</li>
                                    <li>Adjust trading parameters</li>
                                    <li>Start the trading bot</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

@app.get("/admin/exchanges", response_class=HTMLResponse)
async def exchanges_page(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Exchange Management - CryptoSDCA-AI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="fas fa-robot me-2"></i>CryptoSDCA-AI
                </a>
                <div class="navbar-nav">
                    <a class="nav-link" href="/dashboard">Dashboard</a>
                    <a class="nav-link active" href="/admin/exchanges">Exchanges</a>
                    <a class="nav-link" href="/admin/ai-agents">AI Agents</a>
                </div>
            </div>
        </nav>
        
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-12">
                    <h1><i class="fas fa-exchange-alt me-2"></i>Exchange Management</h1>
                    
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-plus me-2"></i>Add New Exchange</h5>
                        </div>
                        <div class="card-body">
                            <form id="addExchangeForm">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">Exchange</label>
                                            <select class="form-select" name="name" required>
                                                <option value="">Select Exchange</option>
                                                <option value="binance">Binance</option>
                                                <option value="kucoin">KuCoin</option>
                                                <option value="bingx">BingX</option>
                                                <option value="kraken">Kraken</option>
                                            </select>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">Display Name</label>
                                            <input type="text" class="form-control" name="display_name" required>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">API Key</label>
                                            <input type="text" class="form-control" name="api_key" required>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">API Secret</label>
                                            <input type="password" class="form-control" name="api_secret" required>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">API Passphrase (KuCoin only)</label>
                                            <input type="password" class="form-control" name="api_passphrase">
                                        </div>
                                        <div class="mb-3">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="is_testnet" id="isTestnet">
                                                <label class="form-check-label" for="isTestnet">
                                                    Use Testnet/Sandbox
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save me-2"></i>Add Exchange
                                </button>
                            </form>
                        </div>
                    </div>
                    
                    <div class="card mt-4">
                        <div class="card-header">
                            <h5><i class="fas fa-list me-2"></i>Configured Exchanges</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted text-center">No exchanges configured yet</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            document.getElementById('addExchangeForm').addEventListener('submit', function(e) {
                e.preventDefault();
                alert('Exchange management functionality will be available in the full version!');
            });
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
'''
        
        # Write the app code to a temporary file
        with open("simple_app.py", "w") as f:
            f.write(app_code)
        
        # Start the server
        print("🚀 Starting CryptoSDCA-AI server...")
        print("🌐 Access the application at: http://127.0.0.1:8000")
        print("👤 Default login: admin / bot123")
        print("=" * 60)
        
        subprocess.run([sys.executable, "simple_app.py"])
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def main():
    """Main function"""
    print("=" * 60)
    print("🤖 CryptoSDCA-AI Trading Bot - Quick Start")
    print("=" * 60)
    
    try:
        # Install minimal dependencies
        print("📦 Installing minimal dependencies...")
        install_minimal_deps()
        
        # Create data directory
        print("📁 Creating data directory...")
        create_data_directory()
        
        # Create database
        print("🗄️ Creating database...")
        create_simple_database()
        
        # Start server
        print("🎉 Starting application...")
        start_simple_server()
        
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Application failed to start: {e}")

if __name__ == "__main__":
    main()