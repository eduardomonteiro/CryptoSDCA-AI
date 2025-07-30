
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
