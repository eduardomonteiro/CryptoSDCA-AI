"""
src/config.py
Application configuration using Pydantic v2 and pydantic-settings.
Supports environment variable loading, defaults, and validation.
Complete field definitions for CryptoSDCA-AI trading bot.
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configurações completas do CryptoSDCA-AI
    Inclui todos os campos necessários para evitar erros de validação
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # =====================================
    # INFORMAÇÕES DA APLICAÇÃO
    # =====================================
    app_name: str = Field("CryptoSDCA-AI", description="Nome da aplicação")
    app_version: str = Field("1.0.0", description="Versão da aplicação (env: APP_VERSION)")
    version: str = Field("1.0.0", description="Versão da aplicação (backup)")
    debug: bool = Field(True, description="Modo de debug ativo")

    # =====================================
    # CONFIGURAÇÕES DO SERVIDOR
    # =====================================
    host: str = Field("127.0.0.1", description="Host do servidor")
    port: int = Field(8000, description="Porta do servidor")
    reload: bool = Field(True, description="Auto-reload durante desenvolvimento")
    reload_on_change: bool = Field(True, description="Recarregar quando arquivos mudarem")

    # =====================================
    # SEGURANÇA E AUTENTICAÇÃO
    # =====================================
    secret_key: str = Field("cryptography-secret-key-change-in-production", description="Chave secreta para JWT")
    algorithm: str = Field("HS256", description="Algoritmo JWT")
    jwt_algorithm: str = Field("HS256", description="Algoritmo JWT (alternativo)")
    access_token_expire_minutes: int = Field(30, description="Expiração do token em minutos")
    
    # Usuário administrador padrão
    default_admin_username: str = Field("admin", description="Username do admin padrão")
    default_admin_password: str = Field("bot123", description="Senha do admin padrão")

    # =====================================
    # BANCO DE DADOS
    # =====================================
    database_url: str = Field("sqlite:///./data/cryptosdca.sqlite3", description="URL do banco principal")
    test_database_url: str = Field("sqlite:///./data/test_crypto_dca_bot.db", description="URL do banco de testes")

    # =====================================
    # CORS (AGORA COMO STRING)
    # =====================================
    cors_origins: str = Field("http://localhost:3000,http://127.0.0.1:8000", description="Origens permitidas para CORS (CSV)")

    # =====================================
    # CONFIGURAÇÕES DE TRADING
    # =====================================
    paper_trading: bool = Field(True, description="Modo paper trading (simulação)")
    test_mode: bool = Field(False, description="Modo de teste")
    default_exchange: str = Field("binance", description="Exchange padrão")
    
    # Parâmetros de trading principais
    default_profit_target: float = Field(1.0, description="Meta de lucro padrão (%)")
    default_stop_loss: float = Field(-3.0, description="Stop loss padrão (%)")
    max_operation_duration_hours: int = Field(72, description="Duração máxima da operação (horas)")
    min_pairs_count: int = Field(3, description="Número mínimo de pares simultâneos")
    
    # Moedas base (AGORA COMO STRING)
    base_currencies: str = Field("USDT,USDC,DAI", description="Moedas base aceitas (CSV)")
    max_position_size_usd: float = Field(1000.0, description="Tamanho máximo da posição (USD)")
    max_daily_loss_usd: float = Field(100.0, description="Perda máxima diária (USD)")

    # =====================================
    # GESTÃO DE RISCO
    # =====================================
    max_drawdown_percent: float = Field(5.0, description="Drawdown máximo permitido (%)")
    daily_loss_limit: float = Field(100.0, description="Limite de perda diária (USD)")
    max_portfolio_exposure: float = Field(50.0, description="Exposição máxima do portfólio (%)")
    max_daily_drawdown: float = Field(3.0, description="Drawdown máximo diário (%)")
    max_position_size: float = Field(10.0, description="Tamanho máximo da posição (%)")
    max_correlation: float = Field(0.7, description="Correlação máxima entre posições")
    var_limit: float = Field(2.0, description="Limite de Value at Risk (%)")
    volatility_limit: float = Field(30.0, description="Limite de volatilidade (%)")

    # =====================================
    # CHAVES API DAS EXCHANGES
    # =====================================
    
    # Binance
    binance_api_key: Optional[str] = Field(None, description="Chave API Binance")
    binance_secret_key: Optional[str] = Field(None, description="Chave secreta Binance")
    binance_testnet: bool = Field(False, description="Usar testnet Binance")
    
    # KuCoin
    kucoin_api_key: Optional[str] = Field(None, description="Chave API KuCoin")
    kucoin_secret_key: Optional[str] = Field(None, description="Chave secreta KuCoin")
    kucoin_passphrase: Optional[str] = Field(None, description="Passphrase KuCoin")
    kucoin_sandbox: bool = Field(False, description="Usar sandbox KuCoin")
    
    # BingX
    bingx_api_key: Optional[str] = Field(None, description="Chave API BingX")
    bingx_secret_key: Optional[str] = Field(None, description="Chave secreta BingX")
    
    # Kraken
    kraken_api_key: Optional[str] = Field(None, description="Chave API Kraken")
    kraken_secret_key: Optional[str] = Field(None, description="Chave secreta Kraken")

    # =====================================
    # CHAVES API DE IA
    # =====================================
    openai_api_key: Optional[str] = Field(None, description="Chave API OpenAI")
    perplexity_api_key: Optional[str] = Field(None, description="Chave API Perplexity")
    perplexity_model: str = Field("sonar-medium-online", description="Modelo Perplexity")
    
    # Microsoft (para Copilot)
    microsoft_client_id: Optional[str] = Field(None, description="Client ID Microsoft")
    microsoft_client_secret: Optional[str] = Field(None, description="Client Secret Microsoft")
    microsoft_tenant_id: Optional[str] = Field(None, description="Tenant ID Microsoft")
    microsoft_scope: str = Field("https://graph.microsoft.com/.default", description="Escopo Microsoft")

    # =====================================
    # INDICADORES TÉCNICOS
    # =====================================
    
    # ATR (Average True Range)
    atr_period: int = Field(14, description="Período ATR")
    atr_multiplier_min: float = Field(1.5, description="Multiplicador ATR mínimo")
    atr_multiplier_max: float = Field(2.5, description="Multiplicador ATR máximo")
    
    # RSI (Relative Strength Index)
    rsi_period: int = Field(14, description="Período RSI")
    rsi_oversold: int = Field(30, description="Nível RSI oversold")
    rsi_overbought: int = Field(70, description="Nível RSI overbought")
    rsi_oversold_volatile: int = Field(20, description="RSI oversold em mercados voláteis")
    rsi_overbought_volatile: int = Field(80, description="RSI overbought em mercados voláteis")
    
    # MACD (Moving Average Convergence Divergence)
    macd_fast_period: int = Field(12, description="Período MACD rápido")
    macd_slow_period: int = Field(26, description="Período MACD lento")
    macd_signal_period: int = Field(9, description="Período do sinal MACD")
    
    # Bollinger Bands
    bb_period: int = Field(20, description="Período Bollinger Bands")
    bb_std_dev: int = Field(2, description="Desvio padrão Bollinger Bands")
    
    # Moving Averages
    ma_short_period: int = Field(50, description="Período MA curta")
    ma_long_period: int = Field(200, description="Período MA longa")
    
    # ADX (Average Directional Index)
    adx_period: int = Field(14, description="Período ADX")
    adx_strong_trend: int = Field(25, description="Nível ADX trend forte")
    adx_weak_trend: int = Field(20, description="Nível ADX trend fraca")
    
    # Stochastic
    stoch_k_period: int = Field(14, description="Período Stochastic %K")
    stoch_d_period: int = Field(3, description="Período Stochastic %D")
    stoch_oversold: int = Field(20, description="Nível Stochastic oversold")
    stoch_overbought: int = Field(80, description="Nível Stochastic overbought")

    # =====================================
    # CONFIGURAÇÕES DE GRID TRADING
    # =====================================
    
    # Grid em mercados laterais
    grid_spacing_sideways_min: float = Field(1.0, description="Espaçamento mínimo grid lateral (%)")
    grid_spacing_sideways_max: float = Field(3.0, description="Espaçamento máximo grid lateral (%)")
    grid_width_sideways_min: float = Field(15.0, description="Largura mínima grid lateral (%)")
    grid_width_sideways_max: float = Field(25.0, description="Largura máxima grid lateral (%)")
    
    # Grid em tendências
    grid_spacing_trend_min: float = Field(2.0, description="Espaçamento mínimo grid tendência (%)")
    grid_spacing_trend_max: float = Field(5.0, description="Espaçamento máximo grid tendência (%)")
    grid_width_trend_min: float = Field(25.0, description="Largura mínima grid tendência (%)")
    grid_width_trend_max: float = Field(40.0, description="Largura máxima grid tendência (%)")

    # =====================================
    # ANÁLISE DE SENTIMENTO
    # =====================================
    fear_greed_api_url: str = Field("https://api.alternative.me/fng/", description="URL API Fear & Greed")
    cointelegraph_rss: str = Field("https://cointelegraph.com/rss", description="RSS CoinTelegraph")
    coindesk_rss: str = Field("https://www.coindesk.com/arc/outboundfeeds/rss/", description="RSS CoinDesk")
    sentiment_update_interval_minutes: int = Field(15, description="Intervalo de atualização sentimento (min)")
    
    # Keywords para análise de sentimento (AGORA COMO STRING)
    negative_keywords: str = Field("manipulation,crash,dump,scam,hack,bear,fear,panic,sell,drop", description="Palavras-chave negativas (CSV)")
    positive_keywords: str = Field("moon,bull,buy,pump,rally,surge,breakout,adoption,institutional", description="Palavras-chave positivas (CSV)")

    # =====================================
    # LOGGING E MONITORAMENTO
    # =====================================
    log_level: str = Field("INFO", description="Nível de logging")
    log_file: Optional[str] = Field("./data/crypto_dca_bot.log", description="Arquivo de log")
    log_max_size: str = Field("10MB", description="Tamanho máximo do arquivo de log")
    log_backup_count: int = Field(5, description="Número de backups de log")

    # =====================================
    # MONITORAMENTO E PROMETHEUS
    # =====================================
    enable_prometheus: bool = Field(True, description="Habilitar métricas Prometheus")
    prometheus_port: int = Field(8001, description="Porta Prometheus")
    health_check_interval_minutes: int = Field(5, description="Intervalo health check (min)")
    restart_on_failure: bool = Field(True, description="Reiniciar em caso de falha")

    # =====================================
    # VALIDADORES DE CAMPO (REMOVIDOS OS PROBLEMÁTICOS)
    # =====================================
    
    @field_validator("database_url")
    def create_database_dir(cls, v):
        """Cria diretório do banco se necessário"""
        if v.startswith("sqlite:///"):
            path = v.replace("sqlite:///", "")
            dir_ = os.path.dirname(path)
            if dir_ and not os.path.exists(dir_):
                os.makedirs(dir_, exist_ok=True)
        return v

    @field_validator("log_file")
    def create_log_dir(cls, v):
        """Cria diretório de logs se necessário"""
        if v:
            dir_ = os.path.dirname(v)
            if dir_ and not os.path.exists(dir_):
                os.makedirs(dir_, exist_ok=True)
        return v

    # =====================================
    # MÉTODOS AUXILIARES COM PARSING
    # =====================================
    
    def get_cors_origins_list(self) -> List[str]:
        """Converte cors_origins string para lista"""
        if not self.cors_origins:
            return ["http://localhost:3000", "http://127.0.0.1:8000"]
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    def get_base_currencies_list(self) -> List[str]:
        """Converte base_currencies string para lista"""
        if not self.base_currencies:
            return ["USDT", "USDC", "DAI"]
        return [x.strip() for x in self.base_currencies.split(",") if x.strip()]

    def get_negative_keywords_list(self) -> List[str]:
        """Converte negative_keywords string para lista"""
        if not self.negative_keywords:
            return ["manipulation", "crash", "dump", "scam", "hack", "bear", "fear", "panic", "sell", "drop"]
        return [x.strip() for x in self.negative_keywords.split(",") if x.strip()]

    def get_positive_keywords_list(self) -> List[str]:
        """Converte positive_keywords string para lista"""
        if not self.positive_keywords:
            return ["moon", "bull", "buy", "pump", "rally", "surge", "breakout", "adoption", "institutional"]
        return [x.strip() for x in self.positive_keywords.split(",") if x.strip()]

    def get_database_url(self) -> str:
        """Retorna URL do banco de dados"""
        return self.database_url

    def is_development(self) -> bool:
        """Verifica se está em modo de desenvolvimento"""
        return self.debug or self.test_mode

    def get_api_base_url(self) -> str:
        """Retorna URL base da API"""
        return f"http://{self.host}:{self.port}"

    def get_exchange_config(self, exchange: str) -> dict:
        """Retorna configuração de uma exchange específica"""
        configs = {
            "binance": {
                "api_key": self.binance_api_key,
                "secret": self.binance_secret_key,
                "sandbox": self.binance_testnet
            },
            "kucoin": {
                "api_key": self.kucoin_api_key,
                "secret": self.kucoin_secret_key,
                "passphrase": self.kucoin_passphrase,
                "sandbox": self.kucoin_sandbox
            },
            "bingx": {
                "api_key": self.bingx_api_key,
                "secret": self.bingx_secret_key
            },
            "kraken": {
                "api_key": self.kraken_api_key,
                "secret": self.kraken_secret_key
            }
        }
        return configs.get(exchange.lower(), {})

    def get_indicator_config(self) -> dict:
        """Retorna configuração dos indicadores técnicos"""
        return {
            "atr": {
                "period": self.atr_period,
                "multiplier_min": self.atr_multiplier_min,
                "multiplier_max": self.atr_multiplier_max
            },
            "rsi": {
                "period": self.rsi_period,
                "oversold": self.rsi_oversold,
                "overbought": self.rsi_overbought,
                "oversold_volatile": self.rsi_oversold_volatile,
                "overbought_volatile": self.rsi_overbought_volatile
            },
            "macd": {
                "fast": self.macd_fast_period,
                "slow": self.macd_slow_period,
                "signal": self.macd_signal_period
            },
            "bollinger": {
                "period": self.bb_period,
                "std_dev": self.bb_std_dev
            },
            "moving_averages": {
                "short": self.ma_short_period,
                "long": self.ma_long_period
            },
            "adx": {
                "period": self.adx_period,
                "strong_trend": self.adx_strong_trend,
                "weak_trend": self.adx_weak_trend
            },
            "stochastic": {
                "k_period": self.stoch_k_period,
                "d_period": self.stoch_d_period,
                "oversold": self.stoch_oversold,
                "overbought": self.stoch_overbought
            }
        }

    def get_grid_config(self, market_type: str = "sideways") -> dict:
        """Retorna configuração do grid trading"""
        if market_type.lower() == "trend":
            return {
                "spacing_min": self.grid_spacing_trend_min,
                "spacing_max": self.grid_spacing_trend_max,
                "width_min": self.grid_width_trend_min,
                "width_max": self.grid_width_trend_max
            }
        else:  # sideways
            return {
                "spacing_min": self.grid_spacing_sideways_min,
                "spacing_max": self.grid_spacing_sideways_max,
                "width_min": self.grid_width_sideways_min,
                "width_max": self.grid_width_sideways_max
            }

    def validate_exchange_config(self, exchange: str) -> bool:
        """Valida se a configuração de uma exchange está completa"""
        config = self.get_exchange_config(exchange)
        required_fields = ["api_key", "secret"]
        
        if exchange.lower() == "kucoin":
            required_fields.append("passphrase")
            
        return all(config.get(field) for field in required_fields)


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações
    Usa cache para evitar re-leitura desnecessária
    """
    return Settings()


