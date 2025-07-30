"""
api/routes/auth.py - Authentication Routes for CryptoSDCA-AI
Handles user authentication, login, logout, and session management
UPDATED: Now using real database with User model
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import bcrypt
from datetime import datetime, timedelta

from src.database import get_db
from src.models.models import User

router = APIRouter()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except:
        return False

def hash_password(password: str) -> str:
    """Hash a password with bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def authenticate_user(username: str, password: str, db: Session) -> Optional[User]:
    """Authenticate user credentials against database"""
    user = db.query(User).filter_by(username=username, is_active=True).first()
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current authenticated user from session"""
    username = request.session.get("user")
    if not username:
        return None
    
    user = db.query(User).filter_by(username=username, is_active=True).first()
    return user

def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency that requires authentication"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

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
            body { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                min-height: 100vh; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .login-card { 
                backdrop-filter: blur(10px); 
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .btn-login { 
                background: linear-gradient(45deg, #667eea, #764ba2);
                border: none;
                border-radius: 10px;
                padding: 12px 0;
                font-weight: 600;
                letter-spacing: 0.5px;
                transition: all 0.3s ease;
            }
            .btn-login:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
            }
            .robot-icon { 
                font-size: 4rem; 
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: pulse 2s infinite;        
            }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            .form-control {
                border-radius: 10px;
                border: 2px solid #e9ecef;
                padding: 12px 15px;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            .form-control:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
            }
            .form-label {
                font-weight: 600;
                color: #495057;
                margin-bottom: 8px;
            }
            .alert {
                border-radius: 10px;
                border: none;
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
                                <h2 class="fw-bold mt-3" style="color: #2d3748;">CryptoSDCA-AI</h2>
                                <p class="text-muted">Advanced Trading Bot Platform</p>
                            </div>
                            
                            <form method="POST" action="/auth/login">
                                <div class="mb-3">
                                    <label for="username" class="form-label">
                                        <i class="fas fa-user me-2"></i>Username
                                    </label>
                                    <input type="text" class="form-control form-control-lg" 
                                           id="username" name="username" value="admin" 
                                           placeholder="Enter your username" required>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="password" class="form-label">
                                        <i class="fas fa-lock me-2"></i>Password
                                    </label>
                                    <input type="password" class="form-control form-control-lg" 
                                           id="password" name="password" 
                                           placeholder="Enter your password" required>
                                    <small class="form-text text-muted mt-2">
                                        <i class="fas fa-info-circle me-1"></i>Default credentials: admin / bot123
                                    </small>
                                </div>
                                
                                <div class="mb-4 form-check">
                                    <input type="checkbox" class="form-check-input" id="remember">
                                    <label class="form-check-label" for="remember">
                                        Keep me signed in
                                    </label>
                                </div>
                                
                                <button type="submit" class="btn btn-login btn-lg w-100 text-white">
                                    <i class="fas fa-sign-in-alt me-2"></i>Access Dashboard
                                </button>
                            </form>
                            
                            <div class="text-center mt-4">
                                <small class="text-muted">
                                    <i class="fas fa-shield-alt me-1"></i>
                                    Secured with Database Authentication
                                </small>
                            </div>
                            
                            <div class="text-center mt-3">
                                <small class="text-muted">
                                    <i class="fas fa-chart-line me-1"></i>
                                    Multi-Exchange AI Trading Platform
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
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process login form submission"""
    try:
        # Authenticate user against database
        user = authenticate_user(username, password, db)
        if not user:
            # Return to login with error
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login Error - CryptoSDCA-AI</title>
                <meta http-equiv="refresh" content="4;url=/auth/login">
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                <style>
                    body {{ 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        min-height: 100vh; 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    }}
                    .error-card {{
                        backdrop-filter: blur(10px); 
                        background: rgba(255, 255, 255, 0.95);
                        border-radius: 20px;
                        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
                    }}
                </style>
            </head>
            <body class="bg-light d-flex align-items-center min-vh-100">
                <div class="container">
                    <div class="row justify-content-center">
                        <div class="col-md-6">
                            <div class="card error-card border-0">
                                <div class="card-body p-5 text-center">
                                    <div class="mb-4">
                                        <i class="fas fa-exclamation-triangle text-danger" style="font-size: 4rem;"></i>
                                    </div>
                                    <h4 class="text-danger mb-3">
                                        <i class="fas fa-lock me-2"></i>Authentication Failed
                                    </h4>
                                    <div class="alert alert-danger">
                                        <strong>Invalid credentials!</strong><br>
                                        Please check your username and password.
                                    </div>
                                    <p class="text-muted mb-4">
                                        <i class="fas fa-info-circle me-1"></i>
                                        If you're using default credentials, try: <strong>admin</strong> / <strong>bot123</strong>
                                    </p>
                                    <div class="progress mb-3">
                                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                             style="width: 100%"></div>
                                    </div>
                                    <p class="text-muted">
                                        <i class="fas fa-arrow-left me-1"></i>
                                        Redirecting to login page in <span id="countdown">4</span> seconds...
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <script>
                    let countdown = 4;
                    const countdownElement = document.getElementById('countdown');
                    const timer = setInterval(() => {{
                        countdown--;
                        countdownElement.textContent = countdown;
                        if (countdown <= 0) {{
                            clearInterval(timer);
                        }}
                    }}, 1000);
                </script>
            </body>
            </html>
            """, status_code=401)
        
        # Set session with user info
        request.session["user"] = user.username
        request.session["user_id"] = user.id
        request.session["is_admin"] = user.is_admin
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
async def auth_status(request: Request, db: Session = Depends(get_db)):
    """Get authentication status"""
    user = get_current_user(request, db)
    
    return JSONResponse({
        "authenticated": user is not None,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "last_login": user.last_login.isoformat() if user.last_login else None
        } if user else None,
        "login_time": request.session.get("login_time"),
        "session_expires": "24h",
        "timestamp": datetime.utcnow().isoformat()
    })

@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Change user password"""
    
    # Verify current password
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Verify new password confirmation
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    # Validate new password strength
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters long")
    
    # Update password
    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return JSONResponse({
        "success": True,
        "message": "Password changed successfully",
        "timestamp": datetime.utcnow().isoformat()
    })

@router.post("/create-user")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(None),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create new user (admin only)"""
    
    # Only admins can create users
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Check if username already exists
    existing_user = db.query(User).filter_by(username=username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Validate password
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    
    # Create new user
    new_user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        is_admin=is_admin,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return JSONResponse({
        "success": True,
        "message": f"User '{username}' created successfully",
        "user_id": new_user.id,
        "timestamp": datetime.utcnow().isoformat()
    })

@router.get("/profile")
async def get_profile(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get current user profile"""
    
    return JSONResponse({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    })

# Export commonly used functions
__all__ = ["router", "get_current_user", "require_auth", "authenticate_user"]
