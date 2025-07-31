# CryptoSDCA-AI: Intelligent Multi-Layer DCA Trading Bot

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)](https://github.com/your-repo/crypto-dca-bot)

## 🚀 Overview

**CryptoSDCA-AI** is a sophisticated cryptocurrency trading bot that implements intelligent multi-layer Dollar Cost Averaging (DCA) with dual AI validation using Microsoft 365 Copilot and Perplexity API. The bot operates 24/7 across multiple exchanges with advanced risk management and real-time market sentiment analysis.

### ✨ Key Features

- **🤖 Dual AI Validation**: Microsoft 365 Copilot + Perplexity API consensus system
- **📊 Multi-Exchange Support**: Binance, KuCoin, BingX, Kraken (spot + margin)
- **💰 Intelligent DCA**: Dynamic grid recalibration based on market volatility
- **📈 Technical Indicators**: RSI, MACD, ADX, Bollinger Bands, Fibonacci levels
- **🎯 Risk Management**: Equity guard, trailing stops, slippage protection
- **📰 Sentiment Analysis**: Real-time news and Fear & Greed Index integration
- **📱 Web Dashboard**: Real-time monitoring and control interface
- **🔒 Security**: JWT authentication, API key encryption, rate limiting

## 🏗️ Architecture

```
CryptoSDCA-AI/
├── src/                    # Core application logic
│   ├── core/              # Trading engine components
│   ├── models/            # Database models
│   └── config.py          # Configuration management
├── api/                   # FastAPI routes and endpoints
│   └── routes/            # API route handlers
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, JS, and static assets
├── data/                  # SQLite database and logs
├── scripts/               # Utility scripts
├── tests/                 # Test suite
└── requirements.txt       # Python dependencies
```

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Anaconda** or **Miniconda** ([Download](https://docs.conda.io/en/latest/miniconda.html))
- **Visual Studio Code** ([Download](https://code.visualstudio.com/))
- **Git** ([Download](https://git-scm.com/))

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-repo/crypto-dca-bot.git
cd crypto-dca-bot
```

### Step 2: Create Conda Environment

```bash
# Create new conda environment
conda create -n cryptosdca python=3.11

# Activate environment
conda activate cryptosdca
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Or install with conda (recommended)
conda install --file requirements.txt
```

### Step 4: Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Application Settings
APP_NAME=CryptoSDCA-AI
APP_VERSION=1.0.0
DEBUG=true
HOST=127.0.0.1
PORT=8000

# Security
SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///./data/cryptosdca.sqlite3

# Default Admin User
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=bot123

# Trading Configuration
PAPER_TRADING=true
DEFAULT_PROFIT_TARGET=1.0
DEFAULT_STOP_LOSS=-3.0
MAX_OPERATION_DURATION_HOURS=72
MIN_PAIRS_COUNT=3

# Exchange API Keys (Optional - can be added via web interface)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
KUCOIN_API_KEY=your_kucoin_api_key
KUCOIN_SECRET_KEY=your_kucoin_secret_key
BINGX_API_KEY=your_bingx_api_key
BINGX_SECRET_KEY=your_bingx_secret_key
KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_SECRET_KEY=your_kraken_secret_key

# AI API Keys (Optional - can be added via web interface)
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
MICROSOFT_TENANT_ID=your_microsoft_tenant_id
```

### Step 5: Initialize Database

```bash
# Create data directory
mkdir -p data

# Initialize database and create tables
python -c "from src.database import init_database; import asyncio; asyncio.run(init_database())"
```

### Step 6: Run the Application

#### Development Mode (Recommended for VS Code)

```bash
# Start the development server
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

#### Production Mode

```bash
# Start production server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Step 7: Access the Application

Open your browser and navigate to:
- **Main Dashboard**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/docs

**Default Login Credentials:**
- Username: `admin`
- Password: `bot123`

## 🎯 VS Code Setup

### 1. Open Project in VS Code

```bash
code .
```

### 2. Select Python Interpreter

1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type "Python: Select Interpreter"
3. Choose the `cryptosdca` conda environment

### 3. Install VS Code Extensions

Recommended extensions for this project:

```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-python.flake8",
        "ms-python.mypy-type-checker",
        "ms-vscode.vscode-json",
        "bradlc.vscode-tailwindcss",
        "ms-vscode.vscode-typescript-next"
    ]
}
```

### 4. Configure VS Code Settings

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./env/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

## 🔧 Configuration

### Exchange Setup

1. **Access Admin Panel**: http://localhost:8000/admin
2. **Navigate to Exchanges**: Click "Exchange Management"
3. **Add Exchange**: Click "Add New Exchange"
4. **Configure API Keys**: Enter your exchange API credentials
5. **Test Connection**: Verify connectivity before saving

### AI Agents Setup

1. **Access AI Management**: http://localhost:8000/admin/ai-agents
2. **Add Copilot Agent**: Configure Microsoft 365 Copilot
3. **Add Perplexity Agent**: Configure Perplexity API
4. **Set Agent Roles**: Define specific roles for each AI agent
5. **Test Connections**: Verify AI services are accessible

### Trading Parameters

1. **Access Settings**: http://localhost:8000/settings
2. **Configure Risk Management**: Set stop-loss and profit targets
3. **Set Grid Parameters**: Configure DCA grid spacing and width
4. **Define Trading Pairs**: Select preferred cryptocurrency pairs
5. **Set Position Sizes**: Define maximum position sizes

## 📊 Usage

### Starting the Trading Bot

1. **Login**: Access http://localhost:8000 with admin credentials
2. **Configure Exchanges**: Add and verify exchange connections
3. **Set AI Agents**: Configure Copilot and Perplexity agents
4. **Start Trading**: Click "Start Bot" in the dashboard
5. **Monitor**: Watch real-time updates in the dashboard

### Dashboard Features

- **Real-time Monitoring**: Live profit/loss tracking
- **Active Orders**: Current open positions and orders
- **AI Consensus**: Real-time AI validation status
- **Emergency Controls**: Quick stop and emergency sell buttons
- **Performance Analytics**: Historical trade analysis

### Risk Management

- **Daily Loss Limits**: Automatic stop on daily loss threshold
- **Position Sizing**: Dynamic position size calculation
- **Correlation Limits**: Prevent over-exposure to correlated assets
- **Circuit Breakers**: Automatic halt on significant losses

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_trading_system.py

# Run with verbose output
pytest -v
```

### Manual Testing

```bash
# Test database connection
python -c "from src.database import check_database_connection; print(check_database_connection())"

# Test configuration
python -c "from src.config import validate_all_settings; print(validate_all_settings())"

# Test exchange connections
python scripts/test_exchanges.py
```

## 🐛 Debugging

### Enable Debug Mode

```bash
# Set debug environment variable
export DEBUG=true

# Or edit .env file
DEBUG=true
```

### View Logs

```bash
# View application logs
tail -f data/crypto_dca_bot.log

# View error logs only
grep "ERROR" data/crypto_dca_bot.log

# View AI validation logs
grep "AI" data/crypto_dca_bot.log
```

### Common Issues

#### Database Connection Issues

```bash
# Check database file permissions
ls -la data/

# Recreate database
rm data/cryptosdca.sqlite3
python -c "from src.database import init_database; import asyncio; asyncio.run(init_database())"
```

#### Exchange API Issues

```bash
# Test exchange connectivity
python scripts/test_exchanges.py

# Check API key permissions
# Ensure API keys have trading permissions enabled
```

#### AI Service Issues

```bash
# Test AI connections
python scripts/test_ai_services.py

# Check API quotas and limits
# Verify API keys are valid and have sufficient credits
```

## 📈 Performance Monitoring

### System Health

- **CPU Usage**: Monitor via dashboard
- **Memory Usage**: Real-time memory consumption
- **Database Performance**: Query response times
- **Exchange Latency**: API response times

### Trading Performance

- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Daily Returns**: Daily profit/loss tracking

## 🔒 Security

### Best Practices

1. **Change Default Password**: Update admin password immediately
2. **Use Strong API Keys**: Generate new API keys with minimal permissions
3. **Enable 2FA**: Use two-factor authentication where available
4. **Regular Updates**: Keep dependencies updated
5. **Monitor Logs**: Regularly review system logs for suspicious activity

### API Key Security

- Store API keys in environment variables
- Use read-only API keys for testing
- Enable IP whitelisting on exchanges
- Regularly rotate API keys

## 📚 API Documentation

### REST API Endpoints

- **Authentication**: `/auth/login`, `/auth/logout`
- **Dashboard**: `/dashboard`, `/api/dashboard/stats`
- **Trading**: `/api/trading/start`, `/api/trading/stop`
- **Settings**: `/api/settings`, `/api/settings/update`
- **History**: `/api/history/trades`, `/api/history/analytics`

### WebSocket Endpoints

- **Real-time Updates**: `/ws`
- **Market Data**: `/ws/market-data`
- **Trade Updates**: `/ws/trades`

### API Examples

```bash
# Get dashboard statistics
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/dashboard/stats

# Start trading bot
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/trading/start

# Get trade history
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/history/trades
```

## 🤝 Contributing

### Development Setup

```bash
# Fork the repository
git clone https://github.com/your-fork/crypto-dca-bot.git

# Create feature branch
git checkout -b feature/your-feature-name

# Install development dependencies
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Add unit tests for new features

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**Trading cryptocurrencies involves substantial risk of loss and is not suitable for all investors. The value of cryptocurrencies can go down as well as up, and you may lose some or all of your investment.**

This software is provided "as is" without warranty of any kind. The authors are not responsible for any financial losses incurred through the use of this software.

## 🆘 Support

### Getting Help

- **Documentation**: Check this README and inline code comments
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join community discussions
- **Email**: Contact support@cryptosdca.com

### Community Resources

- **Discord**: Join our Discord server
- **Telegram**: Follow our Telegram channel
- **YouTube**: Watch tutorial videos
- **Blog**: Read latest updates and strategies

---

**Made with ❤️ by the CryptoSDCA-AI Team**

*Version 1.0.0 - Last updated: December 2024*