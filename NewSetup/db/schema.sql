-- NewSetup database schema (playbook 2.4, SQLite development)
-- Stores signals, trades, events and per-inefficiency quality metrics.

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME NOT NULL,
    headline TEXT NOT NULL,
    themes TEXT,               -- JSON array
    goldstein_score REAL,
    relevance_score REAL,
    source TEXT
);

CREATE TABLE IF NOT EXISTS inefficiencies (
    id INTEGER PRIMARY KEY,    -- 1..40
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    concentration TEXT,
    trade_type TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME NOT NULL,
    inefficiency_id INTEGER NOT NULL REFERENCES inefficiencies(id),
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    trigger_type TEXT,
    trigger_description TEXT,
    layer1_confidence REAL,
    confirmed INTEGER,          -- 0/1
    layer2_score REAL,
    lot_size REAL,
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    sector TEXT,
    status TEXT DEFAULT 'emitted'   -- emitted | filled | rejected | expired
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opened_at DATETIME NOT NULL,
    closed_at DATETIME,
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,
    lot_size REAL NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    stop_loss REAL,
    take_profit REAL,
    pnl REAL,
    exit_reason TEXT,
    inefficiency_id INTEGER,
    sector TEXT
);

CREATE TABLE IF NOT EXISTS signal_quality (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,        -- YYYY-MM
    inefficiency_id INTEGER NOT NULL,
    signals_fired INTEGER DEFAULT 0,
    signals_confirmed INTEGER DEFAULT 0,
    trades_taken INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    gross_pnl REAL DEFAULT 0,
    UNIQUE (month, inefficiency_id)
);

CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(ts);
CREATE INDEX IF NOT EXISTS idx_trades_opened ON trades(opened_at);
