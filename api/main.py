"""
api/main.py - Main FastAPI Application Entry Point for CryptoSDCA-AI
Updated with all routers and proper configuration
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Add project root to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# Import all routers - CORRIGIDO
try:
    from api.routes.auth import router as auth_router
    from api.routes.dashboard import router as dashboard_router
    from api.routes.manager import router as manager_router  # CORREÇÃO: import direto do router
    from api.routes.trading import router as trading_router
    from api.routes.websocket import router as websocket_router
    from api.routes.admin import router as admin_router
    from api.routes.history import router as history_router
    from api.routes.settings import router as settings_router
    print("✅ All routers imported successfully")
except ImportError as e:
    print(f"❌ Error importing routers: {e}")
    # Create minimal routers as fallback
    from fastapi import APIRouter
    auth_router = APIRouter()
    dashboard_router = APIRouter()
    manager_router = APIRouter()
    trading_router = APIRouter()
    websocket_router = APIRouter()
    admin_router = APIRouter()
    history_router = APIRouter()
    settings_router = APIRouter()

# Create FastAPI application
app = FastAPI(
    title="CryptoSDCA-AI",
    description="Intelligent Crypto DCA Trading Bot with AI Validation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="cryptosdca-secret-key-change-in-production-2024"
)

# Setup templates
templates_dir = project_root / "templates"
if templates_dir.exists():
    templates = Jinja2Templates(directory=str(templates_dir))
else:
    templates = None

# Setup static files
static_dir = project_root / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Database initialization
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        # Create data directory
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        
        print("✅ CryptoSDCA-AI application started successfully!")
        print(f"📍 Project root: {project_root}")
        print(f"📁 Data directory: {data_dir}")
        print("🌐 Server running on http://127.0.0.1:8000")
        print("📖 API Documentation: http://127.0.0.1:8000/docs")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")

# Include all routers with proper prefixes - CORRIGIDO
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(manager_router, prefix="/api/manager", tags=["Manager"])  # CORREÇÃO: removido .router
app.include_router(trading_router, prefix="/api/trading", tags=["Trading"])
app.include_router(websocket_router, prefix="", tags=["WebSocket"])  # No prefix for WebSocket
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(history_router, prefix="/history", tags=["History"])
app.include_router(settings_router, prefix="/settings", tags=["Settings"])

print("✅ All routers included successfully:")
print("   - /auth/* (Authentication)")
print("   - /api/* (Dashboard)")
print("   - /api/manager/* (Manager)")
print("   - /api/trading/* (Trading)")
print("   - /admin/* (Admin)")
print("   - /history/* (History)")
print("   - /settings/* (Settings)")
print("   - /ws (WebSocket)")

# Root route - Main dashboard
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main dashboard page with authentication check"""
    
    # Check if user is authenticated
    user = request.session.get("user")
    if not user:
        # Redirect to login
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login", status_code=302)
    
    if templates:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user
        })
    else:
        # Inline dashboard HTML
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CryptoSDCA-AI Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body class="bg-light">
            <!-- Navigation -->
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
                <div class="container">
                    <a class="navbar-brand" href="/">
                        <i class="fas fa-robot me-2"></i>CryptoSDCA-AI
                    </a>
                    <div class="navbar-nav ms-auto">
                        <span class="navbar-text me-3">Welcome, {user}</span>
                        <a class="nav-link" href="/auth/logout">
                            <i class="fas fa-sign-out-alt"></i> Logout
                        </a>
                    </div>
                </div>
            </nav>

            <div class="container mt-4">
                <!-- Status Cards -->
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card bg-success text-white">
                            <div class="card-body">
                                <h5>Total Profit</h5>
                                <h3 id="total-profit">$0.00</h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-primary text-white">
                            <div class="card-body">
                                <h5>Active Orders</h5>
                                <h3 id="active-orders">0</h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-info text-white">
                            <div class="card-body">
                                <h5>Bot Status</h5>
                                <h3 id="bot-status">STOPPED</h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-warning text-white">
                            <div class="card-body">
                                <h5>AI Consensus</h5>
                                <h3 id="ai-consensus">WAITING</h3>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Control Panel -->
                <div class="row mb-4">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header d-flex justify-content-between">
                                <h5>Bot Control Panel</h5>
                                <div>
                                    <button class="btn btn-success" onclick="startBot()">
                                        <i class="fas fa-play"></i> Start Bot
                                    </button>
                                    <button class="btn btn-warning" onclick="stopBot()">
                                        <i class="fas fa-pause"></i> Stop Bot
                                    </button>
                                    <button class="btn btn-danger" onclick="emergencySell()">
                                        <i class="fas fa-exclamation-triangle"></i> Emergency Sell
                                    </button>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <a href="/api/manager/" class="btn btn-outline-primary w-100">
                                            <i class="fas fa-cog"></i> Manager Panel
                                        </a>
                                    </div>
                                    <div class="col-md-4">
                                        <a href="/api/trading/history" class="btn btn-outline-info w-100">
                                            <i class="fas fa-history"></i> Trading History
                                        </a>
                                    </div>
                                    <div class="col-md-4">
                                        <a href="/docs" class="btn btn-outline-secondary w-100">
                                            <i class="fas fa-book"></i> API Documentation
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Live Data Section -->
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-chart-line"></i> Live Trading Data</h5>
                            </div>
                            <div class="card-body">
                                <div id="websocket-status" class="alert alert-info">
                                    <i class="fas fa-spinner fa-spin"></i> Connecting to WebSocket...
                                </div>
                                <div id="live-data">
                                    <!-- Live data will be populated here -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                // WebSocket connection
                const ws = new WebSocket(`ws://${{window.location.host}}/ws`);
                
                ws.onopen = function(event) {{
                    document.getElementById('websocket-status').innerHTML = 
                        '<i class="fas fa-check-circle text-success"></i> WebSocket Connected';
                    document.getElementById('websocket-status').className = 'alert alert-success';
                }};
                
                ws.onmessage = function(event) {{
                    const data = JSON.parse(event.data);
                    console.log('WebSocket message:', data);
                    
                    if (data.type === 'portfolio_update') {{
                        updateDashboard(data.data);
                    }}
                }};
                
                ws.onerror = function(error) {{
                    document.getElementById('websocket-status').innerHTML = 
                        '<i class="fas fa-exclamation-triangle text-danger"></i> WebSocket Error';
                    document.getElementById('websocket-status').className = 'alert alert-danger';
                }};

                // Bot control functions
                function startBot() {{
                    fetch('/api/bot/start', {{ method: 'POST' }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                document.getElementById('bot-status').textContent = 'STARTING';
                                alert('Bot started successfully!');
                            }}
                        }});
                }}

                function stopBot() {{
                    fetch('/api/bot/stop', {{ method: 'POST' }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                document.getElementById('bot-status').textContent = 'STOPPED';
                                alert('Bot stopped successfully!');
                            }}
                        }});
                }}

                function emergencySell() {{
                    if (confirm('Are you sure you want to sell all positions?')) {{
                        fetch('/api/emergency-sell', {{ method: 'POST' }})
                            .then(response => response.json())
                            .then(data => {{
                                if (data.success) {{
                                    alert('Emergency sell executed!');
                                }}
                            }});
                    }}
                }}

                function updateDashboard(data) {{
                    if (data.total_profit !== undefined) {{
                        document.getElementById('total-profit').textContent = '$' + data.total_profit.toFixed(2);
                    }}
                    if (data.active_orders !== undefined) {{
                        document.getElementById('active-orders').textContent = data.active_orders;
                    }}
                }}

                // Load initial data
                fetch('/api/dashboard-data')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            updateDashboard(data.portfolio);
                        }}
                    }})
                    .catch(error => console.log('Initial data fetch error:', error));
            </script>
        </body>
        </html>
        """)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "CryptoSDCA-AI",
        "version": "1.0.0",
        "timestamp": "2024-01-28T00:00:00Z"
    })

# Add favicon handler to prevent 404 errors
@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests"""
    # Return a simple response to prevent 404 errors
    return JSONResponse({"message": "No favicon configured"}, status_code=204)

@app.get("/manager", response_class=HTMLResponse)
async def manager_page(request: Request):
    return templates.TemplateResponse("manager.html", {"request": request})

# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return JSONResponse(
        content={"detail": f"Endpoint not found: {request.url.path}"},
        status_code=404
    )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CryptoSDCA-AI server...")
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
