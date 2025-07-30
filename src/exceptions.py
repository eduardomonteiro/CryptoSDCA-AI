"""
src/exceptions.py - Custom exceptions for CryptoSDCA-AI
Defines all custom exceptions used throughout the application
"""

from typing import Any, Dict, Optional


class CryptoBotException(Exception):
    """Base exception for all CryptoSDCA-AI errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ExchangeError(CryptoBotException):
    """Exchange-related errors"""
    
    def __init__(self, message: str, exchange: str = "unknown", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="EXCHANGE_ERROR",
            status_code=500,
            details={"exchange": exchange, **(details or {})}
        )


class AuthenticationError(CryptoBotException):
    """Authentication and authorization errors"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(CryptoBotException):
    """Authorization errors"""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details
        )


class ValidationError(CryptoBotException):
    """Data validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field, **(details or {})}
        )


class DatabaseError(CryptoBotException):
    """Database-related errors"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation, **(details or {})}
        )


class AIValidationError(CryptoBotException):
    """AI validation errors"""
    
    def __init__(self, message: str, ai_agent: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AI_VALIDATION_ERROR",
            status_code=500,
            details={"ai_agent": ai_agent, **(details or {})}
        )


class TradingError(CryptoBotException):
    """Trading operation errors"""
    
    def __init__(self, message: str, pair: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="TRADING_ERROR",
            status_code=500,
            details={"pair": pair, **(details or {})}
        )


class ConfigurationError(CryptoBotException):
    """Configuration errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details={"config_key": config_key, **(details or {})}
        )


class RateLimitError(CryptoBotException):
    """Rate limiting errors"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            status_code=429,
            details={"retry_after": retry_after, **(details or {})}
        )


class NetworkError(CryptoBotException):
    """Network-related errors"""
    
    def __init__(self, message: str, url: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            status_code=503,
            details={"url": url, **(details or {})}
        )


class InsufficientFundsError(CryptoBotException):
    """Insufficient funds errors"""
    
    def __init__(self, message: str, currency: Optional[str] = None, required: Optional[float] = None, available: Optional[float] = None):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_FUNDS",
            status_code=400,
            details={
                "currency": currency,
                "required": required,
                "available": available
            }
        )


class OrderError(CryptoBotException):
    """Order-related errors"""
    
    def __init__(self, message: str, order_id: Optional[str] = None, pair: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="ORDER_ERROR",
            status_code=500,
            details={
                "order_id": order_id,
                "pair": pair,
                **(details or {})
            }
        )


class RiskManagementError(CryptoBotException):
    """Risk management errors"""
    
    def __init__(self, message: str, risk_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RISK_MANAGEMENT_ERROR",
            status_code=500,
            details={"risk_type": risk_type, **(details or {})}
        )


class SentimentAnalysisError(CryptoBotException):
    """Sentiment analysis errors"""
    
    def __init__(self, message: str, source: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="SENTIMENT_ANALYSIS_ERROR",
            status_code=500,
            details={"source": source, **(details or {})}
        )


class IndicatorError(CryptoBotException):
    """Technical indicator errors"""
    
    def __init__(self, message: str, indicator: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="INDICATOR_ERROR",
            status_code=500,
            details={"indicator": indicator, **(details or {})}
        )


# Export all exceptions
__all__ = [
    "CryptoBotException",
    "ExchangeError",
    "AuthenticationError", 
    "AuthorizationError",
    "ValidationError",
    "DatabaseError",
    "AIValidationError",
    "TradingError",
    "ConfigurationError",
    "RateLimitError",
    "NetworkError",
    "InsufficientFundsError",
    "OrderError",
    "RiskManagementError",
    "SentimentAnalysisError",
    "IndicatorError"
]