# =====================================
# FUNÇÕES AUXILIARES
# =====================================

def validate_all_settings() -> bool:
    """
    Valida todas as configurações essenciais
    
    Returns:
        bool: True se todas as configurações são válidas
    """
    try:
        settings = get_settings()
        
        # Validações básicas
        assert settings.app_name, "Nome da aplicação não pode estar vazio"
        assert settings.secret_key, "Chave secreta não pode estar vazia"
        assert 1024 <= settings.port <= 65535, "Porta deve estar entre 1024 e 65535"
        
        # Validar banco de dados
        db_url = settings.get_database_url()
        assert db_url, "URL do banco de dados é obrigatória"
        
        print("✅ Todas as configurações validadas com sucesso!")
        return True
        
    except AssertionError as e:
        print(f"❌ Erro na validação: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado na validação: {e}")
        return False


def print_config_summary():
    """Imprime resumo das configurações principais"""
    settings = get_settings()
    
    print(f"""
=== RESUMO DAS CONFIGURAÇÕES CryptoSDCA-AI ===
App: {settings.app_name} v{settings.version}
Debug: {settings.debug}
Database: {settings.database_url}
Host: {settings.host}:{settings.port}
Paper Trading: {settings.paper_trading}
Test Mode: {settings.test_mode}
Default Exchange: {settings.default_exchange}
Base Currencies: {', '.join(settings.get_base_currencies_list())}
Profit Target: {settings.default_profit_target}%
Stop Loss: {settings.default_stop_loss}%
Max Duration: {settings.max_operation_duration_hours}h
=================================================
""")


if __name__ == "__main__":
    # Teste das configurações
    print("🔧 Testando configurações completas...")
    
    settings = get_settings()
    print_config_summary()
    
    # Validar configurações
    validate_all_settings()
    
    # Testar configurações de exchange
    print("\n🔑 Testando configurações de exchange...")
    for exchange in ["binance", "kucoin", "bingx", "kraken"]:
        config = settings.get_exchange_config(exchange)
        is_valid = settings.validate_exchange_config(exchange)
        print(f"{exchange.capitalize()}: {'✅ Configurado' if is_valid else '⚠️ Incompleto'}")
    
    # Testar configurações de indicadores
    print("\n📊 Configurações de indicadores:")
    indicators = settings.get_indicator_config()
    for name, config in indicators.items():
        print(f"{name.upper()}: {config}")
