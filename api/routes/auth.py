"""
api/routes/auth.py - Authentication Routes for CryptoSDCA-AI
Handles user authentication, login, logout, and session management
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import bcrypt
from datetime import datetime, timedelta

router = APIRouter()

# Mock user database - replace with actual database
mock_users = {
    "admin": {
        "username": "admin",
        "password_hash": "$2b$12$/zJONr0IniCrOWjvHiDSGOyOoUuojFx/CaYr3HQPult7x8FjLy9ai",  # bot123
        "email": "admin@cryptosdca.ai",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00"
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except:
        return False

def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user credentials"""
    user = mock_users.get(username)
    if not user:
        return None
    
    if not verify_password(password, user["password_hash"]):
        return None
    
    return user

def get_current_user(request: Request) -> Optional[dict]:
    """Get current authenticated user from session"""
    username = request.session.get("user")
    if not username:
        return None
    return mock_users.get(username)

@router.get("/login")
async def login_page(request: Request):
    """Display login page"""
    # Check if user is already logged in
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - CryptoSDCA-AI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .login-card { 
                backdrop-filter: blur(10px); 
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            }
            .btn-login { 
                background: linear-gradient(45deg, #667eea, #764ba2);
                border: none;
            }
            .robot-icon { 
                font-size: 4rem; 
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;        
            }
        </style>
    </head>
    <body class="d-flex align-items-center">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-4">
                    <div class="card login-card border-0">
                        <div class="card-body p-5">
                            <div class="text-center mb-4">
                                <i class="fas fa-robot robot-icon"></i>
                                <h2 class="fw-bold mt-3">CryptoSDCA-AI</h2>
                                <p class="text-muted">Secure Trading Bot Access</p>
                            </div>
                            
                            <form method="POST" action="/auth/login">
                                <div class="mb-3">
                                    <label for="username" class="form-label">
                                        <i class="fas fa-user me-2"></i>Username
                                    </label>
                                    <input type="text" class="form-control form-control-lg" 
                                           id="username" name="username" value="admin" 
                                           placeholder="Enter username" required>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="password" class="form-label">
                                        <i class="fas fa-lock me-2"></i>Password
                                    </label>
                                    <input type="password" class="form-control form-control-lg" 
                                           id="password" name="password" 
                                           placeholder="Enter password" required>
                                    <small class="form-text text-muted">Default: bot123</small>
                                </div>
                                
                                <div class="mb-3 form-check">
                                    <input type="checkbox" class="form-check-input" id="remember">
                                    <label class="form-check-label" for="remember">
                                        Remember me
                                    </label>
                                </div>
                                
                                <button type="submit" class="btn btn-login btn-lg w-100 text-white">
                                    <i class="fas fa-sign-in-alt me-2"></i>Login
                                </button>
                            </form>
                            
                            <div class="text-center mt-4">
                                <small class="text-muted">
                                    <i class="fas fa-shield-alt me-1"></i>
                                    Secured with Session Authentication
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@router.post("/login")
async def login_process(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Process login form submission"""
    try:
        # Authenticate user
        user = authenticate_user(username, password)
        if not user:
            # Return to login with error
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login Error</title>
                <meta http-equiv="refresh" content="3;url=/auth/login">
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light d-flex align-items-center min-vh-100">
                <div class="container">
                    <div class="row justify-content-center">
                        <div class="col-md-6">
                            <div class="alert alert-danger text-center">
                                <h4><i class="fas fa-exclamation-triangle"></i> Login Failed</h4>
                                <p>Invalid username or password.</p>
                                <p>Redirecting to login page in 3 seconds...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """, status_code=401)
        
        # Set session
        request.session["user"] = user["username"]
        request.session["login_time"] = datetime.utcnow().isoformat()
        
        # Redirect to dashboard
        return RedirectResponse(url="/", status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@router.get("/logout")
async def logout(request: Request):
    """Logout user and clear session"""
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=302)

@router.get("/status")
async def auth_status(request: Request):
    """Get authentication status"""
    user = get_current_user(request)
    
    return JSONResponse({
        "authenticated": user is not None,
        "user": user["username"] if user else None,
        "login_time": request.session.get("login_time"),
        "timestamp": datetime.utcnow().isoformat()
    })

@router.post("/register")
async def register_user(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    confirm_password: str = Form(...)
):
    """Register new user (disabled by default for security)"""
    # In production, you might want to disable registration or add admin approval
    raise HTTPException(
        status_code=403, 
        detail="User registration is disabled. Contact administrator."
    )

# Authentication dependency
def require_auth(request: Request):
    """Dependency to require authentication"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user
