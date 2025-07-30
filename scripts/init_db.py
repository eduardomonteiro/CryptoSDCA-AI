# scripts/init_db.py
"""
scripts/init_db.py - Inicialização do banco de dados SQLite
"""
import os
import sqlite3
from pathlib import Path

def init_database():
    """Inicializa o banco de dados SQLite com tabelas básicas"""
    
    # Determinar caminho do banco
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" 
    
    # Criar diretório se não existir
    data_dir.mkdir(exist_ok=True)
    
    db_path = data_dir / "cryptosdca.sqlite3"
    
    try:
        # Conectar ao banco
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Criar tabelas básicas
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de configurações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de chaves API
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                exchange TEXT NOT NULL,
                api_key TEXT NOT NULL,
                secret_key TEXT NOT NULL,
                passphrase TEXT,
                is_sandbox BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de ordens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL,
                exchange TEXT NOT NULL,
                order_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de histórico de trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                pnl_usd REAL DEFAULT 0,
                pnl_percent REAL DEFAULT 0,
                exchange TEXT NOT NULL,
                status TEXT NOT NULL,
                ai_decision TEXT,
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inserir configurações padrão
        default_settings = [
            ('daily_profit_target', '1.0', 'Meta de lucro diário em %'),
            ('global_stop_loss', '-3.0', 'Stop loss global em %'),
            ('max_duration_hours', '72', 'Duração máxima da estratégia em horas'),
            ('min_pairs', '3', 'Número mínimo de pares simultâneos'),
            ('bot_status', 'stopped', 'Status atual do bot')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO settings (key, value, description)
            VALUES (?, ?, ?)
        ''', default_settings)
        
        # Criar usuário padrão (senha: bot123)
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, password_hash, email)
            VALUES (?, ?, ?)
        ''', ('admin', 'pbkdf2:sha256:260000$salt$hash', 'admin@cryptosdca.ai'))
        
        # Confirmar mudanças
        conn.commit()
        conn.close()
        
        print(f"✅ Banco de dados inicializado com sucesso!")
        print(f"📍 Localização: {db_path}")
        print(f"📊 Tabelas criadas: users, settings, api_keys, orders, trade_history")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco de dados: {e}")
        return False

if __name__ == "__main__":
    init_database()
