# 🏗️ SUPPLY CHAIN INEFFICIENCY TRADING PLAYBOOK

## Complete Implementation Plan — Pepperstone MT5

> **Version:** 1.0 | **Created:** 2026-11-15 | **Status:** Implementation Ready
> **Broker:** Pepperstone (Razor Account, MT5) | **Capital Plan:** $5K → $15K → $50K
> **Universe:** 40 Supply Chain Inefficiencies → Forex, Commodity CFD, ETF CFD, Equity CFD

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Phase 0: Infrastructure Setup](#2-phase-0-infrastructure-setup)
3. [Phase 1: Instrument Mapping](#3-phase-1-instrument-mapping)
4. [Phase 2: Signal Engine Development](#4-phase-2-signal-engine-development)
5. [Phase 3: Backtesting](#5-phase-3-backtesting)
6. [Phase 4: Paper Trading](#6-phase-4-paper-trading)
7. [Phase 5: Live Deployment](#7-phase-5-live-deployment)
8. [Continuous: Monitoring](#8-continuous-monitoring)
9. [Continuous: Testing & Evaluation](#9-continuous-testing--evaluation)
10. [Continuous: Optimization](#10-continuous-optimization)
11. [Appendix A: All 40 Inefficiency Trade Cards](#appendix-a-all-40-inefficiency-trade-cards)
12. [Appendix B: Forex Strategy Playbook](#appendix-b-forex-strategy-playbook)
13. [Appendix C: Event Response Playbook](#appendix-c-event-response-playbook)
14. [Appendix D: Risk Management Rules](#appendix-d-risk-management-rules)

---

# 1. EXECUTIVE SUMMARY

## The Thesis

Global supply chains contain **40 identified structural inefficiencies** — concentration risks, geographic chokepoints, and monopolistic bottlenecks — that create predictable, tradeable price dislocations when disrupted. This playbook systematically exploits those dislocations across forex, commodity, ETF, and equity markets via Pepperstone MT5.

## The Edge

| Dimension | Detail |
|-----------|--------|
| **Alpha Source** | Structural supply chain concentration (not priced until disruption) |
| **Signal Latency** | GDELT/FinBERT detect events 2-12 hours before market pricing |
| **Universe** | 40 inefficiencies → 120+ tradeable instruments on Pepperstone |
| **Correlation** | Low correlation to traditional trend-following / mean-reversion |
| **Capacity** | Unlimited at retail scale (all liquid FX/CFD markets) |

## Target Performance

| Model | Annual Return | Max Drawdown | Sharpe Ratio | Win Rate |
|-------|-------------|-------------|-------------|----------|
| Conservative | 12-18% | ≤8% | >1.2 | >55% |
| Moderate | 20-35% | ≤12% | >1.5 | >52% |
| Aggressive | 40-80% / 18mo | ≤18% | >1.0 | >48% |

## Capital Deployment Timeline

```
Month 1-2:  Phase 0-1  │ Infrastructure + Mapping         │ $0 at risk
Month 3-4:  Phase 2-3  │ Signal Engine + Backtesting       │ $0 at risk
Month 5:    Phase 4    │ Paper Trading (4 weeks)           │ $0 at risk
Month 6-7:  Phase 5A   │ Live Micro ($5K, 0.01 lots)      │ $5K at risk
Month 8-9:  Phase 5B   │ Live Mini ($15K, 0.1 lots)       │ $15K at risk
Month 10+:  Phase 5C   │ Live Standard ($50K, 1.0 lots)   │ $50K at risk
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│  GDELT │ FinBERT │ Quandl │ FRED │ USGS │ MarineTraffic    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 SIGNAL ENGINE (Python)                        │
│  Layer 1: Inefficiency Scanner (40 monitors)                 │
│  Layer 2: Confirmation Engine (TA + Fundamental + Sentiment) │
│  Layer 3: Portfolio Manager (Sizing + Correlation + Risk)    │
└──────────────────────┬──────────────────────────────────────┘
                       │ Signals via file/socket
┌──────────────────────▼──────────────────────────────────────┐
│              EXECUTION ENGINE (MQL5 EA on MT5)               │
│  Order Management │ Position Tracking │ Risk Enforcement     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              MONITORING (Grafana + Alerts)                    │
│  P&L Dashboard │ Signal Quality │ Risk Metrics │ News Feed   │
└─────────────────────────────────────────────────────────────┘
```

## 3-Layer Signal System

- **Layer 1 — Inefficiency Scanner:** Monitors supply data, news events, price triggers for all 40 inefficiencies. Fires raw signals.
- **Layer 2 — Confirmation Engine:** Validates Layer 1 signals against technicals (RSI, MACD, Bollinger), fundamentals (inventory, spreads), and sentiment (FinBERT score).
- **Layer 3 — Portfolio Manager:** Sizes positions using Kelly criterion, enforces correlation limits (<0.7), sector caps (15%), and max positions (8-10).

---

# 2. PHASE 0: INFRASTRUCTURE SETUP

## 2.1 Pepperstone Razor MT5 Account Setup

### Account Specifications

| Parameter | Value |
|-----------|-------|
| Account Type | Razor (Raw Spread) |
| Platform | MetaTrader 5 |
| Base Currency | USD |
| Leverage | 1:30 (EU) or 1:500 (non-EU) |
| Commission | $3.50 per lot per side ($7 round trip) |
| Minimum Deposit | $200 |
| Execution | ECN / No Dealing Desk |

### Setup Checklist

- [ ] Open Pepperstone account at [pepperstone.com](https://pepperstone.com)
- [ ] Select Razor account type
- [ ] Select MT5 platform
- [ ] Complete KYC/AML verification
- [ ] Download and install MT5 desktop terminal
- [ ] Enable "Algo Trading" in MT5 → Tools → Options → Expert Advisors
- [ ] Enable all DLL imports for Python bridge
- [ ] Create demo account first for paper trading phase
- [ ] Fund live account ($5K minimum for Phase 5A)
- [ ] Verify all 40+ required instruments are visible in Market Watch

### Required MT5 Settings

```
Tools → Options → Expert Advisors:
  ☑ Allow algorithmic trading
  ☑ Allow DLL imports
  ☑ Allow import of external experts

Tools → Options → Charts:
  Max bars in chart: Unlimited
  Max bars in window: 100000
```

## 2.2 Python-MT5 Bridge Setup

### Environment Setup

```bash
# Create project virtual environment
python -m venv venv_sci_trade
source venv_sci_trade/Scripts/activate  # Windows Git Bash

# Core packages
pip install MetaTrader5==5.0.45
pip install pandas numpy scipy scikit-learn
pip install sqlalchemy psycopg2-binary
pip install transformers torch  # FinBERT
pip install requests schedule apscheduler
pip install python-dotenv loguru
pip install plotly dash  # dashboards
pip install pytest pytest-cov  # testing

# Data packages
pip install gdeltdoc  # GDELT API
pip install nasdaq-data-link  # Quandl replacement
pip install fredapi  # FRED
pip install feedparser  # RSS monitoring
pip install beautifulsoup4 lxml  # web scraping
```

### MT5 Connection Test

```python
# mt5_connection_test.py
import MetaTrader5 as mt5
from loguru import logger

def test_connection():
    """Verify MT5 connection and available instruments."""
    if not mt5.initialize():
        logger.error(f"MT5 init failed: {mt5.last_error()}")
        return False

    account = mt5.account_info()
    logger.info(f"Connected: {account.login} | Balance: ${account.balance}")
    logger.info(f"Server: {account.server} | Leverage: 1:{account.leverage}")

    # Check critical instruments
    required = [
        "AUDUSD", "USDCAD", "USDNOK", "USDCNH", "USDJPY",
        "COPPER", "COCOA", "XAUUSD",
        "FCX.US", "TSM.US", "CCJ.US",  # Equity CFDs
        # ETF CFDs (Pepperstone symbols may vary)
    ]
    missing = []
    for sym in required:
        info = mt5.symbol_info(sym)
        if info is None:
            missing.append(sym)
        else:
            logger.info(f"  ✓ {sym}: spread={info.spread}, digits={info.digits}")

    if missing:
        logger.warning(f"Missing symbols: {missing}")

    mt5.shutdown()
    return len(missing) == 0

if __name__ == "__main__":
    test_connection()
```

## 2.3 Data Pipeline Setup

### Data Source Configuration

| Source | Type | Cost | Frequency | Data |
|--------|------|------|-----------|------|
| GDELT | REST API | Free | 15 min | Geopolitical events, disruption signals |
| FinBERT | Local model | Free | On-demand | News sentiment (-1 to +1) |
| Nasdaq Data Link (Quandl) | REST API | Freemium | Daily | Commodity stocks, futures, prices |
| FRED | REST API | Free | Daily | Macro indicators, rates, USD index |
| USGS | Web scrape | Free | Monthly | Mineral production, trade flows |
| MarineTraffic | API | $49/mo | Hourly | Vessel tracking, port congestion |
| RSS Feeds | feedparser | Free | 15 min | Mining.com, Reuters commodities |

### API Key Configuration

```python
# .env (NEVER commit to git)
FRED_API_KEY=your_key_here
QUANDL_API_KEY=your_key_here
GDELT_API_KEY=  # no key needed
MARINE_TRAFFIC_API_KEY=your_key_here
MT5_LOGIN=your_login
MT5_PASSWORD=your_password
MT5_SERVER=Pepperstone-MT5-Live
```

### GDELT Pipeline

```python
# data/gdelt_monitor.py
from gdeltdoc import GdeltDoc, Filters
import pandas as pd
from datetime import datetime, timedelta

class GDELTMonitor:
    """Monitor GDELT for supply chain disruption events."""

    SUPPLY_CHAIN_THEMES = {
        "mining_disruption": ["MINING", "MINE_ACCIDENT", "MINE_CLOSURE"],
        "shipping_disruption": ["MARITIME", "CANAL", "PORT_CLOSURE", "PIRACY"],
        "trade_war": ["TRADE_WAR", "SANCTION", "EXPORT_BAN", "TARIFF"],
        "geopolitical": ["MILITARY", "CONFLICT", "BLOCKADE", "COUP"],
        "natural_disaster": ["EARTHQUAKE", "FLOOD", "DROUGHT", "HURRICANE"],
        "energy_crisis": ["ENERGY_CRISIS", "POWER_OUTAGE", "OIL_SHOCK"],
    }

    COUNTRY_WATCHLIST = {
        "CN": "China (rare earths, gallium, germanium, antimony)",
        "CD": "DRC (cobalt, copper)",
        "CL": "Chile (copper, lithium)",
        "AU": "Australia (iron ore, bauxite, rare earths)",
        "TW": "Taiwan (semiconductors)",
        "PA": "Panama (canal)",
        "YE": "Yemen (Red Sea)",
        "RU": "Russia (titanium, palladium, wheat)",
        "UA": "Ukraine (neon gas, wheat)",
        "PE": "Peru (copper, fishmeal)",
        "ID": "Indonesia (nickel, palm oil)",
        "MG": "Madagascar (vanilla)",
    }

    def scan(self, lookback_hours: int = 24) -> pd.DataFrame:
        gd = GdeltDoc()
        start = datetime.now() - timedelta(hours=lookback_hours)

        all_articles = []
        for theme_group, themes in self.SUPPLY_CHAIN_THEMES.items():
            for theme in themes:
                f = Filters(
                    keyword=theme,
                    start_date=start.strftime("%Y-%m-%d"),
                    end_date=datetime.now().strftime("%Y-%m-%d"),
                )
                try:
                    articles = gd.article_search(f)
                    if not articles.empty:
                        articles["theme_group"] = theme_group
                        articles["theme"] = theme
                        all_articles.append(articles)
                except Exception:
                    pass

        if all_articles:
            df = pd.concat(all_articles, ignore_index=True)
            return df.sort_values("seendate", ascending=False)
        return pd.DataFrame()
```

### FinBERT Sentiment Pipeline

```python
# data/sentiment.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np

class FinBERTSentiment:
    """Analyze financial news sentiment using FinBERT."""

    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        self.labels = ["positive", "negative", "neutral"]

    def analyze(self, text: str) -> dict:
        inputs = self.tokenizer(text, return_tensors="pt",
                                truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        probs = probs.numpy()[0]

        return {
            "sentiment": self.labels[np.argmax(probs)],
            "score": float(np.max(probs)),
            "positive": float(probs[0]),
            "negative": float(probs[1]),
            "neutral": float(probs[2]),
            "composite": float(probs[0] - probs[1]),  # -1 to +1
        }

    def analyze_batch(self, texts: list[str]) -> list[dict]:
        return [self.analyze(t) for t in texts]
```

## 2.4 Database Setup

### SQLite Schema (Development)

```sql
-- signals.db

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    inefficiency_id INTEGER NOT NULL,
    inefficiency_name TEXT NOT NULL,
    layer INTEGER NOT NULL,  -- 1=scanner, 2=confirmed, 3=sized
    signal_type TEXT NOT NULL,  -- BUY, SELL, CLOSE
    instrument TEXT NOT NULL,
    confidence REAL NOT NULL,  -- 0.0-1.0
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    position_size REAL,
    metadata TEXT,  -- JSON blob for extra data
    status TEXT DEFAULT 'PENDING'  -- PENDING, EXECUTED, EXPIRED, REJECTED
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER REFERENCES signals(id),
    ticket INTEGER,  -- MT5 ticket number
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,  -- BUY, SELL
    open_time TEXT NOT NULL,
    close_time TEXT,
    open_price REAL NOT NULL,
    close_price REAL,
    volume REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    commission REAL,
    swap REAL,
    profit REAL,
    pips REAL,
    status TEXT DEFAULT 'OPEN',  -- OPEN, CLOSED, CANCELLED
    inefficiency_id INTEGER,
    strategy_name TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS daily_metrics (
    date TEXT PRIMARY KEY,
    equity REAL NOT NULL,
    balance REAL NOT NULL,
    open_positions INTEGER,
    daily_pnl REAL,
    daily_return_pct REAL,
    max_drawdown_pct REAL,
    sharpe_rolling_30d REAL,
    win_rate_rolling_30d REAL,
    signals_generated INTEGER,
    signals_executed INTEGER,
    signals_rejected INTEGER
);

CREATE TABLE IF NOT EXISTS inefficiency_status (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- ENERGY_MINING, FOOD_SHIPPING, TECH_INFRA
    alert_level TEXT DEFAULT 'GREEN',  -- GREEN, YELLOW, ORANGE, RED
    last_trigger_date TEXT,
    trigger_count_30d INTEGER DEFAULT 0,
    last_sentiment_score REAL,
    notes TEXT,
    updated_at TEXT
);

CREATE INDEX idx_signals_timestamp ON signals(timestamp);
CREATE INDEX idx_signals_inefficiency ON signals(inefficiency_id);
CREATE INDEX idx_trades_instrument ON trades(instrument);
CREATE INDEX idx_trades_status ON trades(status);
```

### PostgreSQL Schema (Production)

Same schema as above with these additions:

```sql
-- Add partitioning for trades table (by month)
CREATE TABLE trades (
    -- ... same columns ...
) PARTITION BY RANGE (open_time);

-- Add materialized views for dashboard
CREATE MATERIALIZED VIEW mv_strategy_performance AS
SELECT
    strategy_name,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(profit)::numeric, 2) as avg_profit,
    ROUND(SUM(profit)::numeric, 2) as total_profit,
    ROUND(MAX(profit)::numeric, 2) as best_trade,
    ROUND(MIN(profit)::numeric, 2) as worst_trade
FROM trades
WHERE status = 'CLOSED'
GROUP BY strategy_name;
```

## 2.5 Grafana Dashboard Setup

### Dashboard Panels

| Panel | Type | Data Source | Refresh |
|-------|------|-------------|---------|
| Equity Curve | Time series | PostgreSQL | 1 min |
| Open Positions | Table | MT5 API → DB | 30 sec |
| Daily P&L | Bar chart | PostgreSQL | 5 min |
| Drawdown | Gauge | PostgreSQL | 1 min |
| Signal Pipeline | Stat | PostgreSQL | 1 min |
| Inefficiency Heat Map | Heatmap | PostgreSQL | 15 min |
| News Feed | Logs | GDELT → DB | 5 min |
| Sentiment Score | Time series | FinBERT → DB | 15 min |
| Correlation Matrix | Heatmap | Python calc → DB | 1 hour |
| Risk Utilization | Gauge | PostgreSQL | 1 min |

### Alert Rules

```yaml
# grafana_alerts.yaml
alerts:
  - name: max_drawdown_breach
    condition: daily_metrics.max_drawdown_pct > 10
    severity: critical
    action: close_all_positions
    notify: [email, telegram]

  - name: single_position_overlimit
    condition: any position > 5% of equity
    severity: high
    action: reduce_position
    notify: [telegram]

  - name: high_correlation_detected
    condition: correlation_matrix > 0.7 between open positions
    severity: medium
    action: flag_for_review
    notify: [telegram]

  - name: supply_chain_event_detected
    condition: gdelt_alert_score > 0.8
    severity: info
    action: queue_signal_check
    notify: [telegram]

  - name: daily_var_breach
    condition: daily_var > 2%
    severity: high
    action: no_new_positions
    notify: [email, telegram]
```

## 2.6 Directory Structure

```
C:\Users\I022583\SCI_Trade\
│
├── config\
│   ├── .env                          # API keys (git-ignored)
│   ├── settings.yaml                 # Strategy parameters
│   ├── instruments.yaml              # Pepperstone instrument map
│   └── inefficiencies.yaml           # 40 inefficiency definitions
│
├── data\
│   ├── __init__.py
│   ├── gdelt_monitor.py              # GDELT event scanner
│   ├── sentiment.py                  # FinBERT pipeline
│   ├── quandl_fetcher.py             # Commodity data
│   ├── fred_fetcher.py               # Macro indicators
│   ├── usgs_scraper.py               # Mineral production data
│   ├── marine_traffic.py             # Shipping/vessel data
│   └── rss_monitor.py                # News RSS feeds
│
├── signals\
│   ├── __init__.py
│   ├── layer1_scanner.py             # Inefficiency trigger scanner
│   ├── layer2_confirmation.py        # TA + fundamental + sentiment
│   ├── layer3_portfolio.py           # Position sizing + risk
│   └── signal_bus.py                 # Signal routing & logging
│
├── execution\
│   ├── __init__.py
│   ├── mt5_bridge.py                 # MetaTrader5 API wrapper
│   ├── order_manager.py              # Order lifecycle
│   └── risk_enforcer.py              # Hard limit checks
│
├── mql5\
│   ├── Experts\
│   │   ├── SCI_Main_EA.mq5           # Main Expert Advisor
│   │   └── SCI_Signal_Reader.mq5     # Reads Python signals
│   ├── Include\
│   │   ├── SCI_RiskManager.mqh       # Risk management module
│   │   └── SCI_SignalParser.mqh       # Signal file parser
│   └── Scripts\
│       └── SCI_InstrumentCheck.mq5   # Instrument availability test
│
├── backtest\
│   ├── __init__.py
│   ├── runner.py                      # Backtest orchestrator
│   ├── analyzer.py                    # Results analysis
│   ├── walk_forward.py                # Walk-forward optimizer
│   └── results\                       # Saved backtest reports
│
├── monitoring\
│   ├── __init__.py
│   ├── dashboard.py                   # Plotly/Dash dashboard
│   ├── alerter.py                     # Telegram/email alerts
│   ├── daily_report.py                # Daily P&L report
│   └── grafana\
│       └── dashboards\                # Grafana JSON exports
│
├── db\
│   ├── signals.db                     # SQLite (dev)
│   ├── schema.sql                     # Database schema
│   └── migrations\                    # Alembic migrations
│
├── tests\
│   ├── test_signals.py
│   ├── test_execution.py
│   ├── test_risk.py
│   └── test_data.py
│
├── logs\
│   ├── signals.log
│   ├── trades.log
│   └── errors.log
│
├── notebooks\
│   ├── 01_data_exploration.ipynb
│   ├── 02_signal_development.ipynb
│   ├── 03_backtest_analysis.ipynb
│   └── 04_correlation_study.ipynb
│
├── main.py                            # Main entry point
├── scheduler.py                       # APScheduler job definitions
├── requirements.txt
├── pytest.ini
└── README.md
```

---

# 3. PHASE 1: INSTRUMENT MAPPING

## 3.1 Master Instrument Map — All 40 Inefficiencies

### ENERGY / MINING (12 Inefficiencies)

| # | Inefficiency | Concentration | Direct CFD | Forex Proxy | ETF Proxy | Equity Proxy | Trade Type |
|---|-------------|--------------|------------|-------------|-----------|-------------|------------|
| 1 | **Helium** | US 40%, Qatar 25% | — | USD/QAR ✗ | — | `LIN.US` ✓, `APD.US` ✓ | Equity CFD |
| 2 | **Antimony** | China 48% | — | `USDCNH` ✓ | `REMX.US` ✓ | — | Forex + ETF |
| 3 | **Gallium/Germanium** | China 80%/60% | — | `USDCNH` ✓ | `REMX.US` ✓, `SOXX.US` ✓ | `INTC.US` ✓ | Multi-instrument |
| 4 | **Graphite** | China 65% | — | `USDCNH` ✓, `AUDUSD` ✓ | — | `SYA.AU` ✗ | Forex |
| 5 | **Manganese** | S.Africa 28%, Gabon 23% | — | `USDZAR` ✓ | — | `BHP.US` ✓ | Forex + Equity |
| 6 | **Fluorspar** | China 64% | — | `USDCNH` ✓ | — | `VALE.US` ✓ | Forex + Equity |
| 7 | **Phosphate Rock** | Morocco 70% (reserves) | — | `USDMAD` ✗ | `MOS.US` ✓ (ETF proxy) | `MOS.US` ✓, `NTR.US` ✓ | Equity CFD |
| 8 | **Rare Earth Refining** | China 90% | — | `USDCNH` ✓, `AUDUSD` ✓ | `REMX.US` ✓ | `MP.US` ✓ | Multi-instrument |
| 9 | **Cobalt** | DRC 74% | `COPPER` ✓ (proxy) | `USDCNH` ✓ | — | `GLEN.UK` ✗ | Forex + Commodity |
| 10 | **Uranium Enrichment** | Russia 35-40% | — | `USDCAD` ✓ | `URA.US` ✓ | `CCJ.US` ✓ | Multi-instrument |
| 11 | **Titanium Sponge** | China 55%, Japan 19% | — | `USDCNH` ✓, `USDJPY` ✓ | — | `TKR.UK` ✗ | Forex |
| 12 | **Magnesium** | China 87% | — | `USDCNH` ✓ | — | `VALE.US` ✓ | Forex + Equity |

### FOOD / SHIPPING (14 Inefficiencies)

| # | Inefficiency | Concentration | Direct CFD | Forex Proxy | ETF Proxy | Equity Proxy | Trade Type |
|---|-------------|--------------|------------|-------------|-----------|-------------|------------|
| 13 | **Potash** | Canada 31%, Russia 20%, Belarus 18% | — | `USDCAD` ✓ | — | `NTR.US` ✓, `MOS.US` ✓ | Forex + Equity |
| 14 | **Seed Genetics** | Top 4 = 60%+ | — | — | — | `DE.US` ✓, `CTVA.US` ✓ | Equity CFD |
| 15 | **Pollination** | California 80% (US almonds) | — | — | — | `DAR.US` ✓ | Equity CFD |
| 16 | **Refrigerant Gases** | China 60% | — | `USDCNH` ✓ | — | `HON.US` ✓, `CARR.US` ✓ | Forex + Equity |
| 17 | **Container Imbalance** | Asia-West 70% vol | — | — | — | `ZIM.US` ✓, `MATX.US` ✓ | Equity CFD |
| 18 | **Panama Canal** | 5% global trade | — | — | — | `ZIM.US` ✓ | Equity CFD |
| 19 | **Red Sea / Suez** | 12-15% global trade | `XTIUSD` ✓ | `USDNOK` ✓, `USDCAD` ✓ | — | `STNG.US` ✓, `FRO.US` ✓ | Multi-instrument |
| 20 | **Vanilla** | Madagascar 80% | — | — | — | — | No trade (illiquid) |
| 21 | **Palm Oil** | Indonesia 58%, Malaysia 25% | — | `USDMYR` ✗ | — | `WIL.UK` ✗ | Proxy: `SOYBEAN` ✓ |
| 22 | **Fishmeal** | Peru 25%, Chile 15% | — | `USDPEN` ✗ | — | `MOWI.US` ✓ | Equity CFD |
| 23 | **Cocoa** | Ivory Coast 38%, Ghana 17% | `COCOA` ✓ | — | — | — | Commodity CFD |
| 24 | **Natural Rubber** | Thailand 33%, Indonesia 26% | — | `USDTHB` ✗ | — | — | Proxy: `USDJPY` ✓ |
| 25 | **Bauxite/Alumina** | Australia 28%, Guinea 22% | `ALUMINIUM` ✓ | `AUDUSD` ✓ | — | `AA.US` ✓ | Multi-instrument |
| 26 | **Wheat Chokepoints** | Black Sea 30% exports | `WHEAT` ✓ | `USDTRY` ✓ | — | `ADM.US` ✓, `BG.US` ✓ | Multi-instrument |

### TECH / INFRA (14 Inefficiencies)

| # | Inefficiency | Concentration | Direct CFD | Forex Proxy | ETF Proxy | Equity Proxy | Trade Type |
|---|-------------|--------------|------------|-------------|-----------|-------------|------------|
| 27 | **Undersea Cables** | 3 companies = 90%+ | — | — | — | `TE.US` ✓, `NOK.US` ✓ | Equity CFD |
| 28 | **ASML Monopoly** | ASML 100% (EUV) | — | `EURUSD` ✓ | `SOXX.US` ✓ | `ASML.US` ✓ | Multi-instrument |
| 29 | **TSMC Concentration** | TSMC 90% (adv. chips) | — | `USDTWD` ✗ | `SOXX.US` ✓ | `TSM.US` ✓ | Equity + ETF |
| 30 | **Neon Gas** | Ukraine was 50%+ | — | — | `SOXX.US` ✓ | — | ETF CFD |
| 31 | **Ultra-Pure Water** | US/Japan dominance | — | `USDJPY` ✓ | — | `DHR.US` ✓ | Forex + Equity |
| 32 | **SWIFT System** | Global monopoly | — | `EURUSD` ✓ | — | — | Forex (event only) |
| 33 | **GPS/GNSS** | US GPS + EU Galileo | — | — | — | `LMT.US` ✓, `RTX.US` ✓ | Equity CFD |
| 34 | **Power Transformers** | 3 companies = 75% | — | `EURUSD` ✓ | — | `ETN.US` ✓, `CLF.US` ✓ | Multi-instrument |
| 35 | **HVDC Converters** | 4 companies = 85% | — | `EURSEK` ✓ | — | `ABB.US` ✓ | Forex + Equity |
| 36 | **Skilled Labor** | US/EU/Japan constrained | — | — | — | — | Macro indicator only |
| 37 | **Cloud Concentration** | AWS 31%, Azure 25%, GCP 11% | — | — | `QQQ.US` ✓ | `AMZN.US` ✓, `MSFT.US` ✓, `GOOGL.US` ✓ | Equity + ETF |
| 38 | **Copper** | Chile 24%, DRC 12%, Peru 10% | `COPPER` ✓ | `AUDUSD` ✓ | `COPX.US` ✓ | `FCX.US` ✓, `SCCO.US` ✓ | Multi-instrument |
| 39 | **Sand** | Localized markets | — | — | — | `VMC.US` ✓, `MLM.US` ✓ | Equity CFD |
| 40 | **Polysilicon** | China 80%+ | — | `USDCNH` ✓ | `TAN.US` ✓ | `ENPH.US` ✓ | Multi-instrument |

> **Legend:** ✓ = Available on Pepperstone | ✗ = Not available (use proxy) | — = No direct instrument

## 3.2 Instrument Grouping by Trade Type

### Pure Forex Trades

| Strategy | Pairs | Trigger |
|----------|-------|---------|
| China Export Ban | `USDCNH`, `AUDUSD` | China restricts critical mineral exports |
| Chokepoint/Oil Shock | `USDNOK`, `USDCAD`, `USDTRY` | Suez/Hormuz/Panama disruption |
| Taiwan Tension | `USDJPY`, `AUDJPY`, `CHFJPY` | Cross-strait military escalation |
| Mining Country Shock | `USDZAR`, `AUDUSD` | Mine closures in SA/Australia |

### Commodity CFD Trades

| Instrument | Pepperstone Symbol | Spread (typical) | Inefficiencies Covered |
|------------|-------------------|-------------------|----------------------|
| Copper | `COPPER` | $0.003 | #38 Copper, #9 Cobalt (proxy) |
| Cocoa | `COCOA` | $8 | #23 Cocoa |
| Wheat | `WHEAT` | $0.5 | #26 Wheat Chokepoints |
| Gold | `XAUUSD` | $0.12 | Risk-off hedge |
| Crude Oil | `XTIUSD` | $0.03 | #19 Red Sea/Suez |
| Soybean | `SOYBEAN` | $1.0 | #21 Palm Oil (proxy) |
| Aluminium | `ALUMINIUM` | $2.0 | #25 Bauxite/Alumina |

### ETF CFD Trades

| ETF | Pepperstone Symbol | Sector | Inefficiencies Covered |
|-----|-------------------|--------|----------------------|
| VanEck Rare Earth | `REMX.US` | Critical Minerals | #2, #3, #8 |
| iShares Semiconductor | `SOXX.US` | Semiconductors | #3, #28, #29, #30 |
| Global X Uranium | `URA.US` | Nuclear | #10 |
| Invesco Solar | `TAN.US` | Solar | #40 |
| Global X Copper Miners | `COPX.US` | Copper | #38 |
| Invesco QQQ | `QQQ.US` | Tech | #37 |

### Equity CFD Trades — Primary

| Company | Symbol | Sector | Inefficiencies |
|---------|--------|--------|---------------|
| Freeport-McMoRan | `FCX.US` | Copper Mining | #38 |
| Southern Copper | `SCCO.US` | Copper Mining | #38 |
| Cameco | `CCJ.US` | Uranium | #10 |
| MP Materials | `MP.US` | Rare Earths | #8 |
| TSMC | `TSM.US` | Semiconductors | #29 |
| ASML | `ASML.US` | Semiconductor Equip | #28 |
| Eaton Corp | `ETN.US` | Power Transformers | #34 |
| Linde | `LIN.US` | Industrial Gases | #1 |
| Air Products | `APD.US` | Industrial Gases | #1 |
| Nutrien | `NTR.US` | Potash/Phosphate | #7, #13 |
| Mosaic | `MOS.US` | Phosphate | #7, #13 |
| Scorpio Tankers | `STNG.US` | Tankers | #19 |
| ZIM Shipping | `ZIM.US` | Container Shipping | #17, #18 |
| Alcoa | `AA.US` | Aluminium | #25 |
| ABB Ltd | `ABB.US` | HVDC | #35 |
| Honeywell | `HON.US` | Refrigerants | #16 |

## 3.3 Correlation Groups (Avoid Doubling Up)

| Group | Instruments | Max Combined Allocation |
|-------|------------|------------------------|
| China Critical Minerals | USDCNH, REMX, MP, AUDUSD(short) | 15% |
| Copper Complex | COPPER, FCX, SCCO, COPX, AUDUSD | 15% |
| Semiconductor Chain | SOXX, TSM, ASML, INTC | 15% |
| Energy/Uranium | URA, CCJ, XTIUSD, USDCAD | 15% |
| Shipping/Chokepoints | ZIM, STNG, FRO, USDNOK | 12% |
| Agriculture | WHEAT, COCOA, SOYBEAN, NTR, MOS | 12% |

---

# 4. PHASE 2: SIGNAL ENGINE DEVELOPMENT

## 4.1 Layer 1: Inefficiency Scanner

### Scanner Architecture

```python
# signals/layer1_scanner.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import datetime

class AlertLevel(Enum):
    GREEN = 0   # Normal — no action
    YELLOW = 1  # Elevated — increase monitoring
    ORANGE = 2  # High — prepare positions
    RED = 3     # Critical — execute trades

@dataclass
class InefficiencySignal:
    inefficiency_id: int
    name: str
    alert_level: AlertLevel
    trigger_type: str          # EVENT, PRICE, DATA, SENTIMENT
    confidence: float          # 0.0 - 1.0
    instruments: list[str]     # Pepperstone symbols
    direction: str             # BUY, SELL
    source: str                # GDELT, PRICE, QUANDL, RSS
    headline: Optional[str] = None
    timestamp: datetime.datetime = None

class Layer1Scanner:
    """Scan all 40 inefficiencies for trigger conditions."""

    def __init__(self, config, gdelt, sentiment, quandl, fred):
        self.config = config
        self.gdelt = gdelt
        self.sentiment = sentiment
        self.quandl = quandl
        self.fred = fred
        self.scanners = self._build_scanners()

    def _build_scanners(self) -> dict:
        return {
            1: self._scan_helium,
            2: self._scan_antimony,
            3: self._scan_gallium_germanium,
            # ... all 40
            38: self._scan_copper,
            39: self._scan_sand,
            40: self._scan_polysilicon,
        }

    def scan_all(self) -> list[InefficiencySignal]:
        signals = []
        for ineff_id, scanner_fn in self.scanners.items():
            try:
                result = scanner_fn()
                if result and result.alert_level.value >= AlertLevel.ORANGE.value:
                    signals.append(result)
            except Exception as e:
                logger.error(f"Scanner {ineff_id} failed: {e}")
        return signals
```

### Trigger Conditions — All 40 Inefficiencies

#### ENERGY / MINING Triggers

| # | Inefficiency | Trigger Type | Condition | Threshold | Data Source | Scan Freq |
|---|-------------|-------------|-----------|-----------|-------------|-----------|
| 1 | Helium | EVENT | US BLM plant shutdown, Qatar disruption | GDELT score >0.7 | GDELT + RSS | 15 min |
| 1 | Helium | PRICE | Helium spot price spike | >20% in 30 days | Quandl | Daily |
| 2 | Antimony | EVENT | China export restriction announcement | GDELT theme match | GDELT + RSS | 15 min |
| 2 | Antimony | PRICE | USDCNH move >1.5% in session | FX rate | MT5 | Real-time |
| 3 | Gallium/Germ. | EVENT | China Ga/Ge export ban/quota | GDELT theme match | GDELT + RSS | 15 min |
| 3 | Gallium/Germ. | PRICE | SOXX drop >3% intraday | ETF price | MT5 | Real-time |
| 3 | Gallium/Germ. | DATA | Ga/Ge inventory drawdown | <3 months supply | USGS | Monthly |
| 4 | Graphite | EVENT | China graphite export controls | GDELT theme match | GDELT | 15 min |
| 4 | Graphite | SENTIMENT | Negative EV battery supply sentiment | FinBERT <-0.5 | News | Hourly |
| 5 | Manganese | EVENT | S.Africa/Gabon mining disruption | GDELT theme match | GDELT | 15 min |
| 5 | Manganese | PRICE | USDZAR spike >2% in 24h | FX rate | MT5 | Real-time |
| 6 | Fluorspar | EVENT | China fluoride chemical restriction | GDELT theme match | GDELT | 15 min |
| 7 | Phosphate | EVENT | Morocco political event, OCP disruption | GDELT theme match | GDELT | 15 min |
| 7 | Phosphate | PRICE | DAP fertilizer price >$600/t | Quandl | Daily |
| 8 | Rare Earths | EVENT | China RE export ban/processing halt | GDELT score >0.8 | GDELT + RSS | 15 min |
| 8 | Rare Earths | DATA | USGS RE import dependency change | >80% import reliance | USGS | Monthly |
| 8 | Rare Earths | PRICE | REMX gap up/down >5% | ETF price | MT5 | Real-time |
| 9 | Cobalt | EVENT | DRC mining accident, export halt | GDELT theme match | GDELT | 15 min |
| 9 | Cobalt | PRICE | Cobalt LME price spike >15% in 30d | LME | Daily |
| 10 | Uranium | EVENT | Russia enrichment disruption, Kazakh revolt | GDELT theme match | GDELT | 15 min |
| 10 | Uranium | PRICE | URA ETF breakout above 52-week high | ETF price | MT5 | Daily |
| 10 | Uranium | DATA | US uranium inventory <1 year reserve | FRED / EIA | Monthly |
| 11 | Titanium Sponge | EVENT | Russia/China titanium supply cut | GDELT theme match | GDELT | 15 min |
| 12 | Magnesium | EVENT | China magnesium production cut / env. shutdown | GDELT theme match | GDELT | 15 min |

#### FOOD / SHIPPING Triggers

| # | Inefficiency | Trigger Type | Condition | Threshold | Data Source | Scan Freq |
|---|-------------|-------------|-----------|-----------|-------------|-----------|
| 13 | Potash | EVENT | Russia/Belarus sanction escalation | GDELT score >0.7 | GDELT | 15 min |
| 13 | Potash | PRICE | Potash spot >$400/t | Quandl | Daily |
| 14 | Seed Genetics | EVENT | Major crop failure / IP dispute | GDELT theme match | GDELT + RSS | Hourly |
| 15 | Pollination | EVENT | California bee colony collapse report | RSS + USDA | Weekly |
| 16 | Refrigerants | EVENT | China HFC quota announcement | GDELT theme match | GDELT | 15 min |
| 17 | Container Imb. | PRICE | SCFI freight index >3000 | Quandl / RSS | Daily |
| 17 | Container Imb. | DATA | Port congestion >15 ships waiting | MarineTraffic | Hourly |
| 18 | Panama Canal | EVENT | Water level critical / transit restrictions | GDELT + RSS | 15 min |
| 18 | Panama Canal | DATA | Daily transits <24 (vs normal 36) | ACP reports | Daily |
| 19 | Red Sea/Suez | EVENT | Houthi attack, strait closure threat | GDELT score >0.8 | GDELT | 15 min |
| 19 | Red Sea/Suez | PRICE | Crude oil spike >5% intraday | MT5 | Real-time |
| 19 | Red Sea/Suez | DATA | Suez transit count drop >30% | MarineTraffic | Daily |
| 20 | Vanilla | — | No tradeable instrument | — | — | — |
| 21 | Palm Oil | PRICE | Palm oil futures spike >10% in 30d | Quandl | Daily |
| 21 | Palm Oil | EVENT | Indonesia export ban | GDELT theme match | GDELT | 15 min |
| 22 | Fishmeal | EVENT | Peru El Niño anchovy ban | GDELT + RSS | Weekly |
| 23 | Cocoa | PRICE | Cocoa CFD >15% above 200-DMA | MT5 | Daily |
| 23 | Cocoa | EVENT | Ivory Coast supply shock / weather | GDELT + RSS | 15 min |
| 24 | Nat. Rubber | EVENT | Thailand flood / Indonesia disruption | GDELT theme match | GDELT | 15 min |
| 25 | Bauxite | EVENT | Guinea coup / Australia mine closure | GDELT score >0.7 | GDELT | 15 min |
| 25 | Bauxite | PRICE | Aluminium LME spike >8% in 30d | MT5 | Daily |
| 26 | Wheat | EVENT | Black Sea corridor collapse | GDELT score >0.8 | GDELT | 15 min |
| 26 | Wheat | PRICE | Wheat CFD breakout above 52-wk high | MT5 | Daily |

#### TECH / INFRA Triggers

| # | Inefficiency | Trigger Type | Condition | Threshold | Data Source | Scan Freq |
|---|-------------|-------------|-----------|-----------|-------------|-----------|
| 27 | Undersea Cables | EVENT | Cable cut (SEA-ME-WE, etc.) | GDELT theme match | GDELT + RSS | 15 min |
| 28 | ASML | EVENT | Dutch export restriction, ASML guidance | GDELT + RSS | 15 min |
| 28 | ASML | PRICE | ASML.US gap down >5% | MT5 | Real-time |
| 29 | TSMC | EVENT | Taiwan Strait military activity | GDELT score >0.8 | GDELT | 15 min |
| 29 | TSMC | PRICE | TSM.US drop >7% in session | MT5 | Real-time |
| 30 | Neon Gas | EVENT | Ukraine conflict escalation near Odesa | GDELT theme match | GDELT | 15 min |
| 31 | Ultra-Pure Water | EVENT | Japan semiconductor fab disruption | GDELT + RSS | Hourly |
| 32 | SWIFT | EVENT | Country disconnected from SWIFT | GDELT score >0.9 | GDELT | 15 min |
| 33 | GPS/GNSS | EVENT | GPS spoofing/jamming mass event | GDELT + RSS | 15 min |
| 34 | Power Transformers | EVENT | Grid failure, transformer shortage report | GDELT + RSS | Hourly |
| 34 | Power Transformers | DATA | US transformer backlog >3 years | DOE/RSS | Monthly |
| 35 | HVDC | EVENT | Major HVDC project delay/cancellation | RSS | Weekly |
| 36 | Skilled Labor | DATA | Manufacturing PMI employment <48 | FRED | Monthly |
| 37 | Cloud | EVENT | AWS/Azure major outage >4 hours | RSS + GDELT | 15 min |
| 38 | Copper | PRICE | Copper CFD breakout above $5.00/lb | MT5 | Real-time |
| 38 | Copper | EVENT | Chile/Peru/DRC mine disruption | GDELT score >0.7 | GDELT | 15 min |
| 38 | Copper | DATA | LME copper inventory <150,000t | Quandl | Daily |
| 39 | Sand | EVENT | Regional sand mining ban | GDELT + RSS | Weekly |
| 40 | Polysilicon | EVENT | China polysilicon factory accident / power cut | GDELT | 15 min |
| 40 | Polysilicon | PRICE | TAN ETF move >5% intraday | MT5 | Real-time |

## 4.2 Layer 2: Confirmation Engine

### Architecture

```python
# signals/layer2_confirmation.py

class Layer2Confirmation:
    """
    Confirm Layer 1 signals using 3 pillars:
    1. Technical Analysis (price action + indicators)
    2. Fundamental Check (inventory, spreads, macro)
    3. Sentiment Analysis (FinBERT on recent news)

    A signal must pass ≥2 of 3 pillars to be confirmed.
    """

    TECHNICAL_WEIGHT = 0.35
    FUNDAMENTAL_WEIGHT = 0.35
    SENTIMENT_WEIGHT = 0.30
    CONFIRMATION_THRESHOLD = 0.60  # Weighted score must exceed this

    def confirm(self, signal: InefficiencySignal) -> ConfirmedSignal:
        tech_score = self._technical_check(signal)
        fund_score = self._fundamental_check(signal)
        sent_score = self._sentiment_check(signal)

        weighted = (
            tech_score * self.TECHNICAL_WEIGHT +
            fund_score * self.FUNDAMENTAL_WEIGHT +
            sent_score * self.SENTIMENT_WEIGHT
        )

        pillars_passed = sum(1 for s in [tech_score, fund_score, sent_score] if s > 0.5)

        confirmed = weighted >= self.CONFIRMATION_THRESHOLD and pillars_passed >= 2

        return ConfirmedSignal(
            signal=signal,
            tech_score=tech_score,
            fund_score=fund_score,
            sent_score=sent_score,
            composite_score=weighted,
            pillars_passed=pillars_passed,
            confirmed=confirmed
        )
```

### Technical Indicators

| Indicator | Parameters | BUY Condition | SELL Condition | Weight |
|-----------|-----------|--------------|---------------|--------|
| RSI(14) | Period: 14 | RSI < 30 (oversold) | RSI > 70 (overbought) | 0.15 |
| MACD | 12, 26, 9 | MACD crosses above signal | MACD crosses below signal | 0.20 |
| Bollinger Bands | 20, 2.0 | Price touches lower band | Price touches upper band | 0.15 |
| 200-DMA | Period: 200 | Price > 200-DMA | Price < 200-DMA | 0.20 |
| ATR(14) | Period: 14 | ATR expanding (trend) | ATR contracting (range) | 0.10 |
| Volume | 20-day avg | Volume > 1.5x average | Volume > 1.5x average | 0.10 |
| ADX(14) | Period: 14 | ADX > 25 (trending) | ADX > 25 (trending) | 0.10 |

### Fundamental Checks Per Category

| Category | Check | BUY Trigger | SELL Trigger | Source |
|----------|-------|------------|-------------|--------|
| Commodity | Inventory levels | Below 3-month average | Above 6-month average | Quandl |
| Commodity | Forward curve | Backwardation | Contango | Quandl |
| Forex | Interest rate diff | Positive carry | Negative carry | FRED |
| Forex | Current account | Worsening deficit | Improving surplus | FRED |
| Equity | P/E ratio | < sector average | > 2x sector average | Quandl |
| Equity | Revenue growth | > 10% YoY | < -5% YoY | Quandl |
| All | DXY direction | DXY falling (risk-on) | DXY rising (risk-off) | FRED |
| All | VIX level | VIX < 20 (calm) | VIX > 30 (fear) | MT5 |

### Sentiment Scoring

```python
def _sentiment_check(self, signal: InefficiencySignal) -> float:
    """
    Score: 0.0 (bearish) to 1.0 (bullish)
    Uses FinBERT on last 24h of relevant news headlines.
    """
    keywords = self._get_keywords_for_inefficiency(signal.inefficiency_id)
    articles = self.gdelt.search_articles(keywords, hours=24)

    if not articles:
        return 0.5  # Neutral if no news

    sentiments = self.finbert.analyze_batch([a['title'] for a in articles])
    avg_composite = np.mean([s['composite'] for s in sentiments])

    # Map from [-1, 1] to [0, 1]
    score = (avg_composite + 1) / 2

    # For SELL signals, invert (negative news = bullish for short)
    if signal.direction == "SELL":
        score = 1 - score

    return float(np.clip(score, 0, 1))
```

## 4.3 Layer 3: Portfolio Manager

### Position Sizing

```python
# signals/layer3_portfolio.py

class Layer3PortfolioManager:
    """
    Portfolio-level position sizing and risk management.

    Rules:
    - Max positions: 10
    - Single position max: 5% of equity
    - Sector max: 15% of equity
    - Correlated pair (ρ > 0.7): only best 1
    - Max drawdown: 10% → close all
    - Daily VaR: 2%
    """

    MAX_POSITIONS = 10
    MAX_SINGLE_POSITION_PCT = 0.05   # 5% of equity
    MAX_SECTOR_PCT = 0.15            # 15% of equity
    MAX_CORRELATION = 0.70
    MAX_DRAWDOWN_PCT = 0.10          # 10%
    MAX_DAILY_VAR = 0.02             # 2%

    def size_position(self, signal: ConfirmedSignal, account: AccountInfo) -> SizedPosition:
        equity = account.equity

        # Step 1: Kelly Criterion (capped)
        win_rate = self._get_historical_win_rate(signal.inefficiency_id)
        avg_win = self._get_avg_win(signal.inefficiency_id)
        avg_loss = self._get_avg_loss(signal.inefficiency_id)

        if avg_loss == 0:
            kelly_pct = 0.01  # minimum
        else:
            win_loss_ratio = avg_win / abs(avg_loss)
            kelly_pct = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
            kelly_pct = max(0.01, min(kelly_pct * 0.5, 0.05))  # Half-Kelly, capped at 5%

        # Step 2: ATR-based stop distance
        atr = self._get_atr(signal.instrument, period=14)
        stop_distance = atr * 2.0  # 2x ATR

        # Step 3: Position size from risk
        risk_amount = equity * kelly_pct
        pip_value = self._get_pip_value(signal.instrument)
        stop_pips = stop_distance / pip_value

        if stop_pips > 0:
            lot_size = risk_amount / (stop_pips * pip_value * 100000)
        else:
            lot_size = 0.01  # minimum

        # Step 4: Apply portfolio constraints
        lot_size = self._apply_constraints(lot_size, signal, equity)

        return SizedPosition(
            signal=signal,
            lot_size=round(lot_size, 2),
            stop_loss=signal.entry_price - stop_distance if signal.direction == "BUY"
                      else signal.entry_price + stop_distance,
            take_profit=signal.entry_price + (stop_distance * 2.0) if signal.direction == "BUY"
                        else signal.entry_price - (stop_distance * 2.0),
            risk_pct=kelly_pct,
            risk_amount=risk_amount,
        )

    def _apply_constraints(self, lot_size, signal, equity):
        # Check max positions
        open_count = self._count_open_positions()
        if open_count >= self.MAX_POSITIONS:
            return 0  # Reject

        # Check sector exposure
        sector = self._get_sector(signal.inefficiency_id)
        sector_exposure = self._get_sector_exposure(sector)
        remaining_sector = (self.MAX_SECTOR_PCT * equity) - sector_exposure
        if remaining_sector <= 0:
            return 0  # Reject

        # Check correlation
        for pos in self._get_open_positions():
            corr = self._get_correlation(signal.instrument, pos.instrument)
            if abs(corr) > self.MAX_CORRELATION:
                if signal.composite_score <= pos.composite_score:
                    return 0  # Reject — existing position is stronger

        # Check drawdown circuit breaker
        current_dd = self._get_current_drawdown()
        if current_dd > self.MAX_DRAWDOWN_PCT:
            return 0  # HALT — close everything

        return lot_size
```

### Correlation Matrix (Key Pairs)

| | COPPER | AUDUSD | FCX | USDCNH | REMX | SOXX | URA | WHEAT | XTIUSD |
|---|--------|--------|-----|--------|------|------|-----|-------|--------|
| **COPPER** | 1.00 | 0.72 | 0.85 | -0.45 | 0.55 | 0.30 | 0.15 | 0.10 | 0.25 |
| **AUDUSD** | 0.72 | 1.00 | 0.68 | -0.52 | 0.48 | 0.22 | 0.18 | 0.05 | 0.20 |
| **FCX** | 0.85 | 0.68 | 1.00 | -0.40 | 0.52 | 0.28 | 0.12 | 0.08 | 0.22 |
| **USDCNH** | -0.45 | -0.52 | -0.40 | 1.00 | -0.35 | -0.15 | -0.08 | 0.05 | -0.10 |
| **REMX** | 0.55 | 0.48 | 0.52 | -0.35 | 1.00 | 0.42 | 0.25 | 0.02 | 0.12 |
| **SOXX** | 0.30 | 0.22 | 0.28 | -0.15 | 0.42 | 1.00 | 0.10 | -0.05 | 0.08 |
| **URA** | 0.15 | 0.18 | 0.12 | -0.08 | 0.25 | 0.10 | 1.00 | 0.00 | 0.15 |
| **WHEAT** | 0.10 | 0.05 | 0.08 | 0.05 | 0.02 | -0.05 | 0.00 | 1.00 | 0.30 |
| **XTIUSD** | 0.25 | 0.20 | 0.22 | -0.10 | 0.12 | 0.08 | 0.15 | 0.30 | 1.00 |

> ⚠️ **COPPER ↔ AUDUSD (0.72)**: Only take the stronger signal. Never hold both simultaneously.
> ⚠️ **COPPER ↔ FCX (0.85)**: FCX is a leveraged copper play. Choose one.

## 4.4 MQL5 Expert Advisor Structure

```mql5
//+------------------------------------------------------------------+
//| SCI_Main_EA.mq5 — Supply Chain Inefficiency Main EA              |
//+------------------------------------------------------------------+
#property copyright "SCI Trading System"
#property version   "1.00"
#property description "Reads Python signals and executes trades with risk mgmt"

#include <SCI_RiskManager.mqh>
#include <SCI_SignalParser.mqh>

// Input parameters
input string   SignalFilePath = "C:\\Users\\I022583\\SCI_Trade\\signals\\active_signals.json";
input int      SignalCheckInterval = 5;        // seconds
input double   MaxDrawdownPct = 10.0;          // circuit breaker
input int      MaxPositions = 10;
input double   MaxSinglePositionPct = 5.0;     // % of equity
input double   MaxSectorPct = 15.0;            // % of equity per sector
input bool     EnableTrading = true;
input double   SlippagePips = 3.0;

// Global objects
CRiskManager   riskMgr;
CSignalParser  signalParser;
datetime       lastSignalCheck;

//+------------------------------------------------------------------+
int OnInit() {
    // Initialize risk manager
    riskMgr.Init(MaxDrawdownPct, MaxPositions, MaxSinglePositionPct, MaxSectorPct);

    // Set timer for signal checks
    EventSetTimer(SignalCheckInterval);

    Print("SCI EA initialized. Signal file: ", SignalFilePath);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnTimer() {
    if (!EnableTrading) return;

    // Circuit breaker check
    if (riskMgr.IsCircuitBreakerTriggered()) {
        Print("⚠️ CIRCUIT BREAKER ACTIVE — closing all positions");
        riskMgr.CloseAllPositions();
        return;
    }

    // Read signals from Python
    SCISignal signals[];
    int count = signalParser.ReadSignals(SignalFilePath, signals);

    for (int i = 0; i < count; i++) {
        ProcessSignal(signals[i]);
    }
}

//+------------------------------------------------------------------+
void ProcessSignal(SCISignal &signal) {
    // Validate signal freshness (max 60 seconds old)
    if (TimeCurrent() - signal.timestamp > 60) {
        Print("Signal expired: ", signal.instrument);
        return;
    }

    // Risk checks
    if (!riskMgr.CanOpenPosition(signal.instrument, signal.sector,
                                  signal.lotSize, signal.direction)) {
        Print("Risk check failed for: ", signal.instrument);
        return;
    }

    // Execute
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    request.action = TRADE_ACTION_DEAL;
    request.symbol = signal.instrument;
    request.volume = signal.lotSize;
    request.type = (signal.direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.price = (signal.direction == "BUY") ?
                    SymbolInfoDouble(signal.instrument, SYMBOL_ASK) :
                    SymbolInfoDouble(signal.instrument, SYMBOL_BID);
    request.sl = signal.stopLoss;
    request.tp = signal.takeProfit;
    request.deviation = (ulong)(SlippagePips * 10);
    request.magic = signal.inefficiencyId;
    request.comment = "SCI_" + IntegerToString(signal.inefficiencyId);

    if (OrderSend(request, result)) {
        Print("✓ Order executed: ", signal.instrument, " ", signal.direction,
              " Ticket: ", result.order);
        // Log to file for Python monitoring
        LogTrade(signal, result);
    } else {
        Print("✗ Order failed: ", signal.instrument, " Error: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    EventKillTimer();
    Print("SCI EA stopped. Reason: ", reason);
}
```

### Signal File Format (Python → MQL5)

```json
// active_signals.json — written by Python, read by MQL5 EA
{
    "last_updated": "2026-11-15T14:30:00Z",
    "signals": [
        {
            "inefficiency_id": 38,
            "instrument": "COPPER",
            "direction": "BUY",
            "lot_size": 0.05,
            "entry_price": 4.85,
            "stop_loss": 4.72,
            "take_profit": 5.10,
            "confidence": 0.78,
            "sector": "COPPER_COMPLEX",
            "timestamp": "2026-11-15T14:29:55Z",
            "trigger": "Chile mine strike + LME inventory <150k + RSI(14)=28"
        }
    ]
}
```

## 4.5 Python Signal Generator Structure

```python
# main.py — Main orchestrator

import schedule
import time
from loguru import logger
from signals.layer1_scanner import Layer1Scanner
from signals.layer2_confirmation import Layer2Confirmation
from signals.layer3_portfolio import Layer3PortfolioManager
from signals.signal_bus import SignalBus
from data.gdelt_monitor import GDELTMonitor
from data.sentiment import FinBERTSentiment
from execution.mt5_bridge import MT5Bridge

def run_signal_pipeline():
    """Execute full signal pipeline: Scan → Confirm → Size → Emit."""

    # Layer 1: Scan for raw signals
    raw_signals = scanner.scan_all()
    logger.info(f"Layer 1: {len(raw_signals)} raw signals")

    # Layer 2: Confirm signals
    confirmed = []
    for signal in raw_signals:
        result = confirmation.confirm(signal)
        if result.confirmed:
            confirmed.append(result)
    logger.info(f"Layer 2: {len(confirmed)} confirmed signals")

    # Layer 3: Size and filter through portfolio rules
    account = mt5.get_account_info()
    sized = []
    for signal in confirmed:
        position = portfolio.size_position(signal, account)
        if position.lot_size > 0:
            sized.append(position)
    logger.info(f"Layer 3: {len(sized)} sized positions")

    # Emit to signal bus → writes active_signals.json for MQL5 EA
    signal_bus.emit(sized)

def run_event_scanner():
    """Quick GDELT scan for breaking events."""
    events = gdelt.scan(lookback_hours=1)
    if not events.empty:
        high_priority = events[events['goldstein_scale'].abs() > 5]
        if not high_priority.empty:
            logger.warning(f"🚨 {len(high_priority)} high-priority events detected")
            # Trigger immediate signal pipeline run
            run_signal_pipeline()

# Schedule jobs
schedule.every(15).minutes.do(run_signal_pipeline)
schedule.every(5).minutes.do(run_event_scanner)
schedule.every(1).hours.do(monitoring.update_dashboard)
schedule.every(1).days.at("18:00").do(monitoring.daily_report)

if __name__ == "__main__":
    logger.info("SCI Trading System starting...")

    # Initialize components
    gdelt = GDELTMonitor()
    finbert = FinBERTSentiment()
    mt5 = MT5Bridge()
    scanner = Layer1Scanner(config, gdelt, finbert, quandl, fred)
    confirmation = Layer2Confirmation(mt5, finbert, gdelt)
    portfolio = Layer3PortfolioManager(mt5)
    signal_bus = SignalBus()

    # Run forever
    while True:
        schedule.run_pending()
        time.sleep(1)
```

---

## 4.6 Agent-Based Framework Integration

### Why Agent-Based Trading

Traditional signal engines use fixed rules. Agent-based frameworks add **adaptive reasoning** — LLM agents debate, RL agents optimize, and multi-agent architectures catch what single-model systems miss. The open-source ecosystem now offers production-grade components that map directly onto our 3-layer architecture.

### Architecture — Agent-Enhanced Signal Engine

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER (unchanged)                        │
│  GDELT │ FinBERT/FinGPT │ Quandl │ FRED │ USGS │ MarineTraffic │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│          LAYER 1-2: TradingAgents DEBATE FRAMEWORK              │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐       │
│  │ Supply   │ │ Sentiment│ │ News     │ │ Technical    │       │
│  │ Analyst  │ │ Analyst  │ │ Analyst  │ │ Analyst      │       │
│  │(FinGPT)  │ │(FinBERT) │ │(GDELT)   │ │(TA-Lib/MT5)  │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘       │
│       └─────────────┴────────────┴──────────────┘               │
│                          │                                       │
│                    ┌─────▼──────┐                                │
│                    │ Bull vs    │ ← LangGraph orchestration      │
│                    │ Bear Debate│ ← Hermes-4 / Claude as LLM    │
│                    └─────┬──────┘                                │
│                          │ Signal + confidence score             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│            LAYER 3: FinRL PORTFOLIO OPTIMIZATION                 │
│                                                                  │
│  Deep-RL agent trained on historical inefficiency trades         │
│  → Kelly-weighted position sizing                                │
│  → Correlation-aware allocation                                  │
│  → Regime-adaptive risk budgeting                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│        EXECUTION: QuantDinger → MT5 MCP Bridge                   │
│                                                                  │
│  QuantDinger "Agentic Trading OS"                                │
│  → Python strategies natively                                    │
│  → MCP protocol → MT5 server (127.0.0.1:22346)                  │
│  → Backtest + Paper + Live in one platform                       │
│  → OpenAlice lifecycle patterns for order management             │
│                                                                  │
│  FALLBACK: Direct MQL5 EA if MCP bridge unstable                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│        MONITORING: Grafana + FinRobot Weekly Reports             │
└─────────────────────────────────────────────────────────────────┘
```

### Component Selection Matrix

| Component | Repo | Stars | License | Our Layer | Role |
|-----------|------|-------|---------|-----------|------|
| **TradingAgents** | TauricResearch | 122.7K | Apache-2.0 | Layer 1-2 | Multi-analyst debate → signal generation |
| **FinRL + FinRL-Meta** | AI4Finance | 17.1K | MIT | Layer 3 + Execution | RL portfolio optimization + MT5 live env |
| **QuantDinger** | OpenByte | 13.8K | Apache-2.0 | Execution | Agentic Trading OS + MCP → MT5 bridge |
| **FinGPT** | AI4Finance | 21.6K | MIT | Layer 1-2 | Fine-tuned supply chain sentiment model |
| **OpenAlice** | TraderAlice | 7.5K | AGPL-3.0 | Execution ref | Forex trade lifecycle patterns |
| **FinRobot** | AI4Finance | 8.4K | Apache-2.0 | Monitoring | Automated weekly strategy reports |

### 4.6.1 TradingAgents Integration (Layer 1-2)

**Purpose:** Replace static rule-based signal generation with LLM multi-agent debate for higher signal quality.

**Custom Analyst Personas for Supply Chain:**

```python
# agents/supply_chain_analysts.py

ANALYST_PERSONAS = {
    "supply_analyst": {
        "role": "Supply Chain Concentration Analyst",
        "prompt": """You analyze supply chain concentration risks.
        Monitor: warehouse stocks (LME/COMEX), mine output (USGS),
        export bans (GDELT), shipping disruptions (MarineTraffic).
        Focus: single-source dependencies, chokepoint bottlenecks,
        inventory-to-consumption ratios below 30-day threshold.""",
        "data_feeds": ["quandl_lme", "usgs_minerals", "gdelt_supply"],
    },
    "sentiment_analyst": {
        "role": "Market Sentiment Analyst",
        "prompt": """You analyze market sentiment for commodity and
        supply chain disruptions. Use FinGPT/FinBERT scores on
        supply-chain-specific news. Track fear indicators: VIX,
        commodity volatility indices, shipping rate spikes.
        Distinguish panic (tradeable) from noise (ignore).""",
        "data_feeds": ["finbert_scores", "vix", "bdiy_proxy"],
    },
    "news_analyst": {
        "role": "Geopolitical Event Analyst",
        "prompt": """You monitor real-time geopolitical events that
        impact supply chains. GDELT event categories: export bans,
        strait closures, mine strikes, sanctions, natural disasters.
        Rate each event by: severity (1-10), duration estimate,
        number of commodities affected, historical precedent.""",
        "data_feeds": ["gdelt_events", "rss_reuters", "rss_ft"],
    },
    "technical_analyst": {
        "role": "Technical & Flow Analyst",
        "prompt": """You analyze price action and order flow for
        commodity-correlated instruments. Track: breakout from
        consolidation, volume surges, COT positioning extremes,
        currency pair divergences from commodity benchmarks.
        Use: RSI, MACD, Bollinger Bands, ATR, 50/200 MA.""",
        "data_feeds": ["mt5_prices", "mt5_volume", "cot_data"],
    },
}

DEBATE_CONFIG = {
    "rounds": 2,                    # Bull vs Bear rounds
    "min_confidence": 0.65,         # Minimum consensus to trade
    "llm_provider": "openrouter",   # Hermes-4 via OpenRouter
    "llm_model": "nousresearch/hermes-4",
    "temperature": 0.3,             # Low for consistency
    "max_tokens": 500,              # Per analyst response
    "decision_threshold": 3,        # 3 of 4 analysts must agree
}
```

**LangGraph Workflow:**

```python
# agents/debate_workflow.py
from langgraph.graph import StateGraph, END

def create_debate_graph():
    graph = StateGraph(DebateState)

    # Parallel analyst nodes
    graph.add_node("supply_analyst", supply_analysis)
    graph.add_node("sentiment_analyst", sentiment_analysis)
    graph.add_node("news_analyst", news_analysis)
    graph.add_node("technical_analyst", technical_analysis)

    # Debate nodes
    graph.add_node("bull_case", compile_bull_case)
    graph.add_node("bear_case", compile_bear_case)
    graph.add_node("debate_resolution", resolve_debate)

    # Risk check
    graph.add_node("risk_check", risk_assessment)

    # Flow: parallel analysts → bull/bear → resolution → risk
    graph.add_edge("supply_analyst", "bull_case")
    graph.add_edge("sentiment_analyst", "bull_case")
    graph.add_edge("news_analyst", "bull_case")
    graph.add_edge("technical_analyst", "bull_case")

    graph.add_edge("supply_analyst", "bear_case")
    graph.add_edge("sentiment_analyst", "bear_case")
    graph.add_edge("news_analyst", "bear_case")
    graph.add_edge("technical_analyst", "bear_case")

    graph.add_edge("bull_case", "debate_resolution")
    graph.add_edge("bear_case", "debate_resolution")
    graph.add_edge("debate_resolution", "risk_check")
    graph.add_edge("risk_check", END)

    return graph.compile(checkpointer=MemorySaver())
```

### 4.6.2 FinRL Portfolio Optimization (Layer 3)

**Purpose:** Replace static Kelly criterion with a trained RL agent that learns optimal position sizing across correlated inefficiency trades.

```python
# agents/finrl_portfolio.py
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.agents.stablebaselines3.models import DRLAgent

FINRL_CONFIG = {
    "env": "MT5TradingEnv",        # Custom env wrapping FinRL-Meta MT5
    "algorithm": "PPO",             # Proximal Policy Optimization
    "total_timesteps": 500_000,
    "training_period": "2020-01-01:2025-06-30",
    "validation_period": "2025-07-01:2026-06-30",

    # State space: 40 inefficiency scores + prices + positions + risk
    "state_dim": 40 + 24 + 24 + 5,  # scores + prices + positions + portfolio metrics

    # Action space: position size for each of 24 instruments (-1 to +1)
    "action_dim": 24,

    # Reward: Sharpe ratio (risk-adjusted return)
    "reward_function": "sharpe_with_drawdown_penalty",

    # Risk constraints built into reward
    "max_drawdown_penalty": -10.0,   # Heavy penalty for DD > 10%
    "correlation_penalty": -2.0,     # Penalty for correlated positions
    "position_limit": 0.05,          # Max 5% per position
}
```

**Training Pipeline:**

```
1. Collect historical data for all 24 Pepperstone instruments (2020-2026)
2. Generate historical inefficiency scores (Layer 1 backfill)
3. Create MT5TradingEnv with FinRL-Meta
4. Train PPO agent (500K timesteps, ~8-12 hours on GPU)
5. Validate on 2025-2026 out-of-sample
6. Deploy as Layer 3 decision maker
7. Retrain monthly with new data (walk-forward)
```

### 4.6.3 QuantDinger Execution Bridge

**Purpose:** Replace custom MQL5 EA with QuantDinger's proven execution framework, connecting via MCP to MT5.

```python
# execution/quantdinger_bridge.py

QUANTDINGER_CONFIG = {
    "mode": "live",                          # backtest | paper | live
    "broker_connection": "mt5_mcp",
    "mcp_server": "127.0.0.1:22346",        # Local MT5 MCP server
    "pepperstone_server": "Pepperstone-MT5", # MT5 server name
    "account_type": "razor",

    # Strategy registration
    "strategies": [
        "supply_chain_forex",                 # AUD/USD, USD/CAD etc.
        "supply_chain_commodity",             # Copper, Cocoa, Cotton
        "supply_chain_equity",               # FCX, TSM, ASML etc.
        "supply_chain_etf",                  # URA, SOXX etc.
        "supply_chain_event",                # Event-driven trades
    ],

    # Risk enforcement at execution level
    "max_slippage_pips": 3,
    "max_spread_multiplier": 2.0,            # Skip if spread > 2x normal
    "order_timeout_seconds": 30,
    "retry_count": 3,
}
```

**Execution Flow:**

```
TradingAgents (signal)
    → FinRL (position size)
        → QuantDinger (execution)
            → MCP protocol
                → MT5 Pepperstone Razor
                    → Market order / Limit order

Fallback chain:
  QuantDinger MCP fails → Direct MT5 Python API (MetaTrader5 package)
  MT5 Python API fails → MQL5 EA (standalone, file-based signals)
```

### 4.6.4 FinGPT Fine-Tuned Sentiment (Layer 1-2 Enhancement)

**Purpose:** Train a supply-chain-specific sentiment model that outperforms generic FinBERT on our domain.

```python
# models/fingpt_supply_chain.py

FINGPT_FINETUNE_CONFIG = {
    "base_model": "FinGPT/fingpt-sentiment_llama2-13b_lora",
    "training_data": {
        "sources": [
            "reuters_commodities_2020_2026.jsonl",
            "ft_supply_chain_2020_2026.jsonl",
            "bloomberg_metals_mining_2020_2026.jsonl",
            "gdelt_supply_disruption_2020_2026.jsonl",
        ],
        "labels": "3-class",  # BULLISH / NEUTRAL / BEARISH
        "supply_chain_specific": True,
    },
    "lora_config": {
        "r": 8,
        "lora_alpha": 32,
        "target_modules": ["q_proj", "v_proj"],
    },
    "training": {
        "epochs": 3,
        "batch_size": 4,
        "learning_rate": 2e-4,
        "max_length": 512,
    },
    # Expected improvement over generic FinBERT:
    # +15-20% accuracy on supply chain disruption headlines
    # +25% on non-English commodity news (Turkish, Chinese sources)
}
```

### 4.6.5 FinRobot Weekly Reports (Monitoring Enhancement)

**Purpose:** Auto-generate structured weekly strategy performance reports.

```python
# monitoring/finrobot_reports.py

REPORT_TEMPLATE = {
    "frequency": "weekly",
    "day": "Sunday",
    "sections": [
        "portfolio_summary",        # Total P&L, Sharpe, DD
        "per_inefficiency_review",  # Each active trade performance
        "signal_quality_metrics",   # Precision, recall by Layer 1 category
        "regime_analysis",          # Current market regime detection
        "upcoming_catalysts",       # Next week's expected events
        "optimization_suggestions", # FinRL reward signal trends
    ],
    "delivery": ["markdown_file", "telegram_summary"],
    "llm": "nousresearch/hermes-4",
}
```

### 4.6.6 Implementation Timeline

| Week | Task | Components |
|------|------|-----------|
| 1 | Clone repos, set up Python environments | TradingAgents, FinRL, QuantDinger, FinGPT |
| 2 | Configure TradingAgents with 4 supply chain analyst personas | TradingAgents + LangGraph |
| 3 | Build FinRL MT5 training environment with Pepperstone data | FinRL-Meta + MT5 API |
| 4 | Set up QuantDinger MCP bridge to MT5 | QuantDinger + MCP server |
| 5 | Fine-tune FinGPT on supply chain corpus | FinGPT + training data |
| 6 | Integration testing: agents → FinRL → QuantDinger → MT5 | Full pipeline |
| 7 | Backtest full agent pipeline on 2020-2026 data | All components |
| 8 | Paper trading with agent framework | Live signals, virtual execution |

### 4.6.7 Fallback Strategy

If agent-based framework proves too complex or unstable:

```
TIER 1 (Minimum viable): Rule-based scanner + MQL5 EA (original plan)
TIER 2 (Intermediate):   FinGPT sentiment + rule-based + MQL5 EA
TIER 3 (Full agent):     TradingAgents + FinRL + QuantDinger (target)
```

Start with TIER 1 for live trading, develop TIER 3 in parallel, switch when TIER 3 backtest beats TIER 1 by >20% Sharpe improvement.

---

# 5. PHASE 3: BACKTESTING

## 5.1 MT5 Strategy Tester Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| Model | Every tick based on real ticks | Most accurate (Pepperstone tick data) |
| Deposit | $10,000 | Normalized for comparison |
| Currency | USD | Match live account |
| Leverage | 1:30 | Match live leverage |
| Spread | Current (variable) | Realistic execution |
| Commission | $7/lot round trip | Pepperstone Razor commission |
| Execution | Instant | Pepperstone ECN |

## 5.2 Test Periods

| Period | Dates | Regime | Purpose | Data Points |
|--------|-------|--------|---------|-------------|
| **Period 1** | Jan 2020 — Dec 2021 | COVID supply shock | In-sample: Extreme disruptions, shipping crisis | Supply chain chaos, container shortage |
| **Period 2** | Jan 2022 — Dec 2023 | Ukraine war / inflation | In-sample: Commodity supercycle, energy crisis | Neon gas, wheat, energy disruption |
| **Period 3** | Jan 2024 — Dec 2025 | Normalization / China tension | Out-of-sample: Gallium ban, Red Sea attacks | China export controls, Houthi attacks |
| **Period 4** | Jan 2026 — Nov 2026 | Current regime | Walk-forward: Live validation | Real-time signals vs actual market |

### Period Selection Rationale

- **Period 1 (COVID):** Tests extreme supply shock scenarios. Container imbalance (#17), semiconductor shortage (#29, #30), copper surge (#38). Every supply chain strategy should show edge here.
- **Period 2 (Ukraine):** Tests geopolitical disruption. Neon gas (#30), wheat (#26), titanium (#11), energy (#19). Sanctions and export controls are the core thesis.
- **Period 3 (Normalization):** Out-of-sample test. If strategy only works in crises, it's not robust. Must still show positive expectancy during normalization.
- **Period 4 (Current):** Walk-forward validation. Uses the latest 12 months of data to confirm strategy adapts to current market regime.

## 5.3 Acceptance Criteria

| Metric | Minimum (Conservative) | Target (Moderate) | Stretch (Aggressive) |
|--------|----------------------|-------------------|---------------------|
| **Sharpe Ratio** | >1.0 | >1.5 | >2.0 |
| **Max Drawdown** | <15% | <12% | <10% |
| **Win Rate** | >48% | >52% | >55% |
| **Profit Factor** | >1.3 | >1.5 | >2.0 |
| **Recovery Factor** | >2.0 | >3.0 | >5.0 |
| **Avg Trade Duration** | 1-14 days | 2-10 days | 1-7 days |
| **Max Consecutive Losses** | <8 | <6 | <5 |
| **Monthly Win %** | >55% | >60% | >67% |
| **Expectancy ($/trade)** | >$15 | >$30 | >$50 |

### Hard Rejection Criteria (Any Period)

- Max drawdown > 25% → **REJECT**
- Sharpe < 0.5 → **REJECT**
- Profit factor < 1.1 → **REJECT**
- >10 consecutive losses → **REJECT**
- >3 months with negative return → **REJECT** (unless in clearly defined adverse regime)

## 5.4 Walk-Forward Optimization

```
┌─────────────────────────────────────────────────────┐
│         WALK-FORWARD OPTIMIZATION CYCLE              │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ OPTIMIZATION │→ │  OUT-OF-SAMPLE │→ │  VALIDATE  │ │
│  │  (12 months) │  │   (3 months)   │  │  (metrics) │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│         ↑                                    │       │
│         └────────────────────────────────────┘       │
│              Roll forward 3 months                   │
└─────────────────────────────────────────────────────┘

Window 1: Optimize Jan 2020 - Dec 2020 → Test Jan - Mar 2021
Window 2: Optimize Apr 2020 - Mar 2021 → Test Apr - Jun 2021
Window 3: Optimize Jul 2020 - Jun 2021 → Test Jul - Sep 2021
... (continue rolling)
Window N: Optimize Sep 2025 - Aug 2026 → Test Sep - Nov 2026
```

### Walk-Forward Efficiency Ratio

```
WFE = (Out-of-Sample Performance / In-Sample Performance) × 100%

Target: WFE > 50%
Good:   WFE > 65%
Excellent: WFE > 80%

If WFE < 30%: Strategy is overfit — reject and redesign
```

## 5.5 Per-Strategy Backtest Checklist

- [ ] Data integrity verified (no gaps, correct timezone)
- [ ] Commission and spread set to Pepperstone Razor rates
- [ ] Leverage matches live account (1:30 or 1:500)
- [ ] Slip page simulated (±2 pips for forex, ±5 pips for CFDs)
- [ ] Overnight swap/rollover costs included
- [ ] Period 1 (COVID) completed and logged
- [ ] Period 2 (Ukraine) completed and logged
- [ ] Period 3 (Normalization) completed — out-of-sample
- [ ] Period 4 (Current) completed — walk-forward
- [ ] Sharpe ratio ≥ minimum threshold across ALL periods
- [ ] Max drawdown ≤ maximum threshold in EVERY period
- [ ] Walk-forward efficiency ratio > 50%
- [ ] Equity curve visual inspection (smooth, no cliff drops)
- [ ] Trade distribution analysis (no outsized winners skewing results)
- [ ] Correlation with existing strategies < 0.5
- [ ] Results saved to `backtest/results/{strategy_name}_{date}.json`

---

# 6. PHASE 4: PAPER TRADING

## 6.1 Four-Week Phased Rollout

### Week 1: Foundation (Tier 1 Only)

| Parameter | Value |
|-----------|-------|
| Active Inefficiencies | Top 5: Copper (#38), Rare Earths (#8), Red Sea (#19), Gallium (#3), Uranium (#10) |
| Max Positions | 3 |
| Strategies | Commodity + Equity CFDs only |
| Signal Modes | Layer 1+2 only (no portfolio sizing) |
| Monitoring | Hourly manual checks |

**Week 1 Go/No-Go → Week 2:**
- [ ] Signal engine generating signals without errors for 5 consecutive days
- [ ] All data feeds (GDELT, FRED, Quandl) operational
- [ ] MT5 bridge executing paper trades successfully
- [ ] No false signals (obvious bad trades)
- [ ] Paper P&L tracking matches MT5 demo account

### Week 2: Expansion (Tier 1 + Tier 2)

| Parameter | Value |
|-----------|-------|
| Active Inefficiencies | Top 10 (add: Power Transformers #34, TSMC #29, Helium #1, Fishmeal #22, HVDC #35) |
| Max Positions | 5 |
| Strategies | Commodity + Equity + ETF CFDs |
| Signal Modes | Full 3-layer pipeline |
| Monitoring | Every 4 hours + daily review |

**Week 2 Go/No-Go → Week 3:**
- [ ] Position sizing producing reasonable lot sizes
- [ ] Correlation filter working (blocking correlated trades)
- [ ] Win rate ≥ 45% on paper trades
- [ ] No drawdown > 8% (paper)
- [ ] Daily report generating correctly

### Week 3: Full Universe + Forex Pairs

| Parameter | Value |
|-----------|-------|
| Active Inefficiencies | All 40 (minus #20 Vanilla, #36 Skilled Labor) |
| Max Positions | 8 |
| Strategies | All types including Forex pairs |
| Signal Modes | Full pipeline + event-driven |
| Monitoring | Automated alerts + twice-daily review |

**Week 3 Go/No-Go → Week 4:**
- [ ] Forex pair strategies executing correctly
- [ ] Event-driven signals (GDELT) triggering appropriately
- [ ] No more than 1 false alarm per day
- [ ] Portfolio diversification visible (≥3 sectors represented)
- [ ] Sharpe ratio > 0.8 (annualized from paper trades)

### Week 4: Stress Test + Full Portfolio

| Parameter | Value |
|-----------|-------|
| Active Inefficiencies | All tradeable (38) |
| Max Positions | 10 |
| Strategies | Full portfolio with event responses |
| Signal Modes | All layers + circuit breakers |
| Monitoring | Production monitoring stack |

**Week 4 Go/No-Go → LIVE:**
- [ ] Sharpe ratio > 1.0 (annualized, 4-week paper)
- [ ] Max drawdown < 10% (paper)
- [ ] Win rate > 50%
- [ ] Profit factor > 1.3
- [ ] All monitoring alerts tested and working
- [ ] Circuit breaker tested (simulated 10% DD)
- [ ] Daily reports generated automatically for 7 consecutive days
- [ ] No system crashes or data feed outages in 7 days

## 6.2 Daily Monitoring Checklist (Paper Trading)

```markdown
## Daily Paper Trading Review — [DATE]

### System Health
- [ ] MT5 connected and running
- [ ] Python signal engine running
- [ ] All data feeds active (GDELT, FRED, Quandl)
- [ ] Database recording signals and trades
- [ ] No error logs in past 24h

### Portfolio Status
- Equity: $_____ | Daily P&L: $_____ (___%)
- Open Positions: ___ / 10 max
- Sector Exposure: ___ sectors active
- Largest Position: ___% of equity
- Current Drawdown: ___% (max allowed: 10%)

### Signal Quality
- Signals Generated (L1): ___
- Signals Confirmed (L2): ___
- Signals Executed (L3): ___
- Rejection Reasons: ___

### Trades
| Ticket | Instrument | Direction | Entry | Current | P&L | Time Open |
|--------|-----------|-----------|-------|---------|-----|-----------|
| | | | | | | |

### News/Events
- Key events detected: ___
- Actions taken: ___
- Missed opportunities: ___

### Issues & Notes
- ___
```

## 6.3 Weekly Review Template

```markdown
## Weekly Paper Trading Review — Week [N] of [DATE RANGE]

### Performance Summary
| Metric | This Week | Cumulative | Target |
|--------|-----------|-----------|--------|
| Return | ___% | ___% | >0.5%/wk |
| Sharpe (ann.) | ___ | ___ | >1.0 |
| Win Rate | ___% | ___% | >50% |
| Profit Factor | ___ | ___ | >1.3 |
| Max DD | ___% | ___% | <10% |
| Trades Opened | ___ | ___ | — |
| Trades Closed | ___ | ___ | — |

### Best/Worst Trades
- Best: ___ (+$___ / +___%) — Reason: ___
- Worst: ___ (-$___ / -___%) — Reason: ___

### Signal Analysis
- Total L1 signals: ___
- L2 confirmation rate: ___% (target: 30-50%)
- L3 execution rate: ___% (target: 60-80% of confirmed)
- False positives identified: ___
- Missed opportunities: ___

### Inefficiency Activity
| Inefficiency | Signals | Trades | Win/Loss | Notes |
|-------------|---------|--------|----------|-------|
| #38 Copper | ___ | ___ | ___ | ___ |
| #8 Rare Earths | ___ | ___ | ___ | ___ |
| ... | | | | |

### Adjustments for Next Week
1. ___
2. ___
3. ___

### Go/No-Go Assessment
- [ ] All criteria met → Proceed to Week [N+1]
- [ ] Issues identified → Extend Week [N] by ___ days
- [ ] Critical failure → Return to Phase 3
```

---

# 7. PHASE 5: LIVE DEPLOYMENT

## 7.1 Staged Capital Deployment

### Stage A: Micro Lots ($5,000)

| Parameter | Value |
|-----------|-------|
| Capital | $5,000 |
| Lot Size | 0.01 (micro) |
| Max Positions | 5 |
| Max Position Size | 2.5% ($125) risk per trade |
| Duration | 4 weeks minimum |
| Commission Impact | ~$0.07 per micro lot per side |

**Stage A → Stage B Criteria:**
- [ ] Sharpe > 1.0 over 4 weeks
- [ ] Max drawdown < 15% ($750)
- [ ] Win rate > 48%
- [ ] No system failures
- [ ] Live fills within 2 pips of expected

### Stage B: Mini Lots ($15,000)

| Parameter | Value |
|-----------|-------|
| Capital | $15,000 |
| Lot Size | 0.1 (mini) |
| Max Positions | 8 |
| Max Position Size | 3.5% ($525) risk per trade |
| Duration | 4 weeks minimum |
| Commission Impact | ~$0.70 per mini lot per side |

**Stage B → Stage C Criteria:**
- [ ] Sharpe > 1.0 over 8 cumulative weeks
- [ ] Max drawdown < 12% ($1,800)
- [ ] Win rate > 50%
- [ ] Profit factor > 1.3
- [ ] Slippage average < 1.5 pips

### Stage C: Standard ($50,000+)

| Parameter | Value |
|-----------|-------|
| Capital | $50,000+ |
| Lot Size | 0.1 - 1.0 (variable) |
| Max Positions | 10 |
| Max Position Size | 5% ($2,500) risk per trade |
| Duration | Ongoing |
| Commission Impact | ~$3.50 per standard lot per side |

## 7.2 Risk Management Rules (Hard Limits)

| Rule | Limit | Action When Breached |
|------|-------|---------------------|
| Max single position | 5% of equity | Reduce immediately |
| Max sector exposure | 15% of equity | No new positions in sector |
| Max total exposure | 50% of equity (margin used) | No new positions |
| Max correlation | 0.70 between any 2 open positions | Close weaker one |
| Max daily loss | 3% of equity | Stop trading for day |
| Max weekly loss | 5% of equity | Reduce all positions 50% |
| Max drawdown | 10% of equity | **CLOSE ALL POSITIONS** |
| Max consecutive losses | 6 trades | Reduce size 50% for next 5 trades |
| Daily VaR | 2% of equity | No new positions |

## 7.3 Circuit Breakers

```python
# execution/risk_enforcer.py

class CircuitBreaker:
    """Hard circuit breakers that override all trading logic."""

    LEVELS = {
        "YELLOW": {  # Caution
            "drawdown_pct": 5.0,
            "action": "reduce_new_position_size_50pct",
            "resume": "manual_review"
        },
        "ORANGE": {  # Warning
            "drawdown_pct": 7.5,
            "action": "no_new_positions",
            "resume": "next_trading_day"
        },
        "RED": {  # Emergency
            "drawdown_pct": 10.0,
            "action": "close_all_positions_immediately",
            "resume": "manual_review_required"
        },
        "BLACK": {  # Catastrophic
            "drawdown_pct": 15.0,
            "action": "close_all_and_disable_ea",
            "resume": "full_system_review"
        }
    }

    VOLATILITY_BREAKER = {
        "vix_above_40": "reduce_all_positions_50pct",
        "flash_crash_detected": "close_all_market_orders",  # >5% move in <5 min
    }

    NEWS_BREAKER = {
        "black_swan_detected": "close_all_and_halt",  # GDELT score > 0.95
    }
```

## 7.4 Position Sizing Formulas

### Formula 1: Fixed Fractional (Default)

```
Position Size = (Equity × Risk%) / (Stop Distance in Pips × Pip Value)

Example (AUDUSD):
  Equity = $50,000
  Risk = 2% = $1,000
  Stop = 80 pips
  Pip Value = $10/pip (standard lot)
  Size = $1,000 / (80 × $10) = 0.125 lots → round to 0.12 lots
```

### Formula 2: Volatility-Adjusted (ATR-Based)

```
Position Size = (Equity × Risk%) / (ATR(14) × ATR_Multiplier × Pip Value)

ATR_Multiplier:
  - Low volatility (ATR < 50% of 6-month avg): 1.5x ATR
  - Normal volatility: 2.0x ATR
  - High volatility (ATR > 150% of 6-month avg): 3.0x ATR

Example (COPPER):
  Equity = $50,000
  Risk = 2% = $1,000
  ATR(14) = $0.08
  ATR_Mult = 2.0
  Stop = $0.08 × 2.0 = $0.16
  Pip Value = ~$250/lot for $0.01 move
  Size = $1,000 / ($0.16 × 250 × 100) = 0.025 lots → round to 0.02 lots
```

### Formula 3: Half-Kelly (Optimal Growth)

```
Kelly% = (Win_Rate × Avg_Win/Avg_Loss - (1 - Win_Rate)) / (Avg_Win/Avg_Loss)
Position Risk = Kelly% / 2  (Half-Kelly for safety)

Example:
  Win Rate = 55%
  Avg Win = $120
  Avg Loss = $80
  W/L Ratio = 1.5
  Kelly% = (0.55 × 1.5 - 0.45) / 1.5 = 0.25 = 25%
  Half-Kelly = 12.5% → Cap at 5% max
  Position Risk = 5% of equity
```

### Formula 4: Correlation-Adjusted

```
If adding a position correlated (ρ) with existing position:
  Adjusted Size = Base Size × (1 - |ρ|)

Example:
  FCX.US long (correlated with COPPER at ρ=0.85)
  Base size = 0.10 lots
  Adjusted = 0.10 × (1 - 0.85) = 0.015 lots → effectively blocked

  NTR.US long (correlated with WHEAT at ρ=0.30)
  Base size = 0.10 lots
  Adjusted = 0.10 × (1 - 0.30) = 0.07 lots → acceptable
```

---

# 8. CONTINUOUS: MONITORING

## 8.1 Real-Time Alerts Setup

### Alert Channels

| Channel | Tool | Use Case | Latency |
|---------|------|----------|---------|
| Telegram Bot | python-telegram-bot | Trade executions, circuit breakers | <5 sec |
| Email | SMTP | Daily reports, weekly reviews | <1 min |
| Grafana | Built-in | Dashboard threshold alerts | <30 sec |
| Desktop | Windows toast | Critical alerts | <2 sec |

### Alert Definitions

```python
# monitoring/alerter.py

ALERTS = {
    # CRITICAL — immediate action required
    "CIRCUIT_BREAKER_RED": {
        "condition": "drawdown > 10%",
        "channels": ["telegram", "email", "desktop"],
        "action": "Close all positions",
        "cooldown": 0  # no cooldown
    },
    "FLASH_CRASH": {
        "condition": "any position >5% adverse move in <5 min",
        "channels": ["telegram", "desktop"],
        "action": "Close affected position",
        "cooldown": 0
    },
    "MT5_DISCONNECTED": {
        "condition": "MT5 connection lost > 60 seconds",
        "channels": ["telegram", "desktop"],
        "action": "Attempt reconnection, then alert",
        "cooldown": 300  # 5 min
    },

    # HIGH — review within 1 hour
    "TRADE_EXECUTED": {
        "condition": "any trade opened or closed",
        "channels": ["telegram"],
        "action": "Log and monitor",
        "cooldown": 0
    },
    "DRAWDOWN_WARNING": {
        "condition": "drawdown > 5%",
        "channels": ["telegram"],
        "action": "Review open positions",
        "cooldown": 3600  # 1 hour
    },
    "HIGH_CORRELATION": {
        "condition": "new position ρ > 0.6 with existing",
        "channels": ["telegram"],
        "action": "Review portfolio",
        "cooldown": 3600
    },

    # MEDIUM — review at next daily check
    "SUPPLY_CHAIN_EVENT": {
        "condition": "GDELT score > 0.7 for monitored theme",
        "channels": ["telegram"],
        "action": "Queue signal check",
        "cooldown": 1800  # 30 min
    },
    "DATA_FEED_DOWN": {
        "condition": "any data source unresponsive > 30 min",
        "channels": ["telegram"],
        "action": "Switch to backup / cache",
        "cooldown": 1800
    },

    # INFO — daily digest
    "NEW_SIGNAL": {
        "condition": "Layer 1 signal generated",
        "channels": ["telegram"],
        "action": "Monitor for confirmation",
        "cooldown": 300
    },
    "DAILY_SUMMARY": {
        "condition": "18:00 UTC daily",
        "channels": ["telegram", "email"],
        "action": "Send daily report",
        "cooldown": 86400  # 24h
    },
}
```

### Telegram Bot Setup

```python
# monitoring/telegram_bot.py
import telegram
from telegram.ext import Application

BOT_TOKEN = "your_bot_token"
CHAT_ID = "your_chat_id"

async def send_alert(level: str, message: str):
    bot = telegram.Bot(token=BOT_TOKEN)
    emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "INFO": "🟢"}
    formatted = f"{emoji.get(level, '⚪')} [{level}] {message}"
    await bot.send_message(chat_id=CHAT_ID, text=formatted, parse_mode="Markdown")

async def send_trade_notification(trade: dict):
    msg = (
        f"{'🟢 OPENED' if trade['action'] == 'BUY' else '🔴 CLOSED'}\n"
        f"**{trade['instrument']}** {trade['direction']}\n"
        f"Price: {trade['price']} | Size: {trade['lot_size']}\n"
        f"SL: {trade['stop_loss']} | TP: {trade['take_profit']}\n"
        f"Inefficiency: #{trade['inefficiency_id']} {trade['name']}\n"
        f"Confidence: {trade['confidence']:.0%}"
    )
    await send_alert("HIGH", msg)
```

## 8.2 Daily Dashboard Metrics

| Metric | Source | Target | Red Flag |
|--------|--------|--------|----------|
| **Equity** | MT5 | Growing | Down >3% today |
| **Open Positions** | MT5 | 3-8 | 0 or >10 |
| **Unrealized P&L** | MT5 | Positive | >-3% equity |
| **Margin Used %** | MT5 | <30% | >50% |
| **Today's P&L** | DB | Positive | <-2% |
| **Sharpe (30-day)** | DB | >1.0 | <0.5 |
| **Win Rate (30-day)** | DB | >50% | <40% |
| **Max DD (current)** | DB | <5% | >7.5% |
| **Signals Generated** | DB | 5-20/day | 0 or >50 |
| **Signal Confirm Rate** | DB | 30-50% | <10% or >80% |
| **Data Feed Status** | Health check | All green | Any red |
| **MT5 Connection** | Health check | Connected | Disconnected |

## 8.3 Weekly Review Process

**Every Sunday 18:00 UTC:**

1. **Performance Review** (15 min)
   - Calculate weekly return, Sharpe, max DD
   - Compare to benchmark (S&P 500, DXY)
   - Identify best and worst trades

2. **Signal Quality Audit** (15 min)
   - Review false positives (signals that lost money)
   - Review missed opportunities (events that moved markets but no signal)
   - Calculate precision/recall for each inefficiency

3. **Risk Review** (10 min)
   - Check correlation matrix of open positions
   - Verify sector exposure limits
   - Review circuit breaker proximity

4. **Market Outlook** (10 min)
   - Upcoming macro events (FOMC, NFP, CPI, etc.)
   - Geopolitical watchlist updates
   - Supply chain news summary

5. **Action Items** (10 min)
   - Parameter adjustments needed?
   - New inefficiency developments?
   - System maintenance needed?

## 8.4 Supply Chain News Monitoring Workflow

### Source Priority

| Priority | Source | Check Frequency | Signal Weight |
|----------|--------|----------------|---------------|
| P0 | GDELT real-time | 5 min | 0.40 |
| P1 | Reuters Commodities RSS | 15 min | 0.25 |
| P2 | Mining.com RSS | 30 min | 0.15 |
| P3 | MarineTraffic API | 1 hour | 0.10 |
| P4 | USGS / FRED | Daily | 0.10 |

### RSS Feed List

```python
RSS_FEEDS = {
    "reuters_commodities": "https://www.reuters.com/markets/commodities/rss",
    "mining_dot_com": "https://www.mining.com/feed/",
    "gcaptain_shipping": "https://gcaptain.com/feed/",
    "world_nuclear_news": "https://www.world-nuclear-news.org/rss",
    "semiconductor_eng": "https://semiengineering.com/feed/",
    "eia_petroleum": "https://www.eia.gov/rss/todayinenergy.xml",
    "usda_crops": "https://www.usda.gov/rss/latest-releases.xml",
}
```

### News Processing Pipeline

```
Raw Article → Language Filter (EN only)
           → Keyword Match (40 inefficiency keyword sets)
           → FinBERT Sentiment Score
           → Relevance Score (0-1)
           → If score > 0.6: Queue for Layer 1 Scanner
           → If score > 0.8: Immediate alert
```

## 8.5 Geopolitical Event Response Playbook

See **[Appendix C](#appendix-c-event-response-playbook)** for detailed response plans.

Quick reference:

| Event Type | Response Time | Portfolio Action | Signal Override |
|-----------|--------------|-----------------|-----------------|
| China export ban | <30 min | Increase USDCNH, REMX, MP | Force Layer 1 RED |
| Strait closure (Hormuz/Malacca) | <15 min | Increase XTIUSD, tanker stocks | Force Layer 1 RED |
| Undersea cable cut | <1 hour | Increase cable/telecom stocks | Force Layer 1 ORANGE |
| Major mine disaster | <1 hour | Increase relevant commodity | Force Layer 1 ORANGE |
| Severe weather (agri) | <2 hours | Increase affected soft commodity | Force Layer 1 YELLOW |
| Political instability (producer) | <1 hour | Adjust FX pairs | Force Layer 1 ORANGE |
| Regulatory change | <4 hours | Review affected instruments | Force Layer 1 YELLOW |

---

# 9. CONTINUOUS: TESTING & EVALUATION

## 9.1 Monthly Strategy Performance Review Template

```markdown
## Monthly Strategy Review — [MONTH YEAR]

### Executive Summary
- Monthly Return: ___% ($_____)
- Benchmark (S&P 500): ___% | Alpha: ___% 
- Sharpe Ratio (annualized): ___
- Max Drawdown: ___%

### Strategy Breakdown

| Strategy / Inefficiency | Trades | Win% | P&L | Sharpe | Status |
|------------------------|--------|------|-----|--------|--------|
| #38 Copper Complex | ___ | ___% | $___ | ___ | Active |
| #8 Rare Earths | ___ | ___% | $___ | ___ | Active |
| #3 Gallium/Germanium | ___ | ___% | $___ | ___ | Active |
| #19 Red Sea/Suez | ___ | ___% | $___ | ___ | Active |
| #10 Uranium | ___ | ___% | $___ | ___ | Monitoring |
| Forex Basket | ___ | ___% | $___ | ___ | Active |
| ... | | | | | |

### Signal Quality Metrics
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total L1 Signals | ___ | 100-300/mo | ✓/✗ |
| L2 Confirmation Rate | ___% | 30-50% | ✓/✗ |
| L3 Execution Rate | ___% | 60-80% | ✓/✗ |
| True Positive Rate | ___% | >55% | ✓/✗ |
| False Positive Rate | ___% | <20% | ✓/✗ |

### Risk Metrics
| Metric | Value | Limit | Buffer |
|--------|-------|-------|--------|
| Max Drawdown (month) | ___% | 10% | ___% |
| Avg Daily VaR | ___% | 2% | ___% |
| Max Sector Exposure | ___% | 15% | ___% |
| Avg Correlation | ___ | <0.70 | ___ |
| Circuit Breaker Hits | ___ | 0 | — |

### Action Items
1. ___
2. ___
3. ___

### Strategy Status Changes
- [ ] Promote to Active: ___
- [ ] Demote to Monitoring: ___
- [ ] Retire: ___
```

## 9.2 Signal Quality Metrics

### Definitions

| Metric | Formula | Target | Meaning |
|--------|---------|--------|---------|
| **Precision** | TP / (TP + FP) | >0.55 | % of signals that were profitable |
| **Recall** | TP / (TP + FN) | >0.60 | % of profitable opportunities captured |
| **F1 Score** | 2 × (P × R) / (P + R) | >0.55 | Harmonic mean of precision & recall |
| **Accuracy** | (TP + TN) / Total | >0.55 | Overall correct predictions |
| **Specificity** | TN / (TN + FP) | >0.60 | % of no-trade decisions that were correct |

Where:
- **TP (True Positive):** Signal generated AND trade was profitable
- **FP (False Positive):** Signal generated BUT trade was unprofitable
- **FN (False Negative):** No signal BUT market moved in predicted direction
- **TN (True Negative):** No signal AND market didn't move

### Per-Inefficiency Quality Tracking

```python
# monitoring/signal_quality.py

class SignalQualityTracker:
    def calculate_metrics(self, inefficiency_id: int, period_days: int = 30) -> dict:
        signals = self.db.get_signals(inefficiency_id, days=period_days)
        trades = self.db.get_trades(inefficiency_id, days=period_days)
        events = self.db.get_events(inefficiency_id, days=period_days)

        tp = sum(1 for t in trades if t.profit > 0)
        fp = sum(1 for t in trades if t.profit <= 0)
        fn = self._count_missed_opportunities(inefficiency_id, period_days)
        tn = len(events) - (tp + fp + fn)  # Approximate

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "inefficiency_id": inefficiency_id,
            "period_days": period_days,
            "total_signals": len(signals),
            "total_trades": len(trades),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3),
            "status": self._recommend_status(f1, precision, len(trades))
        }

    def _recommend_status(self, f1, precision, trade_count):
        if trade_count < 5:
            return "INSUFFICIENT_DATA"
        if f1 > 0.60 and precision > 0.55:
            return "ACTIVE"
        if f1 > 0.45:
            return "MONITORING"
        return "REVIEW_FOR_RETIREMENT"
```

## 9.3 Execution Quality Analysis

### Metrics Tracked

| Metric | Calculation | Target | Action if Breached |
|--------|------------|--------|-------------------|
| **Slippage (avg)** | Fill Price - Expected Price | <1.5 pips (FX), <3 pips (CFD) | Review execution timing |
| **Slippage (max)** | Worst single fill | <5 pips (FX), <10 pips (CFD) | Flag for review |
| **Fill Rate** | Filled / Attempted | >98% | Check liquidity windows |
| **Latency** | Signal → Order → Fill | <2 seconds | Optimize code path |
| **Partial Fills** | Partial / Total | <5% | Reduce order size |
| **Requote Rate** | Requotes / Attempts | <2% | Use market orders |

### Execution Quality Report

```python
def execution_quality_report(period_days=30):
    trades = db.get_trades(days=period_days)

    slippage = [t.fill_price - t.expected_price for t in trades]
    avg_slippage = np.mean(np.abs(slippage))
    max_slippage = np.max(np.abs(slippage))
    fill_rate = sum(1 for t in trades if t.status == 'FILLED') / len(trades)
    avg_latency = np.mean([t.fill_time - t.signal_time for t in trades])

    return {
        "avg_slippage_pips": round(avg_slippage, 2),
        "max_slippage_pips": round(max_slippage, 2),
        "fill_rate": round(fill_rate, 4),
        "avg_latency_ms": round(avg_latency * 1000, 1),
        "total_commission": sum(t.commission for t in trades),
        "commission_pct_of_profit": total_commission / total_profit * 100,
    }
```

## 9.4 Strategy Degradation Detection

### Detection Methods

| Method | Check | Threshold | Action |
|--------|-------|-----------|--------|
| **Rolling Sharpe** | 30-day rolling Sharpe ratio | Falls below 0.5 for 2 consecutive weeks | Reduce position size 50% |
| **Win Rate Drift** | 30-day rolling win rate | Falls below 40% | Move to MONITORING |
| **Profit Factor Decay** | 30-day rolling PF | Falls below 1.0 | Suspend new trades |
| **Drawdown Duration** | Days in drawdown | >30 consecutive days | Full strategy review |
| **Correlation Shift** | Strategy ↔ SPX correlation | Rises above 0.6 (was <0.3) | Alpha erosion — review |
| **Signal Frequency** | Signals per week | >2x or <0.5x normal | Data feed issue or market regime change |

### Automated Degradation Response

```python
class DegradationDetector:
    def check_all_strategies(self):
        for strategy in self.active_strategies:
            metrics = self.calculate_rolling_metrics(strategy, window=30)

            if metrics['sharpe'] < 0.5 and metrics['prev_sharpe'] < 0.5:
                self.alert("DEGRADATION", f"{strategy.name}: Sharpe below 0.5 for 2 weeks")
                self.reduce_size(strategy, factor=0.5)

            if metrics['win_rate'] < 0.40:
                self.alert("DEGRADATION", f"{strategy.name}: Win rate {metrics['win_rate']:.0%}")
                self.move_to_monitoring(strategy)

            if metrics['profit_factor'] < 1.0:
                self.alert("DEGRADATION", f"{strategy.name}: PF {metrics['profit_factor']:.2f}")
                self.suspend(strategy)

            if metrics['dd_duration_days'] > 30:
                self.alert("DEGRADATION", f"{strategy.name}: {metrics['dd_duration_days']}d in DD")
                self.flag_for_review(strategy)
```

## 9.5 A/B Testing Framework for New Signals

### A/B Test Process

```
1. HYPOTHESIS: "Adding [new data source/indicator] improves signal quality for [inefficiency]"
2. DESIGN:
   - Control (A): Current signal configuration
   - Treatment (B): Current + new signal component
   - Duration: Minimum 30 trades or 60 days (whichever comes first)
   - Allocation: 50/50 random split of signal events
3. METRICS:
   - Primary: Profit Factor difference
   - Secondary: Sharpe ratio, win rate, avg trade P&L
4. ANALYSIS:
   - Chi-squared test for win rate difference (p < 0.05)
   - t-test for avg P&L difference (p < 0.05)
   - Bootstrap confidence intervals for Sharpe ratio
5. DECISION:
   - If B significantly better: Promote B → new Control
   - If no difference: Reject B (avoid complexity)
   - If B worse: Reject B definitively
```

### A/B Test Tracking Table

| Test ID | Hypothesis | Inefficiency | Start Date | End Date | A Metric | B Metric | p-value | Decision |
|---------|-----------|-------------|------------|----------|----------|----------|---------|----------|
| AB-001 | GDELT + MarineTraffic for Red Sea | #19 | — | — | — | — | — | — |
| AB-002 | FinBERT v2 for Copper signals | #38 | — | — | — | — | — | — |
| AB-003 | Add ADX filter for Forex pairs | All FX | — | — | — | — | — | — |

---

# 10. CONTINUOUS: OPTIMIZATION

## 10.1 Walk-Forward Optimization Schedule

| Cycle | Frequency | In-Sample | Out-of-Sample | Parameters Optimized |
|-------|-----------|-----------|---------------|---------------------|
| **Entry Parameters** | Monthly | 12 months | 3 months | Signal thresholds, indicator periods |
| **Exit Parameters** | Monthly | 12 months | 3 months | Stop multipliers, take-profit ratios |
| **Risk Parameters** | Quarterly | 18 months | 6 months | Position size limits, sector caps |
| **Filter Parameters** | Quarterly | 18 months | 6 months | Confirmation weights, correlation limits |
| **Full System** | Semi-annually | 24 months | 6 months | All parameters simultaneously |

### Optimization Process

```
For each parameter group:
1. Define search space (min, max, step for each parameter)
2. Run genetic optimization on in-sample period
3. Top 10 parameter sets → run on out-of-sample
4. Select set with BEST out-of-sample Sharpe (not in-sample!)
5. Calculate Walk-Forward Efficiency (WFE)
6. If WFE > 50%: Deploy new parameters
7. If WFE 30-50%: Deploy with reduced position sizes
8. If WFE < 30%: Keep old parameters, investigate overfitting
```

## 10.2 Parameter Groups and Tuning Frequency

### Entry Parameters (Monthly Tuning)

| Parameter | Current | Range | Step | Last Optimized |
|-----------|---------|-------|------|----------------|
| GDELT alert threshold | 0.70 | 0.50-0.90 | 0.05 | — |
| FinBERT sentiment threshold | -0.50 | -0.80 to -0.20 | 0.05 | — |
| RSI oversold level | 30 | 20-40 | 2 | — |
| RSI overbought level | 70 | 60-80 | 2 | — |
| MACD fast period | 12 | 8-16 | 1 | — |
| MACD slow period | 26 | 20-32 | 1 | — |
| Price breakout % | 5.0% | 2-10% | 0.5 | — |
| Volume surge multiplier | 1.5x | 1.2-3.0x | 0.1 | — |

### Exit Parameters (Monthly Tuning)

| Parameter | Current | Range | Step | Last Optimized |
|-----------|---------|-------|------|----------------|
| Stop loss ATR multiplier | 2.0 | 1.0-4.0 | 0.25 | — |
| Take profit ATR multiplier | 4.0 | 2.0-8.0 | 0.5 | — |
| Trailing stop activation (ATR) | 2.0 | 1.0-4.0 | 0.25 | — |
| Trailing stop distance (ATR) | 1.0 | 0.5-2.0 | 0.25 | — |
| Max hold time (days) | 14 | 5-30 | 1 | — |
| Profit lock-in % | 50% | 25-75% | 5% | — |

### Risk Parameters (Quarterly Tuning)

| Parameter | Current | Range | Step | Last Optimized |
|-----------|---------|-------|------|----------------|
| Max single position % | 5.0% | 2-8% | 0.5% | — |
| Max sector exposure % | 15.0% | 10-20% | 1% | — |
| Max positions | 10 | 5-15 | 1 | — |
| Max correlation allowed | 0.70 | 0.50-0.85 | 0.05 | — |
| Circuit breaker DD % | 10.0% | 7-15% | 0.5% | — |
| Daily VaR limit % | 2.0% | 1-3% | 0.25% | — |
| Kelly fraction | 0.50 | 0.25-0.75 | 0.05 | — |

### Filter Parameters (Quarterly Tuning)

| Parameter | Current | Range | Step | Last Optimized |
|-----------|---------|-------|------|----------------|
| Technical weight | 0.35 | 0.20-0.50 | 0.05 | — |
| Fundamental weight | 0.35 | 0.20-0.50 | 0.05 | — |
| Sentiment weight | 0.30 | 0.10-0.40 | 0.05 | — |
| Confirmation threshold | 0.60 | 0.40-0.80 | 0.05 | — |
| Min pillars passed | 2 | 1-3 | 1 | — |
| ADX trending threshold | 25 | 15-35 | 2 | — |
| VIX fear threshold | 30 | 20-40 | 2 | — |

## 10.3 Regime Detection and Adaptation

### Market Regimes

| Regime | Detection Criteria | Portfolio Adjustment |
|--------|-------------------|---------------------|
| **Risk-On** | VIX <18, DXY falling, SPX >200-DMA | Full allocation, favor commodity longs |
| **Risk-Off** | VIX >25, DXY rising, SPX <200-DMA | Reduce to 60%, favor USD longs, gold |
| **Supply Shock** | GDELT supply theme count >2x avg | Increase to 120% (leveraged), event-driven trades |
| **Range/Neutral** | VIX 18-25, DXY flat, low GDELT activity | Reduce to 80%, tighter stops |

### Regime Detection Implementation

```python
class RegimeDetector:
    """Detect current market regime from macro indicators."""

    def detect(self) -> str:
        vix = self.get_vix()
        dxy_vs_200dma = self.get_dxy_vs_dma(200)
        spx_vs_200dma = self.get_spx_vs_dma(200)
        gdelt_activity = self.get_gdelt_supply_activity()

        # Supply Shock takes priority
        if gdelt_activity > 2.0:  # 2x normal
            return "SUPPLY_SHOCK"

        if vix < 18 and dxy_vs_200dma < 0 and spx_vs_200dma > 0:
            return "RISK_ON"

        if vix > 25 and dxy_vs_200dma > 0 and spx_vs_200dma < 0:
            return "RISK_OFF"

        return "RANGE"

    def get_allocation_multiplier(self, regime: str) -> float:
        return {
            "RISK_ON": 1.0,
            "RISK_OFF": 0.6,
            "SUPPLY_SHOCK": 1.2,
            "RANGE": 0.8,
        }[regime]
```

### Regime-Specific Parameter Overrides

| Parameter | Risk-On | Risk-Off | Supply Shock | Range |
|-----------|---------|----------|-------------|-------|
| Max positions | 10 | 6 | 10 | 8 |
| Single pos. max | 5% | 3% | 5% | 4% |
| Stop ATR mult. | 2.0 | 2.5 | 1.5 | 2.0 |
| TP ATR mult. | 4.0 | 3.0 | 6.0 | 3.0 |
| Confirmation threshold | 0.60 | 0.70 | 0.50 | 0.65 |
| Sentiment weight | 0.30 | 0.35 | 0.40 | 0.25 |

## 10.4 New Inefficiency Integration Process

### Step-by-Step Process

```
1. IDENTIFY
   - Source: News, research papers, USGS reports, industry analysis
   - Criteria: Single-source >40% OR geographic concentration >60%
   - Log in inefficiency_candidates table

2. VALIDATE (1-2 weeks)
   - Confirm supply concentration data from 2+ sources
   - Identify tradeable instruments on Pepperstone
   - Calculate potential trade frequency (>2 trades/quarter minimum)
   - Assess data availability for monitoring

3. BUILD (1-2 weeks)
   - Define trigger conditions (EVENT, PRICE, DATA types)
   - Add keywords to GDELT monitor
   - Add to Layer 1 scanner
   - Define confirmation rules for Layer 2
   - Calculate correlations with existing inefficiencies

4. BACKTEST (2-4 weeks)
   - Run through all 4 test periods
   - Must meet minimum acceptance criteria
   - Walk-forward efficiency > 50%

5. PAPER TEST (2-4 weeks)
   - Add to paper trading in MONITORING status
   - Generate signals but don't execute
   - Track hypothetical P&L

6. PROMOTE (decision point)
   - If paper P&L positive with Sharpe >0.8: Promote to ACTIVE
   - If inconclusive: Extend paper test
   - If negative: Park in RETIRED

7. INTEGRATE
   - Update correlation matrix
   - Check sector exposure limits
   - Deploy to live signal engine
   - Start with 50% normal position size for 2 weeks
```

## 10.5 Strategy Retirement Criteria

### Automatic Retirement Triggers

| Trigger | Condition | Grace Period |
|---------|-----------|-------------|
| Negative Sharpe | Rolling 90-day Sharpe < 0 | 30 days |
| Consistent Losses | 3 consecutive months negative | Immediate |
| Win Rate Collapse | Rolling 60-day win rate < 35% | 14 days |
| No Signals | Zero L1 signals for 90 days | 30 days |
| Structural Change | Supply concentration drops below 30% | 30 days |
| Instrument Delisted | Pepperstone removes instrument | Immediate |

### Retirement Process

```
1. Move strategy status to RETIRED
2. Close all open positions (at market, not limit)
3. Generate final performance report
4. Archive all signals and trade data
5. Remove from active scanner rotation
6. Keep in monitoring (GREEN level) for 6 months
7. If supply concentration re-emerges: Begin revalidation
8. After 6 months with no reactivation: Archive completely
```

---

# APPENDIX A: ALL 40 INEFFICIENCY TRADE CARDS

---

## Trade Card #1: HELIUM

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | Global helium supply concentrated in US (40%) and Qatar (25%). Used in MRI, semiconductors, space, fiber optics. No synthetic substitute. |
| **Supply Concentration** | US BLM 40%, Qatar 25%, Algeria 10%, Russia 8% |
| **Trigger Scenarios** | US BLM plant shutdown; Qatar diplomatic crisis; Pipeline disruption; Semiconductor demand surge |
| **Primary Instruments** | `LIN.US` (Linde), `APD.US` (Air Products) |
| **Proxy Instruments** | None needed — direct equity plays |
| **Entry Rules** | BUY `LIN.US` or `APD.US` when: GDELT helium/gas shortage score >0.7 AND RSI(14) <45 AND FinBERT sentiment <-0.3 on helium news |
| **Exit Rules** | TP: 2.5x ATR(14) from entry | SL: 1.5x ATR(14) | Time stop: 14 days |
| **Position Sizing** | Max 3% equity per position, 5% combined |
| **Correlations** | LIN ↔ APD: 0.78 (take only 1) |
| **Backtest Results** | *Placeholder — to be filled after Phase 3* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #2: ANTIMONY

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | China produces 48% of global antimony. Used in flame retardants, batteries, military ammunition. |
| **Supply Concentration** | China 48%, Tajikistan 12%, Russia 8%, Myanmar 7% |
| **Trigger Scenarios** | China export restriction; Myanmar conflict; Military demand surge; Environmental crackdown in China |
| **Primary Instruments** | `USDCNH` (short = CNH strength on export ban), `REMX.US` (rare earth miners ETF) |
| **Proxy Instruments** | `AUDUSD` (long = commodity currency) |
| **Entry Rules** | SHORT `USDCNH` when: China antimony export ban announced AND USDCNH >7.20 AND MACD bearish cross |
| **Exit Rules** | TP: 200 pips | SL: 120 pips | Time stop: 7 days |
| **Position Sizing** | Max 3% equity |
| **Correlations** | USDCNH ↔ AUDUSD: -0.52 (can pair) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #3: GALLIUM / GERMANIUM

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | China controls 80% of gallium and 60% of germanium production. Critical for semiconductors, fiber optics, solar cells, military IR systems. China implemented export controls in 2023. |
| **Supply Concentration** | China: Ga 80%, Ge 60% |
| **Trigger Scenarios** | China export ban expansion; US-China tech war escalation; Ga/Ge inventory depletion; Semiconductor shortage |
| **Primary Instruments** | `USDCNH` (short), `REMX.US` (long), `SOXX.US` (short on shortage) |
| **Proxy Instruments** | `INTC.US` (short — most exposed to shortage), `AUDUSD` (long) |
| **Entry Rules** | **Scenario A (Export Ban):** SHORT `USDCNH` + LONG `REMX.US` when GDELT China+Gallium score >0.8 | **Scenario B (Shortage):** SHORT `SOXX.US` when Ga/Ge inventory <3mo supply AND RSI(14) >65 |
| **Exit Rules** | Scenario A: TP 250 pips / 8% REMX | SL 150 pips / 5% | Scenario B: TP 5% | SL 3% |
| **Position Sizing** | Max 4% equity combined (China Minerals group cap 15%) |
| **Correlations** | REMX ↔ SOXX: 0.42 (mild — can hold both); USDCNH ↔ REMX: -0.35 (pair trade OK) |
| **Backtest Results** | *Placeholder — 2023 Ga/Ge ban is key in-sample event* |
| **Status** | 🟢 ACTIVE (Tier 1 — Top 10 opportunity, score 9.7/10) |

---

## Trade Card #4: GRAPHITE

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | China produces 65% of global graphite. Critical for EV battery anodes, steel, nuclear reactors. China implemented export controls in late 2023. |
| **Supply Concentration** | China 65%, Mozambique 8%, Brazil 7% |
| **Trigger Scenarios** | China export controls tightened; EV demand surge; Mine disruption in Mozambique |
| **Primary Instruments** | `USDCNH` (short on ban), `AUDUSD` (long — Australia alt. supplier) |
| **Proxy Instruments** | None direct — graphite is not a separately traded commodity on Pepperstone |
| **Entry Rules** | SHORT `USDCNH` when China graphite export controls announced AND USDCNH MACD bearish |
| **Exit Rules** | TP: 180 pips | SL: 100 pips | Time stop: 10 days |
| **Position Sizing** | Max 2% equity |
| **Correlations** | Shares China Minerals group with #2, #3, #6, #8, #12, #40 |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #5: MANGANESE

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | South Africa (28%) and Gabon (23%) dominate manganese production. Essential for steel production, batteries. |
| **Supply Concentration** | S.Africa 28%, Gabon 23%, Australia 15%, China 10% |
| **Trigger Scenarios** | S.Africa power crisis / mining strikes; Gabon political coup; Port disruption at Richards Bay |
| **Primary Instruments** | `USDZAR` (long on SA disruption), `BHP.US` (long — mining diversified exposure) |
| **Proxy Instruments** | `AUDUSD` (long — Australia alt supplier benefits) |
| **Entry Rules** | LONG `USDZAR` when: SA mining strike/power cut AND USDZAR RSI(14) <65 AND Bollinger <upper band |
| **Exit Rules** | TP: 300 pips | SL: 180 pips | Time stop: 14 days |
| **Position Sizing** | Max 3% equity |
| **Correlations** | USDZAR ↔ AUDUSD: -0.40 (can pair for hedge) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #6: FLUORSPAR

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | China produces 64% of fluorspar. Used in aluminum smelting, steelmaking, refrigerants, uranium processing. |
| **Supply Concentration** | China 64%, Mexico 12%, Mongolia 6% |
| **Trigger Scenarios** | China fluoride chemical export controls; Environmental production cuts; Demand surge for refrigerants |
| **Primary Instruments** | `USDCNH` (short), `VALE.US` (long — diversified miner) |
| **Proxy Instruments** | None — limited tradeable exposure |
| **Entry Rules** | SHORT `USDCNH` on China fluorspar restriction + confirmation from Layer 2 |
| **Exit Rules** | TP: 150 pips | SL: 100 pips | Time stop: 7 days |
| **Position Sizing** | Max 2% equity (China Minerals group) |
| **Correlations** | Part of China Minerals group — see #3 |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #7: PHOSPHATE ROCK

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | Morocco (OCP Group) holds 70% of global phosphate reserves. Critical for fertilizers → global food security. |
| **Supply Concentration** | Morocco 70% (reserves), China 24% (production), US 3% |
| **Trigger Scenarios** | Morocco political instability / OCP disruption; China phosphate export halt; Global food crisis escalation |
| **Primary Instruments** | `MOS.US` (Mosaic — long), `NTR.US` (Nutrien — long) |
| **Proxy Instruments** | `WHEAT` (long — fertilizer costs → food prices) |
| **Entry Rules** | LONG `MOS.US` when: DAP fertilizer price >$600/t AND RSI(14) <50 AND MACD bullish cross |
| **Exit Rules** | TP: 8% | SL: 5% | Time stop: 21 days |
| **Position Sizing** | Max 3% equity per name, 5% combined (Agriculture sector) |
| **Correlations** | MOS ↔ NTR: 0.72 (take only 1); MOS ↔ WHEAT: 0.35 |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #8: RARE EARTH REFINING

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | China controls 90%+ of rare earth refining and processing. Critical for EV motors, wind turbines, military systems, consumer electronics. |
| **Supply Concentration** | China 90% (refining), 60% (mining) |
| **Trigger Scenarios** | China RE export ban; US-China military tension; EV subsidy surge; New Western RE processing capacity announcements |
| **Primary Instruments** | `USDCNH` (short), `REMX.US` (long), `MP.US` (long — only US RE mine) |
| **Proxy Instruments** | `AUDUSD` (long — Lynas in Australia) |
| **Entry Rules** | **Event:** LONG `MP.US` + LONG `REMX.US` when GDELT China+RE score >0.8 AND RSI(14) <55 | **Structural:** LONG `MP.US` when MP RSI(14) <30 on no negative news (deep value) |
| **Exit Rules** | TP: 10% (MP), 7% (REMX) | SL: 5% | Trailing: 1.5x ATR after 5% profit |
| **Position Sizing** | Max 4% equity per position, China Minerals sector cap 15% |
| **Correlations** | MP ↔ REMX: 0.65 (moderate — size accordingly); USDCNH ↔ REMX: -0.35 |
| **Backtest Results** | *Placeholder — 2023 China RE restrictions are key test* |
| **Status** | 🟢 ACTIVE (Tier 1 — Top 10 opportunity, score 9.7/10) |

---

## Trade Card #9: COBALT

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | DRC produces 74% of global cobalt. Critical for lithium-ion batteries, superalloys, catalysts. Artisanal mining and conflict mineral risks. |
| **Supply Concentration** | DRC 74%, Indonesia 5%, Philippines 4%, Russia 4% |
| **Trigger Scenarios** | DRC civil unrest / mine nationalization; Supply route disruption (Lobito corridor); ESG-driven supply constraints; EV demand acceleration |
| **Primary Instruments** | `COPPER` (long — co-product proxy), `USDCNH` (short — China is main processor) |
| **Proxy Instruments** | No direct cobalt CFD on Pepperstone |
| **Entry Rules** | LONG `COPPER` when: DRC mining disruption AND Copper RSI(14) <45 AND LME copper inventory declining |
| **Exit Rules** | TP: $0.30/lb above entry | SL: $0.15 below entry | Time stop: 14 days |
| **Position Sizing** | Max 3% equity, Copper Complex cap 15% |
| **Correlations** | COPPER ↔ AUDUSD: 0.72 (don't double up) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #10: URANIUM ENRICHMENT

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | Russia controls 35-40% of global uranium enrichment capacity (TENEX/Rosatom). Nuclear renaissance + sanctions create structural shortage. |
| **Supply Concentration** | Russia 35-40% (enrichment), Kazakhstan 43% (mining) |
| **Trigger Scenarios** | Russia enrichment sanctions; New nuclear plant approvals; Kazakhstan political instability; US/EU enrichment facility delays |
| **Primary Instruments** | `CCJ.US` (Cameco — long), `URA.US` (uranium ETF — long), `USDCAD` (short — Canadian uranium) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | LONG `CCJ.US` when: URA breaks above 52-week high AND RSI(14) <65 AND FinBERT uranium sentiment >0.3 | LONG `URA.US` for broad exposure when sector thesis intact |
| **Exit Rules** | TP: 12% (CCJ), 8% (URA) | SL: 6% | Trailing: 2x ATR after 6% profit |
| **Position Sizing** | Max 4% CCJ, 3% URA, combined 7% max (Energy sector cap 15%) |
| **Correlations** | CCJ ↔ URA: 0.85 (pick one or size down); CCJ ↔ USDCAD: -0.30 |
| **Backtest Results** | *Placeholder — test against 2022+ nuclear revival* |
| **Status** | 🟢 ACTIVE (Tier 1 — Top 10 opportunity, score 8.5/10) |

---

## Trade Card #11: TITANIUM SPONGE

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | China (55%) and Japan (19%) dominate titanium sponge production. Critical for aerospace (Boeing, Airbus), military, medical implants. |
| **Supply Concentration** | China 55%, Japan 19%, Russia 13%, Kazakhstan 8% |
| **Trigger Scenarios** | Russia titanium supply cut (sanctions); China production halt; Boeing/Airbus production ramp; Japan earthquake |
| **Primary Instruments** | `USDCNH` (short), `USDJPY` (depends on scenario) |
| **Proxy Instruments** | Aerospace equities: `BA.US` (Boeing), `LMT.US` (Lockheed) — but these are multi-factor |
| **Entry Rules** | SHORT `USDCNH` on China titanium restriction | LONG `USDJPY` on Japan earthquake disruption |
| **Exit Rules** | TP: 150 pips | SL: 100 pips | Time stop: 7 days |
| **Position Sizing** | Max 2% equity |
| **Correlations** | Part of China Minerals group |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #12: MAGNESIUM

| Field | Detail |
|-------|--------|
| **Category** | Energy / Mining |
| **Description** | China produces 87% of global magnesium. Used in automotive (lightweight alloys), steel desulfurization, aerospace. 2021 China energy crisis caused global Mg shortage. |
| **Supply Concentration** | China 87%, Russia 3%, Israel 3%, Turkey 2% |
| **Trigger Scenarios** | China energy rationing (repeat of 2021); Environmental shutdowns; Export tax/ban; Winter heating demand crunch |
| **Primary Instruments** | `USDCNH` (short), `VALE.US` (long — diversified miner) |
| **Proxy Instruments** | Auto manufacturers: `F.US` (Ford), `GM.US` (short — supply disrupted) |
| **Entry Rules** | SHORT `USDCNH` when: China Mg production cut >20% AND GDELT China+Magnesium score >0.7 |
| **Exit Rules** | TP: 200 pips | SL: 120 pips | Time stop: 10 days |
| **Position Sizing** | Max 2% equity (China Minerals cap 15%) |
| **Correlations** | Shares China Minerals group |
| **Backtest Results** | *Placeholder — 2021 Mg crisis is key event* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #13: POTASH

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Canada (31%), Russia (20%), Belarus (18%) control potash. Essential fertilizer — no substitute. Sanctions on Belarus/Russia created shortage in 2022. |
| **Supply Concentration** | Canada 31%, Russia 20%, Belarus 18% |
| **Trigger Scenarios** | Russia/Belarus sanction escalation; Canadian mine disruption; Indian/China contract negotiations; Global food crisis |
| **Primary Instruments** | `NTR.US` (Nutrien — long), `MOS.US` (Mosaic — long), `USDCAD` (short — Canadian potash exports boost CAD) |
| **Proxy Instruments** | `WHEAT` (long — fertilizer → food price chain) |
| **Entry Rules** | LONG `NTR.US` when: Potash spot >$400/t AND NTR RSI(14) <50 AND FinBERT fertilizer sentiment <-0.2 (supply fear) |
| **Exit Rules** | TP: 10% | SL: 5% | Time stop: 21 days |
| **Position Sizing** | Max 3% per name, Agriculture sector cap 12% |
| **Correlations** | NTR ↔ MOS: 0.72 (pick one); NTR ↔ WHEAT: 0.30 |
| **Backtest Results** | *Placeholder — 2022 Belarus sanctions are key* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #14: SEED GENETICS

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Top 4 companies (Bayer/Monsanto, Corteva, Syngenta/ChemChina, BASF) control 60%+ of global seed market. IP-protected genetics drive yields. |
| **Supply Concentration** | Top 4 = 60%+ of commercial seed market |
| **Trigger Scenarios** | Major crop failure linked to monoculture genetics; Merger/acquisition in seed sector; GMO regulatory changes; Patent cliff on key traits |
| **Primary Instruments** | `DE.US` (Deere — long, farm equipment proxy), `CTVA.US` (Corteva — long) |
| **Proxy Instruments** | None — direct equity plays |
| **Entry Rules** | LONG `CTVA.US` when: Crop failure news AND CTVA RSI(14) <40 AND positive earnings momentum |
| **Exit Rules** | TP: 8% | SL: 4% | Time stop: 30 days |
| **Position Sizing** | Max 3% equity, Agriculture sector cap 12% |
| **Correlations** | CTVA ↔ DE: 0.55; CTVA ↔ MOS: 0.40 |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #15: POLLINATION SERVICES

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | California produces 80% of global almonds. Dependent on managed honeybee pollination — highly concentrated service. Colony Collapse Disorder (CCD) is ongoing risk. |
| **Supply Concentration** | California 80% (almonds); commercial bee services highly concentrated |
| **Trigger Scenarios** | Colony Collapse Disorder outbreak; California wildfire/drought; Almond price spike; Neonicotinoid pesticide ban |
| **Primary Instruments** | `DAR.US` (Darling Ingredients — processing proxy) |
| **Proxy Instruments** | Limited direct plays |
| **Entry Rules** | LONG `DAR.US` on bee colony collapse news + almond supply fear IF RSI(14) <45 |
| **Exit Rules** | TP: 7% | SL: 4% | Time stop: 21 days |
| **Position Sizing** | Max 2% equity |
| **Correlations** | Low correlation with other inefficiencies |
| **Backtest Results** | *Placeholder* |
| **Status** | ⚪ LOW PRIORITY (limited trade frequency) |

---

## Trade Card #16: REFRIGERANT GASES

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | China produces ~60% of HFC refrigerants. Kigali Amendment phasedown + Chinese dominance = supply risk for HVAC industry globally. |
| **Supply Concentration** | China ~60% of HFC production |
| **Trigger Scenarios** | China HFC production quota; Kigali phasedown deadline; Summer heatwave + AC demand surge; New eco-refrigerant mandate |
| **Primary Instruments** | `USDCNH` (short), `HON.US` (Honeywell — long, next-gen refrigerants), `CARR.US` (Carrier — long, HVAC leader) |
| **Proxy Instruments** | All direct on Pepperstone |
| **Entry Rules** | LONG `HON.US` or `CARR.US` when: China HFC quota announced AND HON RSI(14) <50 AND MACD bullish |
| **Exit Rules** | TP: 7% | SL: 4% | Time stop: 21 days |
| **Position Sizing** | Max 3% per name |
| **Correlations** | HON ↔ CARR: 0.55 (can hold both with reduced size) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #17: CONTAINER IMBALANCE

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | 70% of containerized trade flows Asia → West. Massive imbalance = empty container repositioning costs. SCFI index is key barometer. |
| **Supply Concentration** | Asia export dominance 70%+ of global container volume |
| **Trigger Scenarios** | Port congestion event; Container shortage (COVID repeat); SCFI spike; Labor strike at major port |
| **Primary Instruments** | `ZIM.US` (ZIM Shipping — long), `MATX.US` (Matson — long) |
| **Proxy Instruments** | Shipping rate proxies |
| **Entry Rules** | LONG `ZIM.US` when: SCFI >3000 AND ZIM RSI(14) <50 AND MACD bullish cross |
| **Exit Rules** | TP: 15% (ZIM is volatile) | SL: 8% | Time stop: 14 days |
| **Position Sizing** | Max 3% equity, Shipping sector cap 12% |
| **Correlations** | ZIM ↔ MATX: 0.65; ZIM ↔ STNG: 0.40 |
| **Backtest Results** | *Placeholder — 2021 container crisis is key* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #18: PANAMA CANAL

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Panama Canal handles 5% of global trade, 40% of US container traffic. Drought reduces draft limits → fewer transits → shipping cost surge. |
| **Supply Concentration** | Single chokepoint — no alternative (except Suez + extra distance) |
| **Trigger Scenarios** | Drought / low water levels; Transit restrictions (<24 ships/day vs 36 normal); Political instability in Panama |
| **Primary Instruments** | `ZIM.US` (long — benefits from higher freight rates) |
| **Proxy Instruments** | `XTIUSD` (mild long — rerouting increases fuel costs) |
| **Entry Rules** | LONG `ZIM.US` when: Panama transits <24/day for >7 consecutive days AND ZIM RSI(14) <55 |
| **Exit Rules** | TP: 12% | SL: 6% | Time stop: 21 days (drought can last weeks) |
| **Position Sizing** | Max 3% equity |
| **Correlations** | ZIM ↔ #17 Container: 0.65 (same instrument, different trigger) |
| **Backtest Results** | *Placeholder — 2023 drought is key event* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #19: RED SEA / SUEZ CANAL

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Suez Canal handles 12-15% of global trade. Houthi attacks since 2023 have forced rerouting around Cape of Good Hope. Strait of Hormuz (21% of global oil) is additional risk. |
| **Supply Concentration** | Suez 12-15% of global trade, Hormuz 21% of global oil |
| **Trigger Scenarios** | Houthi attack escalation; Iran-US tension (Hormuz); Suez blockage (Ever Given repeat); Regional war escalation |
| **Primary Instruments** | `XTIUSD` (long), `USDNOK` (short — NOK benefits from oil), `USDCAD` (short — CAD benefits), `STNG.US` (long — tanker rates), `FRO.US` (long — Frontline tankers) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | **Oil Shock:** LONG `XTIUSD` when GDELT Red_Sea/Hormuz score >0.8 AND crude RSI(14) <60 | **Tankers:** LONG `STNG.US` or `FRO.US` when rerouting confirmed AND RSI(14) <55 | **Forex:** SHORT `USDNOK` + SHORT `USDCAD` on oil spike |
| **Exit Rules** | Oil: TP $5/bbl | SL $3/bbl | Tankers: TP 10% | SL 5% | FX: TP 200 pips | SL 120 pips |
| **Position Sizing** | Max 3% per instrument, max 12% combined (Shipping/Energy cap) |
| **Correlations** | XTIUSD ↔ USDNOK: -0.55; STNG ↔ FRO: 0.75 (pick one) |
| **Backtest Results** | *Placeholder — 2023-2024 Houthi attacks are key* |
| **Status** | 🟢 ACTIVE (Tier 1 — Top 10 opportunity, score 9.0/10) |

---

## Trade Card #20: VANILLA

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Madagascar produces 80% of global vanilla. Cyclone-prone, politically unstable. Highest-value spice by weight. |
| **Supply Concentration** | Madagascar 80%, Indonesia 10% |
| **Trigger Scenarios** | Cyclone hitting Madagascar; Political instability; Crop disease |
| **Primary Instruments** | None — vanilla is not traded on any accessible exchange/CFD |
| **Proxy Instruments** | None viable |
| **Entry Rules** | N/A — no tradeable instrument |
| **Exit Rules** | N/A |
| **Position Sizing** | N/A |
| **Correlations** | N/A |
| **Backtest Results** | N/A |
| **Status** | ⚫ NOT TRADEABLE |

---

## Trade Card #21: PALM OIL

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Indonesia (58%) and Malaysia (25%) produce 83% of global palm oil. Used in food, cosmetics, biofuels. Environmental and trade policy risks. |
| **Supply Concentration** | Indonesia 58%, Malaysia 25% |
| **Trigger Scenarios** | Indonesia export ban (happened 2022); Malaysia labor shortage; El Niño drought; EU deforestation regulation; Indian import tariff |
| **Primary Instruments** | `SOYBEAN` (long — substitute commodity on Pepperstone) |
| **Proxy Instruments** | `USDMYR` not available — use `USDJPY` long as indirect Asia risk proxy |
| **Entry Rules** | LONG `SOYBEAN` when: Indonesia palm oil export ban OR palm oil price spike >15% AND Soybean RSI(14) <55 |
| **Exit Rules** | TP: $0.80/bu above entry | SL: $0.40 below | Time stop: 14 days |
| **Position Sizing** | Max 3% equity, Agriculture cap 12% |
| **Correlations** | SOYBEAN ↔ WHEAT: 0.40; SOYBEAN ↔ COCOA: 0.15 |
| **Backtest Results** | *Placeholder — 2022 Indonesia ban is key* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #22: FISHMEAL

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Peru (25%) and Chile (15%) dominate fishmeal production. Key aquaculture/animal feed ingredient. El Niño collapses anchovy stocks. |
| **Supply Concentration** | Peru 25%, Chile 15% (anchovy-based) |
| **Trigger Scenarios** | El Niño declared (anchovy disappear from cold water); Peru fishing ban; Chilean fishing quota cut; Aquaculture demand surge |
| **Primary Instruments** | `MOWI.US` (Mowi — salmon farming, fishmeal consumer — long on price spike hedging) |
| **Proxy Instruments** | `USDPEN` not on Pepperstone — use `AUDUSD` (long, commodity currency proxy) |
| **Entry Rules** | LONG `MOWI.US` when: El Niño declared by NOAA AND MOWI RSI(14) <45 (market hasn't priced in yet) |
| **Exit Rules** | TP: 8% | SL: 4% | Time stop: 30 days |
| **Position Sizing** | Max 3% equity |
| **Correlations** | Low correlation with other inefficiencies (unique driver) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟢 ACTIVE (Tier 1 — Top 10 opportunity, score 9.3/10) |

---

## Trade Card #23: COCOA

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Ivory Coast (38%) and Ghana (17%) produce 55% of global cocoa. Climate change, swollen shoot virus, and aging trees threaten supply. |
| **Supply Concentration** | Ivory Coast 38%, Ghana 17%, Ecuador 8% |
| **Trigger Scenarios** | West Africa drought / excessive rain; Swollen Shoot Virus spread; Political instability in Ivory Coast; EU deforestation law compliance |
| **Primary Instruments** | `COCOA` (direct commodity CFD on Pepperstone — long) |
| **Proxy Instruments** | None needed — direct trade available |
| **Entry Rules** | LONG `COCOA` when: Ivory Coast weather disruption OR disease outbreak AND Cocoa >15% above 200-DMA AND volume >1.5x avg |
| **Exit Rules** | TP: 12% above entry | SL: 6% | Trailing stop: 3x ATR after 8% gain |
| **Position Sizing** | Max 4% equity |
| **Correlations** | Low correlation with most other inefficiencies |
| **Backtest Results** | *Placeholder — 2024 cocoa surge to $12K is key* |
| **Status** | 🟢 ACTIVE |

---

## Trade Card #24: NATURAL RUBBER

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Thailand (33%), Indonesia (26%), Vietnam (8%) dominate natural rubber. Used in tires (70% of demand), medical, industrial goods. |
| **Supply Concentration** | Thailand 33%, Indonesia 26%, Vietnam 8% |
| **Trigger Scenarios** | Thai flood (major rubber regions); Leaf fall disease; Indonesian export restrictions; Auto production surge |
| **Primary Instruments** | `USDJPY` (long — Japan is largest rubber importer, JPY weakens on input cost pressure) |
| **Proxy Instruments** | `USDTHB` not on Pepperstone |
| **Entry Rules** | LONG `USDJPY` when: Thai rubber disruption AND USDJPY RSI(14) <55 AND positive momentum |
| **Exit Rules** | TP: 150 pips | SL: 80 pips | Time stop: 10 days |
| **Position Sizing** | Max 2% equity |
| **Correlations** | USDJPY ↔ #29 TSMC (Taiwan tension): 0.30 (mild, different drivers) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #25: BAUXITE / ALUMINA

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Australia (28%) and Guinea (22%) dominate bauxite mining. China refines 55% into alumina/aluminium. |
| **Supply Concentration** | Australia 28%, Guinea 22%, China 55% (refining) |
| **Trigger Scenarios** | Guinea coup / export halt (happened 2021); Australia mine disruption; China smelter curtailment (power costs); Aluminium demand surge |
| **Primary Instruments** | `ALUMINIUM` (direct commodity CFD — long), `AUDUSD` (long), `AA.US` (Alcoa — long) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | LONG `ALUMINIUM` when: Guinea/Australia disruption AND Aluminium >8% above 200-DMA AND RSI(14) <60 | LONG `AA.US` for leveraged play |
| **Exit Rules** | Aluminium: TP $150 | SL $80 | AA: TP 10% | SL 5% |
| **Position Sizing** | Max 3% per instrument, max 7% combined |
| **Correlations** | ALUMINIUM ↔ COPPER: 0.55; ALUMINIUM ↔ AUDUSD: 0.50; AA ↔ ALUMINIUM: 0.78 (pick one) |
| **Backtest Results** | *Placeholder — 2021 Guinea coup is key event* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #26: WHEAT CHOKEPOINTS

| Field | Detail |
|-------|--------|
| **Category** | Food / Shipping |
| **Description** | Black Sea region exports ~30% of global wheat. Turkey controls Bosphorus Strait — chokepoint for Ukrainian/Russian exports. |
| **Supply Concentration** | Black Sea 30% of global wheat exports |
| **Trigger Scenarios** | Black Sea grain corridor collapse; Russia-Ukraine conflict escalation; Bosphorus closure; US/EU wheat crop failure; India export ban |
| **Primary Instruments** | `WHEAT` (direct CFD — long), `USDTRY` (long — Turkey under pressure), `ADM.US` (long), `BG.US` (Bunge — long) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | LONG `WHEAT` when: Black Sea disruption AND Wheat breaks above 52-wk high AND RSI(14) <65 | LONG `ADM.US` when: Global food crisis sentiment AND ADM RSI(14) <45 |
| **Exit Rules** | Wheat: TP $1.50/bu | SL $0.75 | ADM: TP 8% | SL 4% |
| **Position Sizing** | Max 4% WHEAT, 3% equities, Agriculture cap 12% |
| **Correlations** | WHEAT ↔ XTIUSD: 0.30; WHEAT ↔ SOYBEAN: 0.40; ADM ↔ BG: 0.68 (pick one) |
| **Backtest Results** | *Placeholder — 2022 Ukraine crisis is key* |
| **Status** | 🟢 ACTIVE |

---

## Trade Card #27: UNDERSEA CABLES

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | 3 companies (SubCom, NEC, Alcatel/Nokia) build 90%+ of undersea cables. 95% of intercontinental data travels through them. |
| **Supply Concentration** | 3 manufacturers = 90%+; Key cables: SEA-ME-WE, FLAG, TAT-14 |
| **Trigger Scenarios** | Cable cut event (anchoring, earthquake, sabotage); Russia/China submarine cable threat; Massive capacity demand (AI data centers) |
| **Primary Instruments** | `TE.US` (TE Connectivity — long), `NOK.US` (Nokia — long, owns ASN) |
| **Proxy Instruments** | Direct equity plays available |
| **Entry Rules** | LONG `TE.US` or `NOK.US` when: Major cable cut event AND RSI(14) <50 AND GDELT cable score >0.7 |
| **Exit Rules** | TP: 7% | SL: 4% | Time stop: 14 days |
| **Position Sizing** | Max 3% per name, Tech/Infra sector cap 15% |
| **Correlations** | TE ↔ NOK: 0.40 (can hold both with reduced size) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #28: ASML MONOPOLY

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | ASML is the sole manufacturer of EUV lithography systems. 100% monopoly on machines needed for <7nm chips. $350M+ per machine. |
| **Supply Concentration** | ASML 100% (EUV), ~85% (DUV) |
| **Trigger Scenarios** | Dutch export restriction expansion; ASML production disruption; China sanctions retaliation; ASML guidance cut; New fab build announcements |
| **Primary Instruments** | `ASML.US` (long on demand, short on restriction), `SOXX.US` (directional), `EURUSD` (long — Netherlands/EU tech strength) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | **Demand story:** LONG `ASML.US` when: New fab announcements AND ASML RSI(14) <45 | **Restriction story:** SHORT `SOXX.US` when: Dutch export ban expansion AND SOXX RSI(14) >60 |
| **Exit Rules** | ASML: TP 8% | SL 4% | SOXX short: TP 5% | SL 3% |
| **Position Sizing** | Max 4% equity, Semiconductor sector cap 15% |
| **Correlations** | ASML ↔ SOXX: 0.72 (don't double); ASML ↔ TSM: 0.65 |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟢 ACTIVE |

---

## Trade Card #29: TSMC CONCENTRATION

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | TSMC manufactures 90% of world's advanced chips (<7nm). Single island (Taiwan) concentration. China military threat. |
| **Supply Concentration** | TSMC 90% (advanced node), Taiwan overall ~65% (all chips) |
| **Trigger Scenarios** | China-Taiwan military escalation; TSMC fab fire/earthquake; US CHIPS Act competitor announcements; TSMC Arizona delays |
| **Primary Instruments** | `TSM.US` (long structural / short on Taiwan crisis), `SOXX.US` (directional) |
| **Proxy Instruments** | `USDJPY` (long on Taiwan crisis — risk-off), `CHFJPY` (long — safe haven) |
| **Entry Rules** | **Structural long:** LONG `TSM.US` when: Global chip demand rising AND TSM RSI(14) <40 AND no military escalation | **Crisis short:** SHORT `TSM.US` when: GDELT Taiwan military score >0.8 AND TSM gap down >3% |
| **Exit Rules** | Structural: TP 10% | SL 5% | Crisis: TP 8% | SL 4% (fast exit) |
| **Position Sizing** | Max 4% equity, Semiconductor cap 15% |
| **Correlations** | TSM ↔ SOXX: 0.78 (pick one); TSM ↔ ASML: 0.65 |
| **Backtest Results** | *Placeholder — 2022 Pelosi visit is key event* |
| **Status** | 🟢 ACTIVE (Tier 1 — Top 10 opportunity, score 8.5/10) |

---

## Trade Card #30: NEON GAS

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | Ukraine was producing 50%+ of semiconductor-grade neon (byproduct of steel mills). War disrupted supply, alternatives emerging. |
| **Supply Concentration** | Previously Ukraine 50%+ (now diversifying); China emerging as alternative |
| **Trigger Scenarios** | Ukraine conflict escalation near Odesa/Mariupol; New neon plant delays; Semiconductor neon shortage reports |
| **Primary Instruments** | `SOXX.US` (short on shortage) |
| **Proxy Instruments** | Indirect through chip equities |
| **Entry Rules** | SHORT `SOXX.US` when: Ukraine conflict near neon plants AND SOXX RSI(14) >60 AND FinBERT neon/semiconductor sentiment <-0.4 |
| **Exit Rules** | TP: 5% | SL: 3% | Time stop: 7 days |
| **Position Sizing** | Max 3% equity, Semiconductor cap 15% |
| **Correlations** | SOXX ↔ TSM: 0.78; SOXX ↔ ASML: 0.72 |
| **Backtest Results** | *Placeholder — 2022 is key (Ukraine invasion)* |
| **Status** | 🟡 MONITORING (diversification reducing concentration) |

---

## Trade Card #31: ULTRA-PURE WATER

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | US and Japan dominate ultra-pure water (UPW) systems for semiconductor fabs. 18.2 MΩ·cm resistivity required. Key players: Veolia, SUEZ, Kurita (Japan). |
| **Supply Concentration** | US/Japan dominate UPW systems; Key: Kurita Water (Japan) |
| **Trigger Scenarios** | Japan earthquake near semiconductor hubs; UPW contamination event; New fab water demand exceeds local supply |
| **Primary Instruments** | `USDJPY` (long on Japan disruption), `DHR.US` (Danaher — long, water tech) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | LONG `DHR.US` when: Semiconductor water shortage reports AND DHR RSI(14) <45 AND tech sector momentum positive |
| **Exit Rules** | TP: 7% | SL: 4% | Time stop: 21 days |
| **Position Sizing** | Max 3% equity |
| **Correlations** | DHR ↔ SOXX: 0.30 (low — different driver); DHR ↔ USDJPY: 0.15 |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #32: SWIFT FINANCIAL SYSTEM

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | SWIFT is the global financial messaging monopoly (11,000+ institutions). Disconnection from SWIFT is a "financial nuclear option." |
| **Supply Concentration** | SWIFT: near-100% monopoly on interbank messaging |
| **Trigger Scenarios** | New country SWIFT disconnection; SWIFT system outage; China CIPS expansion; Digital currency bypass threat |
| **Primary Instruments** | `EURUSD` (event-driven — EUR weakens if European institutions affected) |
| **Proxy Instruments** | Bank equities for affected countries |
| **Entry Rules** | **Event only:** Trade `EURUSD` directionally based on SWIFT disconnection scenario. Requires manual assessment — no automated trigger. |
| **Exit Rules** | Case-by-case. Typically TP: 150 pips | SL: 80 pips |
| **Position Sizing** | Max 2% equity (rare event) |
| **Correlations** | Unique — near zero with other inefficiencies |
| **Backtest Results** | *Placeholder — 2022 Russia SWIFT ban is key* |
| **Status** | 🟡 MONITORING (rare but high-impact) |

---

## Trade Card #33: GPS/GNSS VULNERABILITY

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | GPS (US) + Galileo (EU) + GLONASS (Russia) + BeiDou (China). Mass spoofing/jamming events increasing. Critical for navigation, timing, finance. |
| **Supply Concentration** | GPS 31 satellites (US controlled); Military-grade dependency |
| **Trigger Scenarios** | Mass GPS spoofing event (Middle East pattern); Anti-satellite weapon test; Solar storm GPS disruption; Military GPS denial |
| **Primary Instruments** | `LMT.US` (Lockheed — long, GPS satellite manufacturer), `RTX.US` (Raytheon — long, defense) |
| **Proxy Instruments** | Defense ETF as broadener |
| **Entry Rules** | LONG `LMT.US` or `RTX.US` when: GPS spoofing event AND defense spending increase AND RSI(14) <50 |
| **Exit Rules** | TP: 6% | SL: 3% | Time stop: 14 days |
| **Position Sizing** | Max 3% per name |
| **Correlations** | LMT ↔ RTX: 0.65 (defense sector — pick one or reduce size) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #34: POWER TRANSFORMERS

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | 3 companies (Siemens Energy, Hitachi Energy, GE Vernova) make ~75% of large power transformers. Lead times now 3-5 years. AI/EV demand explosion. |
| **Supply Concentration** | Top 3 = 75%; US backlog = 3-5 years |
| **Trigger Scenarios** | Grid failure / transformer shortage emergency; AI data center power demand surge; Extreme weather grid damage; New transformer factory announcement |
| **Primary Instruments** | `ETN.US` (Eaton — long), `CLF.US` (Cleveland-Cliffs — long, electrical steel) |
| **Proxy Instruments** | `EURUSD` (long — Siemens Energy is European) |
| **Entry Rules** | LONG `ETN.US` when: Grid emergency OR transformer backlog reports AND ETN RSI(14) <50 AND MACD bullish cross |
| **Exit Rules** | TP: 8% | SL: 4% | Time stop: 30 days (structural trade) |
| **Position Sizing** | Max 4% equity, Tech/Infra cap 15% |
| **Correlations** | ETN ↔ CLF: 0.35 (can hold both); ETN ↔ ABB: 0.50 |
| **Backtest Results** | *Placeholder — ongoing structural shortage since 2023* |
| **Status** | 🟢 ACTIVE (Tier 1 — Top 10 opportunity, score 9.5/10) |

---

## Trade Card #35: HVDC CONVERTERS

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | 4 companies (Hitachi Energy, Siemens Energy, GE Vernova, NR Electric) control 85% of HVDC converter technology. Critical for offshore wind, long-distance power transmission. |
| **Supply Concentration** | Top 4 = 85% of HVDC converter market |
| **Trigger Scenarios** | Offshore wind buildout acceleration; HVDC project delay/cancellation; Subsea cable failure; Energy transition policy boost |
| **Primary Instruments** | `ABB.US` (ABB — long, owns Hitachi Energy stake), `EURSEK` (long — Swedish ABB/infrastructure) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | LONG `ABB.US` when: New HVDC project announcement OR energy transition policy AND ABB RSI(14) <50 AND FinBERT energy sentiment >0.2 |
| **Exit Rules** | TP: 7% | SL: 4% | Time stop: 30 days |
| **Position Sizing** | Max 3% equity, Tech/Infra cap 15% |
| **Correlations** | ABB ↔ ETN: 0.50 (moderate — reduce combined size) |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟢 ACTIVE (Tier 1 — Top 10 opportunity, score 8.0/10) |

---

## Trade Card #36: SKILLED LABOR SHORTAGE

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | US/EU/Japan face critical skilled labor shortages in manufacturing, construction, energy. Structural demographic constraint. |
| **Supply Concentration** | Systemic — all developed economies affected |
| **Trigger Scenarios** | Manufacturing PMI employment <48; Immigration policy tightening; STEM graduation rates declining |
| **Primary Instruments** | None — macro indicator, not directly tradeable as single instrument |
| **Proxy Instruments** | Could use staffing company equities but low correlation |
| **Entry Rules** | **Macro indicator only** — feeds into regime detection, not direct trades |
| **Exit Rules** | N/A |
| **Position Sizing** | N/A |
| **Correlations** | Background factor for all manufacturing trades |
| **Backtest Results** | N/A |
| **Status** | ⚪ INDICATOR ONLY (no direct trade) |

---

## Trade Card #37: CLOUD CONCENTRATION

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | AWS (31%), Azure (25%), GCP (11%) = 67% of global cloud. Single outage affects millions of businesses. |
| **Supply Concentration** | Top 3 = 67% of global cloud market |
| **Trigger Scenarios** | Major AWS/Azure/GCP outage >4 hours; Cloud pricing war; Antitrust action; Sovereign cloud mandates |
| **Primary Instruments** | `AMZN.US` (Amazon — long structural), `MSFT.US` (Microsoft — long), `GOOGL.US` (Google — long) |
| **Proxy Instruments** | `QQQ.US` (tech ETF) for broad exposure |
| **Entry Rules** | **Outage play:** SHORT affected stock on major outage IF RSI(14) >55 (sell the overreaction) OR LONG competitors | **Structural:** LONG `AMZN.US` on cloud growth reports |
| **Exit Rules** | TP: 5% | SL: 3% | Time stop: 7 days (outage trades are short-lived) |
| **Position Sizing** | Max 3% per name, max 10% combined (mega-cap risk) |
| **Correlations** | AMZN ↔ MSFT: 0.72; AMZN ↔ GOOGL: 0.68; All ↔ QQQ: 0.85+ |
| **Backtest Results** | *Placeholder* |
| **Status** | 🟡 MONITORING |

---

## Trade Card #38: COPPER

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | Chile (24%), DRC (12%), Peru (10%) produce most copper. Critical for electrification, EVs, renewables, construction. AI data center power = massive new demand. |
| **Supply Concentration** | Chile 24%, DRC 12%, Peru 10%; Top 3 = 46% |
| **Trigger Scenarios** | Chile mine strike / water shortage; DRC civil unrest; Peru political instability; LME inventory depletion; AI power demand surge; EV adoption acceleration |
| **Primary Instruments** | `COPPER` (direct CFD — long), `FCX.US` (Freeport — long), `SCCO.US` (Southern Copper — long), `COPX.US` (copper miners ETF — long), `AUDUSD` (long) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | **Supply disruption:** LONG `COPPER` when: Mine disruption event AND LME inventory <150,000t AND Copper RSI(14) <50 | **Structural:** LONG `FCX.US` when: FCX RSI(14) <30 AND copper >200-DMA (deep value) | **Forex:** LONG `AUDUSD` on broad commodity cycle upturn |
| **Exit Rules** | Copper: TP $0.30/lb | SL $0.15 | FCX: TP 12% | SL 6% | AUDUSD: TP 200 pips | SL 100 pips |
| **Position Sizing** | Max 5% COPPER, 4% FCX, 3% COPX — but Copper Complex cap 15% total |
| **Correlations** | COPPER ↔ FCX: 0.85 (pick one!); COPPER ↔ AUDUSD: 0.72 (pick one!); FCX ↔ SCCO: 0.80 (pick one!) |
| **Backtest Results** | *Placeholder — 2020-2024 copper bull market is rich dataset* |
| **Status** | 🟢 ACTIVE (Tier 1 — #1 opportunity, score 9.7/10) |

---

## Trade Card #39: SAND (Construction Aggregate)

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | Construction sand is locally sourced but increasingly scarce globally. Sand mining bans in India, Singapore import dependency. |
| **Supply Concentration** | Highly localized; Key producers: US, India, China |
| **Trigger Scenarios** | Regional sand mining ban; Major construction boom; Singapore land reclamation surge; Environmental regulation |
| **Primary Instruments** | `VMC.US` (Vulcan Materials — long), `MLM.US` (Martin Marietta — long) |
| **Proxy Instruments** | Construction/infrastructure ETFs |
| **Entry Rules** | LONG `VMC.US` or `MLM.US` when: US infrastructure bill + construction demand AND RSI(14) <45 |
| **Exit Rules** | TP: 7% | SL: 4% | Time stop: 30 days |
| **Position Sizing** | Max 3% per name |
| **Correlations** | VMC ↔ MLM: 0.82 (pick one); Low correlation with other inefficiencies |
| **Backtest Results** | *Placeholder* |
| **Status** | ⚪ LOW PRIORITY (slow-moving, hard to time) |

---

## Trade Card #40: POLYSILICON

| Field | Detail |
|-------|--------|
| **Category** | Tech / Infra |
| **Description** | China produces 80%+ of global polysilicon for solar panels. Xinjiang forced labor concerns + export dependency. |
| **Supply Concentration** | China 80%+ (mostly Xinjiang region) |
| **Trigger Scenarios** | China polysilicon production accident; US Uyghur Forced Labor Prevention Act enforcement; EU carbon border tariff; Solar demand surge outpacing supply |
| **Primary Instruments** | `USDCNH` (short on China polysilicon disruption), `TAN.US` (Invesco Solar ETF), `ENPH.US` (Enphase — long on solar demand) |
| **Proxy Instruments** | All available on Pepperstone |
| **Entry Rules** | LONG `TAN.US` when: China polysilicon disruption + solar demand intact AND TAN RSI(14) <45 | LONG `ENPH.US` when: Polysilicon shortage → US/EU solar beneficiaries AND ENPH RSI(14) <35 |
| **Exit Rules** | TAN: TP 8% | SL 4% | ENPH: TP 12% | SL 6% |
| **Position Sizing** | Max 3% per position, China Minerals cap 15% |
| **Correlations** | TAN ↔ ENPH: 0.65; TAN ↔ USDCNH: -0.20 |
| **Backtest Results** | *Placeholder — 2021-2022 polysilicon squeeze is key* |
| **Status** | 🟡 MONITORING |

---

# APPENDIX B: FOREX STRATEGY PLAYBOOK

## B.1 Strategy Overview

| # | Strategy Name | Pairs | Trigger | Avg Duration | Expected Freq |
|---|-------------|-------|---------|-------------|---------------|
| FX-1 | Commodity Currency Basket | AUD/USD, USD/CAD, USD/NOK | Broad commodity cycle | 5-15 days | 2-4 /month |
| FX-2 | China Export Ban Event | USD/CNH, AUD/USD, (USD/KRW proxy) | China critical mineral restriction | 2-7 days | 1-3 /quarter |
| FX-3 | Chokepoint/Oil Shock | USD/NOK, USD/CAD, USD/INR, USD/TRY, AUD/JPY | Strait closure / oil spike | 3-10 days | 1-2 /quarter |
| FX-4 | Taiwan Tension Hedge | (USD/TWD proxy), AUD/JPY, CHF/JPY, (USD/KRW proxy) | Cross-strait military tension | 1-5 days | 0-2 /year |
| FX-5 | Mining Country Shock | USD/ZAR, AUD/USD, USD/CLP proxy | Mine closure / political instability | 3-14 days | 1-3 /quarter |
| FX-6 | Agricultural Crisis | USD/TRY, AUD/USD | Wheat/food supply disruption | 5-21 days | 1-2 /quarter |

---

## B.2 FX-1: Commodity Currency Basket

### Description
Trade AUD, CAD, NOK as commodity proxy currencies during broad supply chain disruption events that push commodity prices higher.

### Instruments

| Pair | Pepperstone Symbol | Direction | Rationale |
|------|-------------------|-----------|-----------|
| AUD/USD | `AUDUSD` | LONG | Australia = iron ore, copper, gold, bauxite, coal |
| USD/CAD | `USDCAD` | SHORT | Canada = oil, uranium, potash, forestry |
| USD/NOK | `USDNOK` | SHORT | Norway = oil, gas, fish, metals |

### Entry Rules

```
ALL three conditions must be met:
1. GDELT global supply chain disruption index > 0.6
   (OR Bloomberg Commodity Index > 200-DMA by >5%)
2. DXY (US Dollar Index) < 200-DMA (dollar weakening)
3. At least 2 of 3 pairs showing RSI(14) in favorable zone:
   - AUDUSD RSI(14) < 45 (oversold → long)
   - USDCAD RSI(14) > 55 (overbought → short)
   - USDNOK RSI(14) > 55 (overbought → short)
```

### Position Sizing

```
Total basket allocation: Max 8% of equity
  AUDUSD: 3% risk
  USDCAD: 3% risk
  USDNOK: 2% risk (wider spreads → smaller size)

Stop: 1.5x ATR(14) from entry
TP: 3.0x ATR(14) from entry (2:1 R:R)
```

### Exit Rules

- **Profit target:** TP hit on individual pairs → close that pair
- **Stop loss:** SL hit on individual pairs → close that pair
- **Basket close:** If 2 of 3 pairs hit SL → close remaining pair immediately
- **Time stop:** 15 trading days maximum
- **Regime change:** DXY crosses above 200-DMA → close all

---

## B.3 FX-2: China Export Ban Event

### Description
Fast-acting event trade when China announces or signals export restrictions on critical minerals (gallium, germanium, antimony, rare earths, graphite, magnesium, polysilicon).

### Instruments

| Pair | Pepperstone Symbol | Direction | Rationale |
|------|-------------------|-----------|-----------|
| USD/CNH | `USDCNH` | SHORT | CNH strengthens on export control (reduced supply → higher value of Chinese goods) |
| AUD/USD | `AUDUSD` | LONG | Australia benefits as alternative supplier |

### Entry Rules

```
FAST ENTRY (within 2 hours of event):
1. GDELT China + (Gallium|Germanium|Antimony|RareEarth|Graphite|Magnesium) score > 0.8
2. OR confirmed news headline from Reuters/Bloomberg
3. USDCNH must be > 7.10 (meaningful level)
4. No existing China Minerals positions

CONFIRMED ENTRY (within 24 hours):
1. FinBERT sentiment on China export news < -0.5
2. At least one technical confirmation:
   - USDCNH MACD bearish crossover
   - AUDUSD MACD bullish crossover
```

### Position Sizing

```
Event trade allocation: Max 5% of equity combined
  USDCNH: 3% risk
  AUDUSD: 2% risk

Stop: 120 pips (USDCNH), 60 pips (AUDUSD)
TP: 250 pips (USDCNH), 120 pips (AUDUSD)
```

### Exit Rules

- **Profit target:** Scale out 50% at 150 pips (CNH) / 80 pips (AUD), remainder at full TP
- **Stop loss:** Hard stop, no averaging down
- **Reversal:** If China announces exemptions/rollback within 48h → close immediately
- **Time stop:** 7 trading days (event fading)

---

## B.4 FX-3: Chokepoint / Oil Shock

### Description
Trade oil-correlated currencies when a major maritime chokepoint is disrupted (Red Sea, Hormuz, Malacca, Panama).

### Instruments

| Pair | Pepperstone Symbol | Direction | Rationale |
|------|-------------------|-----------|-----------|
| USD/NOK | `USDNOK` | SHORT | Norway is major oil exporter → NOK strengthens |
| USD/CAD | `USDCAD` | SHORT | Canada is major oil exporter → CAD strengthens |
| USD/INR | `USDINR` ✓ | LONG | India is major oil importer → INR weakens |
| USD/TRY | `USDTRY` ✓ | LONG | Turkey is energy importer + Bosphorus proximity |
| AUD/JPY | `AUDJPY` ✓ | SHORT on severe crisis | Both affected, but JPY safe-haven bid dominates |

### Entry Rules

```
1. GDELT (Hormuz|Suez|RedSea|Malacca|Panama) score > 0.8
2. Crude Oil (XTIUSD) spike > 3% intraday
3. Pair-specific:
   - USDNOK: RSI(14) > 50 (room to fall)
   - USDCAD: RSI(14) > 50
   - USDINR: RSI(14) < 65 (room to rise)
   - USDTRY: RSI(14) < 70
```

### Position Sizing

```
Total chokepoint allocation: Max 10% of equity
  USDNOK: 3% risk
  USDCAD: 3% risk
  USDINR: 2% risk (wider spread)
  USDTRY: 2% risk (volatile, carry cost)

Stop: 2.0x ATR(14) from entry
TP: 3.0x ATR(14) from entry
```

### Exit Rules

- **Oil reversal:** If crude drops >3% from event peak → reduce 50%
- **Resolution signal:** If strait reopens / attacks stop → close within 4h
- **Time stop:** 10 trading days
- **Carry consideration:** USDTRY short has high negative swap — limit hold time

---

## B.5 FX-4: Taiwan Tension Hedge

### Description
Risk-off trade during Taiwan Strait military tension. JPY and CHF appreciate as safe havens; Asia-Pacific currencies weaken.

### Instruments

| Pair | Pepperstone Symbol | Direction | Rationale |
|------|-------------------|-----------|-----------|
| AUD/JPY | `AUDJPY` | SHORT | AUD weakens (risk-off), JPY strengthens (safe haven) |
| CHF/JPY | `CHFJPY` | LONG | Both safe havens, but CHF outperforms on European distance from conflict |
| USD/JPY | `USDJPY` | SHORT | JPY safe-haven bid dominates |

### Entry Rules

```
EXTREME CAUTION — only trade on HIGH-CONVICTION signals:
1. GDELT Taiwan + (Military|Invasion|Blockade|Missile) score > 0.85
2. VIX > 25 (fear confirming)
3. USDJPY dropping (JPY strengthening)
4. Gold (XAUUSD) rising > 1% intraday

MINIMUM 2 of 4 conditions required
```

### Position Sizing

```
Defensive allocation: Max 6% of equity combined
  AUDJPY: 3% risk (primary trade)
  CHFJPY: 2% risk
  USDJPY: 1% risk (smallest — already correlated)

Stop: 150 pips (AUDJPY), 100 pips (others)
TP: 300+ pips (AUDJPY), 200 pips (others) — OR hold until tension de-escalates
```

### Exit Rules

- **De-escalation:** Close 50% immediately on confirmed de-escalation signal
- **False alarm:** If VIX drops below 20 within 48h → close all
- **Time stop:** 5 trading days (unless active military operations continue)
- **Profit lock:** Trailing stop at 1.5x ATR after 150 pips profit

---

## B.6 FX-5: Mining Country Shock

### Description
Trade FX pairs when major mining countries experience domestic disruption (strikes, power crisis, political instability).

### Instruments & Scenarios

| Scenario | Pair | Direction | Trigger |
|----------|------|-----------|---------|
| S.Africa power/strike | `USDZAR` | LONG | Eskom load-shedding, mining strikes |
| Australia mine disruption | `AUDUSD` | SHORT (initially), then LONG (price spike benefits) | Cyclone, flooding, environmental halt |
| Chile social unrest | Proxy via `COPPER` | LONG | Political instability, water restrictions |
| Peru political crisis | Proxy via `AUDUSD` LONG | LONG | President impeachment, mining protests |

### Entry Rules

```
1. GDELT country-specific disruption score > 0.7
2. Relevant commodity price responding (COPPER, XAUUSD, etc.)
3. Pair-specific technical confirmation
4. FinBERT sentiment on country-specific news < -0.3
```

### Position Sizing

```
Per-event: Max 3% of equity per pair
Stop: 2.5x ATR(14) — wider for exotic pairs (ZAR volatility)
TP: 4.0x ATR(14)
```

---

## B.7 FX-6: Agricultural Crisis

### Description
Trade currencies affected by agricultural supply disruptions (wheat, fertilizer, food security).

### Instruments

| Pair | Pepperstone Symbol | Direction | Trigger |
|------|-------------------|-----------|---------|
| USD/TRY | `USDTRY` | LONG | Turkey wheat import dependency + inflation |
| AUD/USD | `AUDUSD` | LONG | Australia wheat exporter benefits |

### Entry Rules

```
1. Black Sea grain disruption OR global food crisis escalation
2. WHEAT CFD > 52-week high
3. USDTRY RSI(14) < 75 (room to move despite trend)
4. AUDUSD RSI(14) < 50
```

### Position Sizing

```
USDTRY: 2% risk (high volatility + negative swap on short)
AUDUSD: 3% risk
Stop: 2.0x ATR(14) | TP: 3.0x ATR(14)
```

---

# APPENDIX C: EVENT RESPONSE PLAYBOOK

## C.1 China Export Ban Response

### Scenario
China announces export restrictions on one or more critical minerals (gallium, germanium, antimony, rare earths, graphite, magnesium, polysilicon).

### Immediate Actions (0-2 Hours)

| Step | Action | Priority |
|------|--------|----------|
| 1 | Verify news from 2+ sources (Reuters, Bloomberg, Xinhua) | P0 |
| 2 | Identify which minerals affected | P0 |
| 3 | Check current portfolio exposure to China Minerals group | P0 |
| 4 | If under sector cap: Execute FX-2 (China Export Ban) strategy | P0 |
| 5 | Queue equity/ETF signals for affected minerals | P1 |

### Trade Matrix

| Mineral Banned | Primary Trade | Secondary Trade | Tertiary Trade |
|---------------|--------------|-----------------|----------------|
| Gallium/Germanium | SHORT `USDCNH` | LONG `REMX.US` | SHORT `SOXX.US` |
| Rare Earths | SHORT `USDCNH` | LONG `MP.US` | LONG `REMX.US` |
| Antimony | SHORT `USDCNH` | LONG `REMX.US` | — |
| Graphite | SHORT `USDCNH` | LONG `AUDUSD` | — |
| Magnesium | SHORT `USDCNH` | — | — |
| Polysilicon | SHORT `USDCNH` | LONG `TAN.US` | LONG `ENPH.US` |
| ALL (nuclear option) | SHORT `USDCNH` (max) | LONG `AUDUSD` | LONG all alt. suppliers |

### Position Limits During Event

```
Max China Minerals group: 15% equity (hard cap)
Max single FX position: 3%
Max single equity position: 4%
Reduce other positions if needed to stay within 50% total margin
```

### De-escalation Criteria

- China announces exemptions → reduce 50% immediately
- 72h with no additional escalation → start scaling out
- Full reversal announced → close all event positions within 4h

---

## C.2 Strait Closure Response

### Scenario
Major maritime chokepoint closure or severe disruption (Hormuz, Suez/Red Sea, Malacca, Taiwan Strait, Bosphorus).

### Severity Tiers

| Tier | Description | Example | Response Level |
|------|------------|---------|----------------|
| T1 | Partial disruption, alternative routes available | Houthi attacks (ships reroute) | Moderate — gradual positioning |
| T2 | Full closure, short duration expected (<2 weeks) | Ever Given grounding | Aggressive — immediate positions |
| T3 | Full closure, extended/indefinite | Iran closes Hormuz | Maximum — activate all chokepoint trades |

### Immediate Actions by Strait

#### Strait of Hormuz (21% global oil)

| Priority | Action |
|----------|--------|
| P0 | LONG `XTIUSD` (crude oil) — max 5% equity |
| P0 | SHORT `USDNOK` + SHORT `USDCAD` — 3% each |
| P1 | LONG `STNG.US` or `FRO.US` — 3% |
| P1 | LONG `XAUUSD` (gold safe haven) — 3% |
| P2 | LONG `USDINR`, LONG `USDTRY` — 2% each |

#### Suez Canal / Red Sea (12-15% global trade)

| Priority | Action |
|----------|--------|
| P0 | LONG `XTIUSD` — 3% equity |
| P0 | LONG `ZIM.US` (shipping rates surge) — 3% |
| P1 | SHORT `USDNOK` — 3% |
| P1 | LONG tanker stocks (STNG/FRO) — 3% |
| P2 | LONG `WHEAT` if grain transit affected — 3% |

#### Taiwan Strait (military)

| Priority | Action |
|----------|--------|
| P0 | Activate FX-4 Taiwan Tension Hedge — 6% total |
| P0 | SHORT `TSM.US` — 4% |
| P1 | SHORT `SOXX.US` — 3% |
| P1 | LONG `XAUUSD` — 4% |
| P1 | LONG `LMT.US`, `RTX.US` (defense) — 3% each |
| P2 | Evaluate circuit breaker — may exceed drawdown limits |

### Monitoring During Event

```
Every 30 minutes:
- Check MarineTraffic for vessel rerouting data
- Monitor GDELT for escalation/de-escalation signals
- Update crude oil / shipping rate proxies
- Check portfolio correlation (chokepoint trades cluster)
- Review margin utilization (volatile markets = wider swings)

Every 4 hours:
- FinBERT sentiment on chokepoint news
- Update P&L and drawdown
- Reassess position sizes
```

---

## C.3 Undersea Cable Cut Response

### Scenario
Major undersea telecommunications cable severed (physical damage, sabotage, or earthquake).

### Severity Assessment

| Severity | Criteria | Market Impact |
|----------|---------|--------------|
| Low | Single cable, redundant capacity exists | Minimal — no trade |
| Medium | Multiple cables on same route, some latency impact | Moderate — equity trades |
| High | Critical route severed (Asia-Europe or Trans-Atlantic), major internet disruption | Significant — multi-instrument |

### Trade Actions

| Severity | Primary | Secondary | FX |
|----------|---------|-----------|-----|
| Low | Monitor only | — | — |
| Medium | LONG `TE.US` or `NOK.US` (3%) | — | — |
| High | LONG `TE.US` + `NOK.US` (3% each) | SHORT affected region tech stocks | LONG safe-haven FX (CHF, JPY) |

### Timeline

```
0-1h:  Assess severity from news, submarine cable map
1-4h:  Execute primary trades if medium+ severity
4-24h: Execute secondary trades if impact confirmed
1-7d:  Hold positions while repair ship en route
7-30d: Monitor repair progress, scale out as capacity restored
```

---

## C.4 Mine Disruption Response

### Scenario
Major mining operation disrupted (accident, strike, weather, political).

### Assessment Matrix

| Factor | Low Impact | Medium Impact | High Impact |
|--------|-----------|--------------|-------------|
| Mine size | <5% of global supply | 5-15% | >15% |
| Duration | <1 week | 1-4 weeks | >1 month |
| Alternatives | Many alternative sources | Some alternatives | Few/no alternatives |
| Stockpiles | >6 months industry | 3-6 months | <3 months |

### Response by Commodity

| Commodity | Mine Location | Primary Trade | Size |
|-----------|-------------|---------------|------|
| Copper | Chile | LONG `COPPER` + LONG `FCX.US` | 4% + 3% |
| Copper | DRC | LONG `COPPER` | 4% |
| Cobalt | DRC | LONG `COPPER` (proxy) | 3% |
| Bauxite | Guinea | LONG `ALUMINIUM` + LONG `AA.US` | 3% + 3% |
| Manganese | S.Africa | LONG `USDZAR` | 3% |
| Uranium | Kazakhstan | LONG `CCJ.US` + LONG `URA.US` | 3% + 3% |
| Rare Earths | China | SHORT `USDCNH` + LONG `MP.US` | 3% + 3% |
| Platinum | S.Africa | LONG `USDZAR` | 3% |

---

## C.5 Weather Event Response

### Scenario
Severe weather affecting agricultural or mining production.

### Event Types & Trades

| Weather Event | Affected Commodity | Primary Trade | Timeframe |
|-------------|-------------------|---------------|-----------|
| El Niño declared | Fishmeal (Peru), Cocoa (W.Africa) | LONG `COCOA`, LONG `MOWI.US` | 2-6 months |
| La Niña declared | Wheat (Australia), Copper (Chile dry) | LONG `WHEAT`, LONG `COPPER` | 2-6 months |
| W.Africa drought | Cocoa, Coffee | LONG `COCOA` | 1-3 months |
| Thailand flood | Natural rubber, rice | LONG `USDJPY` | 1-4 weeks |
| Australian cyclone | Iron ore, bauxite | SHORT `AUDUSD` (short-term) | 1-2 weeks |
| US heatwave | Corn, soybeans, power grid | LONG `SOYBEAN`, LONG `ETN.US` | 2-6 weeks |

### Decision Tree

```
Weather event detected
├── Severity < "moderate" → Monitor only
├── Severity = "moderate" AND crop/commodity affected
│   ├── Check inventory levels
│   │   ├── Inventory low (<3 months) → ENTER immediately (2% risk)
│   │   └── Inventory adequate → Wait for price confirmation
│   └── Check duration forecast
│       ├── < 2 weeks → Likely no trade
│       └── > 2 weeks → ENTER on confirmation
└── Severity = "severe/extreme"
    └── ENTER immediately (3% risk) + set wider stops (3x ATR)
```

---

## C.6 Political Instability Response

### Scenario
Coup, revolution, or severe political crisis in a key commodity-producing nation.

### Country Response Matrix

| Country | Key Commodities | Primary Trade | FX Trade | Risk Level |
|---------|----------------|---------------|----------|------------|
| DRC | Cobalt, Copper | LONG `COPPER` | — | High (conflict zone) |
| Guinea | Bauxite | LONG `ALUMINIUM` | — | High |
| Peru | Copper, Fishmeal | LONG `COPPER` | — | Medium |
| Chile | Copper | LONG `COPPER`, `FCX.US` | SHORT `AUDUSD` briefly | Medium |
| S.Africa | Manganese, PGMs | — | LONG `USDZAR` | Medium |
| Myanmar | Antimony, Rare Earths | SHORT `USDCNH` | — | High |
| Gabon | Manganese | — | — | Low (small impact) |
| Kazakhstan | Uranium | LONG `CCJ.US` | — | Medium |
| Panama | Canal transit | LONG `ZIM.US` | — | Low |

### Timeline Protocol

```
Hour 0-4:   ASSESS — Verify event, estimate severity
Hour 4-24:  POSITION — Enter primary trades if severity > medium
Day 1-7:    MONITOR — Track developments, adjust positions
Day 7-30:   REVIEW — Scale out if situation stabilizing
Day 30+:    REBASE — Adjust supply concentration estimates
```

---

## C.7 Regulatory Change Response

### Scenario
Major regulatory change affecting supply chain (export controls, environmental regulations, trade agreements, sanctions).

### Response Matrix

| Regulation Type | Speed | Primary Action | Example |
|----------------|-------|----------------|---------|
| Export ban (immediate) | FAST | Execute event trade within 2h | China Ga/Ge ban |
| Sanction expansion | FAST | Adjust exposure within 4h | Russia SWIFT |
| Environmental regulation | SLOW | Gradual positioning over 1-4 weeks | EU deforestation law |
| Trade agreement change | SLOW | Research and position over 2-4 weeks | USMCA modification |
| Subsidy/incentive | SLOW | Gradual positioning over 1-4 weeks | US CHIPS Act, IRA |

### Key Regulatory Watchlist

| Regulation | Status | Affected Inefficiencies | Monitoring Frequency |
|-----------|--------|------------------------|---------------------|
| China export controls (minerals) | Active, expanding | #2, #3, #4, #6, #8, #11, #12, #40 | Daily |
| EU CBAM (Carbon Border) | Implementing | #25, #38, #40 | Weekly |
| US CHIPS Act | Implementing | #28, #29, #30, #31 | Weekly |
| US IRA (Inflation Reduction Act) | Active | #10, #38, #40 | Weekly |
| EU Deforestation Regulation | Implementing | #21, #23, #24 | Monthly |
| Kigali Amendment (HFCs) | Active | #16 | Quarterly |
| Basel III endgame (banking) | Proposed | #32 | Monthly |
| IMO 2030 shipping rules | Proposed | #17, #18, #19 | Quarterly |

---

# APPENDIX D: RISK MANAGEMENT RULES

## D.1 Hard Limits

### Position Limits

| Rule | Limit | Enforcement |
|------|-------|-------------|
| Maximum open positions | 10 | Reject new signals when at limit |
| Maximum single position (equity %) | 5% | Reduce to 5% immediately if breached |
| Maximum sector exposure | 15% | No new positions in sector |
| Maximum total margin used | 50% | No new positions |
| Maximum correlated pair (ρ > 0.7) | 1 position only | Close weaker of the two |
| Minimum position size | 0.01 lots | Below this = no trade |

### Loss Limits

| Rule | Limit | Action |
|------|-------|--------|
| Maximum daily loss | 3% of equity | Stop all trading for remainder of day |
| Maximum weekly loss | 5% of equity | Reduce all position sizes by 50% |
| Maximum drawdown (circuit breaker) | 10% of equity | **CLOSE ALL POSITIONS** |
| Maximum consecutive losses | 6 trades | Reduce next 5 trade sizes by 50% |
| Maximum loss per trade | 2% of equity | Hard stop loss, never moved further |

### Exposure Limits by Category

| Category | Max Exposure | Instruments Count Max |
|----------|-------------|---------------------|
| China Minerals | 15% | 4 |
| Copper Complex | 15% | 3 |
| Semiconductor | 15% | 3 |
| Energy / Uranium | 15% | 3 |
| Shipping / Chokepoints | 12% | 3 |
| Agriculture | 12% | 3 |
| Safe Haven (Gold, CHF, JPY) | 10% | 2 |
| Forex Only | 12% | 4 |

## D.2 Circuit Breakers

### Drawdown-Based Circuit Breakers

```
LEVEL 1 — YELLOW (5% drawdown):
  ▶ Reduce new position sizes by 50%
  ▶ Increase confirmation threshold to 0.70
  ▶ Alert: Telegram notification
  ▶ Resume: When DD recovers to <3%

LEVEL 2 — ORANGE (7.5% drawdown):
  ▶ No new positions allowed
  ▶ Tighten all stops to 1.5x ATR (from 2x)
  ▶ Alert: Telegram + email
  ▶ Resume: Manual review required + DD < 5%

LEVEL 3 — RED (10% drawdown):
  ▶ CLOSE ALL POSITIONS AT MARKET
  ▶ Disable EA trading
  ▶ Alert: Telegram + email + desktop
  ▶ Resume: Full system review + 48h cooling period + DD < 5%

LEVEL 4 — BLACK (15% drawdown):
  ▶ Close all + disable EA + disable Python engine
  ▶ Alert: All channels
  ▶ Resume: Complete strategy overhaul required
```

### Volatility-Based Circuit Breakers

| Condition | Action |
|-----------|--------|
| VIX > 40 | Reduce all positions to 50% of normal size |
| VIX > 50 | Close all except safe-haven positions (gold, CHF) |
| Any instrument gaps > 5% against position | Close that position immediately |
| Flash crash detected (>5% move in <5 min) | Close all market orders, switch to limit only |
| Weekend gap risk (Friday close) | Reduce all positions to 50% before weekend |

### System-Based Circuit Breakers

| Condition | Action |
|-----------|--------|
| MT5 disconnected > 2 minutes | Alert + attempt reconnect |
| MT5 disconnected > 10 minutes | Close all positions via backup |
| Python engine crash | Alert + auto-restart + no new trades for 15 min |
| Data feed down > 30 minutes | Pause signal generation, keep existing positions |
| Database write failure | Alert + write to backup file + pause new trades |

## D.3 Correlation Matrix — Full

### Live Correlation Matrix (update daily)

| | COPPER | AUDUSD | FCX | USDCNH | REMX | SOXX | URA | CCJ | WHEAT | COCOA | XTIUSD | USDNOK | ZIM | XAUUSD |
|---|--------|--------|-----|--------|------|------|-----|-----|-------|-------|--------|--------|-----|--------|
| **COPPER** | 1.00 | 0.72 | 0.85 | -0.45 | 0.55 | 0.30 | 0.15 | 0.12 | 0.10 | 0.08 | 0.25 | -0.20 | 0.05 | 0.15 |
| **AUDUSD** | — | 1.00 | 0.68 | -0.52 | 0.48 | 0.22 | 0.18 | 0.15 | 0.05 | 0.03 | 0.20 | -0.35 | 0.02 | 0.10 |
| **FCX** | — | — | 1.00 | -0.40 | 0.52 | 0.28 | 0.12 | 0.10 | 0.08 | 0.05 | 0.22 | -0.18 | 0.05 | 0.12 |
| **USDCNH** | — | — | — | 1.00 | -0.35 | -0.15 | -0.08 | -0.05 | 0.05 | 0.02 | -0.10 | 0.30 | -0.02 | -0.15 |
| **REMX** | — | — | — | — | 1.00 | 0.42 | 0.25 | 0.20 | 0.02 | 0.00 | 0.12 | -0.15 | 0.00 | 0.08 |
| **SOXX** | — | — | — | — | — | 1.00 | 0.10 | 0.08 | -0.05 | -0.02 | 0.08 | -0.05 | -0.03 | -0.10 |
| **URA** | — | — | — | — | — | — | 1.00 | 0.85 | 0.00 | 0.00 | 0.15 | -0.10 | 0.00 | 0.10 |
| **CCJ** | — | — | — | — | — | — | — | 1.00 | 0.00 | 0.00 | 0.12 | -0.08 | 0.00 | 0.08 |
| **WHEAT** | — | — | — | — | — | — | — | — | 1.00 | 0.15 | 0.30 | -0.10 | 0.10 | 0.20 |
| **COCOA** | — | — | — | — | — | — | — | — | — | 1.00 | 0.05 | -0.02 | 0.00 | 0.05 |
| **XTIUSD** | — | — | — | — | — | — | — | — | — | — | 1.00 | -0.55 | 0.15 | 0.10 |
| **USDNOK** | — | — | — | — | — | — | — | — | — | — | — | 1.00 | -0.05 | -0.15 |
| **ZIM** | — | — | — | — | — | — | — | — | — | — | — | — | 1.00 | -0.05 |
| **XAUUSD** | — | — | — | — | — | — | — | — | — | — | — | — | — | 1.00 |

### Correlation Rules

```
ρ > 0.70:  ONLY one position allowed. Take the higher-confidence signal.
           Pairs: COPPER↔FCX, COPPER↔AUDUSD, URA↔CCJ, ASML↔SOXX

ρ 0.50-0.70: Both allowed but REDUCE combined size by 30%.
              Pairs: COPPER↔REMX, AUDUSD↔FCX, ABB↔ETN, ADM↔BG

ρ 0.30-0.50: Both allowed at normal size. MONITOR if adding a third.

ρ < 0.30:   Fully independent. No size adjustment needed.
```

## D.4 Maximum Exposure Per Sector

### Sector Limits Visualization

```
                       TOTAL PORTFOLIO EXPOSURE CAP: 50% MARGIN
                       ┌──────────────────────────────────────┐
                       │                                      │

  China Minerals ████████████████░░░░ 15% max
  Copper Complex ████████████████░░░░ 15% max
  Semiconductor  ████████████████░░░░ 15% max
  Energy/Nuclear ████████████████░░░░ 15% max
  Ship/Chokepoint██████████████░░░░░░ 12% max
  Agriculture    ██████████████░░░░░░ 12% max
  Safe Haven     ████████████░░░░░░░░ 10% max
  Forex Only     ██████████████░░░░░░ 12% max

  Note: Total can exceed 100% since categories overlap.
  HARD LIMIT: Total margin used never exceeds 50%.
```

### Sector Overlap Resolution

When an instrument belongs to multiple sectors:

```
Example: AUDUSD is in both "Copper Complex" and "Forex Only"
Rule: Count toward BOTH sector caps.
Effect: Limits the total size of cross-sector positions.

Example: USDCNH is in "China Minerals" and "Forex Only"
Rule: Count toward BOTH.
Effect: A large China Minerals FX position reduces Forex-only capacity.
```

## D.5 Risk Budget Allocation

### Monthly Risk Budget

```
Total Monthly Risk Budget: 10% of equity (maximum drawdown allowed)

Allocation:
  Tier 1 (Top 10 inefficiencies): 6% risk budget
  Tier 2 (Other active):          3% risk budget
  Event-driven reserve:           1% risk budget (held for sudden events)

Per-trade risk:
  Tier 1: 1.5-2.0% per trade
  Tier 2: 0.5-1.0% per trade
  Event:  2.0-3.0% per trade (higher conviction, lower frequency)
```

### Risk Monitoring Dashboard Thresholds

| Metric | Green | Yellow | Orange | Red |
|--------|-------|--------|--------|-----|
| Drawdown | <3% | 3-5% | 5-7.5% | >7.5% |
| Daily P&L | >-1% | -1% to -2% | -2% to -3% | >-3% |
| Margin Used | <25% | 25-35% | 35-45% | >45% |
| Open Positions | 3-7 | 7-9 | 9-10 | >10 |
| Correlation Avg | <0.3 | 0.3-0.5 | 0.5-0.7 | >0.7 |
| Win Rate (30d) | >55% | 45-55% | 40-45% | <40% |
| Sharpe (30d) | >1.5 | 1.0-1.5 | 0.5-1.0 | <0.5 |

---

# REVISION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-11-15 | Initial complete playbook |

---

> **DISCLAIMER:** This playbook is for educational and informational purposes. Trading CFDs and forex involves significant risk of loss. Past performance is not indicative of future results. All specific numbers, thresholds, and parameters require validation through backtesting before live deployment. Never risk more than you can afford to lose.

---

*Generated by SCI Trading System — Supply Chain Inefficiency Research*
*Document version: 1.0 | Last updated: 2026-11-15*
