"""
src/utils.py - Utility functions for CryptoSDCA-AI
Common utility functions used throughout the application
"""

import hashlib
import json
import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, ROUND_DOWN

import bcrypt
from loguru import logger


def generate_secure_password(length: int = 12) -> str:
    """
    Generate a secure random password
    
    Args:
        length: Length of the password
        
    Returns:
        str: Secure password
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password: Plain text password
        hashed: Hashed password
        
    Returns:
        bool: True if password matches
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure API key
    
    Args:
        length: Length of the API key
        
    Returns:
        str: Secure API key
    """
    return secrets.token_urlsafe(length)


def sanitize_symbol(symbol: str) -> str:
    """
    Sanitize a trading symbol
    
    Args:
        symbol: Raw symbol (e.g., "BTC/USDT")
        
    Returns:
        str: Sanitized symbol
    """
    # Remove spaces and convert to uppercase
    symbol = symbol.strip().upper()
    
    # Replace common separators
    symbol = re.sub(r'[_\-\s]+', '/', symbol)
    
    # Ensure proper format (BASE/QUOTE)
    if '/' not in symbol:
        # Try to split by common patterns
        if len(symbol) >= 6:
            # Common pattern: BTCUSDT -> BTC/USDT
            for i in range(3, len(symbol) - 2):
                base = symbol[:i]
                quote = symbol[i:]
                if base in ['BTC', 'ETH', 'BNB', 'ADA', 'DOT', 'LINK', 'LTC', 'BCH', 'XRP']:
                    symbol = f"{base}/{quote}"
                    break
    
    return symbol


def format_decimal(value: Union[float, Decimal, str], precision: int = 8) -> str:
    """
    Format a decimal value with specified precision
    
    Args:
        value: Value to format
        precision: Number of decimal places
        
    Returns:
        str: Formatted decimal string
    """
    if isinstance(value, str):
        value = Decimal(value)
    elif isinstance(value, float):
        value = Decimal(str(value))
    
    return str(value.quantize(Decimal('0.' + '0' * precision), rounding=ROUND_DOWN))


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        float: Percentage change
    """
    if old_value == 0:
        return 0.0
    
    return ((new_value - old_value) / old_value) * 100


def calculate_profit_loss(entry_price: float, exit_price: float, quantity: float, side: str = "buy") -> Dict[str, float]:
    """
    Calculate profit/loss for a trade
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        quantity: Trade quantity
        side: Trade side ("buy" or "sell")
        
    Returns:
        dict: P&L information
    """
    if side.lower() == "buy":
        # Long position: profit when exit > entry
        pnl = (exit_price - entry_price) * quantity
        pnl_percent = calculate_percentage_change(entry_price, exit_price)
    else:
        # Short position: profit when exit < entry
        pnl = (entry_price - exit_price) * quantity
        pnl_percent = calculate_percentage_change(exit_price, entry_price)
    
    return {
        "pnl": pnl,
        "pnl_percent": pnl_percent,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "quantity": quantity,
        "side": side
    }


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid email
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format
    
    Args:
        api_key: API key to validate
        
    Returns:
        bool: True if valid format
    """
    # Most exchange API keys are 32-64 characters alphanumeric
    pattern = r'^[a-zA-Z0-9]{32,64}$'
    return bool(re.match(pattern, api_key))


def parse_timeframe(timeframe: str) -> int:
    """
    Parse timeframe string to seconds
    
    Args:
        timeframe: Timeframe string (e.g., "1m", "1h", "1d")
        
    Returns:
        int: Timeframe in seconds
    """
    timeframe = timeframe.lower()
    
    if timeframe.endswith('m'):
        return int(timeframe[:-1]) * 60
    elif timeframe.endswith('h'):
        return int(timeframe[:-1]) * 3600
    elif timeframe.endswith('d'):
        return int(timeframe[:-1]) * 86400
    elif timeframe.endswith('w'):
        return int(timeframe[:-1]) * 604800
    else:
        raise ValueError(f"Invalid timeframe format: {timeframe}")


def format_timeframe(seconds: int) -> str:
    """
    Format seconds to timeframe string
    
    Args:
        seconds: Time in seconds
        
    Returns:
        str: Formatted timeframe
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    elif seconds < 604800:
        return f"{seconds // 86400}d"
    else:
        return f"{seconds // 604800}w"


def safe_json_loads(data: str, default: Any = None) -> Any:
    """
    Safely parse JSON string
    
    Args:
        data: JSON string
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    Safely serialize data to JSON string
    
    Args:
        data: Data to serialize
        default: Default string if serialization fails
        
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return default


def mask_sensitive_data(data: str, mask_char: str = "*") -> str:
    """
    Mask sensitive data like API keys
    
    Args:
        data: Data to mask
        mask_char: Character to use for masking
        
    Returns:
        str: Masked data
    """
    if not data or len(data) < 8:
        return mask_char * len(data) if data else ""
    
    # Show first 4 and last 4 characters
    return data[:4] + mask_char * (len(data) - 8) + data[-4:]


def format_currency(amount: float, currency: str = "USD", precision: int = 2) -> str:
    """
    Format currency amount
    
    Args:
        amount: Amount to format
        currency: Currency code
        precision: Decimal precision
        
    Returns:
        str: Formatted currency string
    """
    if currency.upper() in ["USD", "USDT", "USDC"]:
        return f"${amount:.{precision}f}"
    elif currency.upper() in ["EUR"]:
        return f"€{amount:.{precision}f}"
    elif currency.upper() in ["GBP"]:
        return f"£{amount:.{precision}f}"
    else:
        return f"{amount:.{precision}f} {currency.upper()}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def get_time_delta_human(delta: timedelta) -> str:
    """
    Get human readable time delta
    
    Args:
        delta: Time delta object
        
    Returns:
        str: Human readable time delta
    """
    total_seconds = int(delta.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}m"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours}h"
    else:
        days = total_seconds // 86400
        return f"{days}d"


def is_market_open() -> bool:
    """
    Check if crypto market is open (always true for crypto)
    
    Returns:
        bool: True (crypto markets are always open)
    """
    return True


def get_current_timestamp() -> int:
    """
    Get current timestamp in milliseconds
    
    Returns:
        int: Current timestamp in milliseconds
    """
    return int(datetime.utcnow().timestamp() * 1000)


def validate_trading_pair(pair: str) -> bool:
    """
    Validate trading pair format
    
    Args:
        pair: Trading pair to validate
        
    Returns:
        bool: True if valid format
    """
    # Basic validation: should contain exactly one "/"
    if pair.count('/') != 1:
        return False
    
    base, quote = pair.split('/')
    
    # Both base and quote should be 2-10 characters, alphanumeric
    if not (2 <= len(base) <= 10 and 2 <= len(quote) <= 10):
        return False
    
    if not (re.match(r'^[A-Z0-9]+$', base) and re.match(r'^[A-Z0-9]+$', quote)):
        return False
    
    return True


def calculate_position_size(account_balance: float, risk_percentage: float, entry_price: float) -> float:
    """
    Calculate position size based on risk percentage
    
    Args:
        account_balance: Total account balance
        risk_percentage: Risk percentage (0-100)
        entry_price: Entry price
        
    Returns:
        float: Position size in base currency
    """
    risk_amount = account_balance * (risk_percentage / 100)
    return risk_amount / entry_price


def round_to_precision(value: float, precision: int) -> float:
    """
    Round value to specified precision
    
    Args:
        value: Value to round
        precision: Number of decimal places
        
    Returns:
        float: Rounded value
    """
    factor = 10 ** precision
    return round(value * factor) / factor


# Export all utility functions
__all__ = [
    "generate_secure_password",
    "hash_password",
    "verify_password",
    "generate_api_key",
    "sanitize_symbol",
    "format_decimal",
    "calculate_percentage_change",
    "calculate_profit_loss",
    "validate_email",
    "validate_api_key_format",
    "parse_timeframe",
    "format_timeframe",
    "safe_json_loads",
    "safe_json_dumps",
    "mask_sensitive_data",
    "format_currency",
    "format_file_size",
    "get_time_delta_human",
    "is_market_open",
    "get_current_timestamp",
    "validate_trading_pair",
    "calculate_position_size",
    "round_to_precision"
]