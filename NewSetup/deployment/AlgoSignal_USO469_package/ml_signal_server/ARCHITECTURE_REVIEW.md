# Architecture Critic Review — ML Signal Server + MT5 EA Portfolio (USO-465)

## 1. Latency Risk: File-Based Signal Delivery

**Risk:** File-based IPC (Python writes JSON, EA polls) adds 100-500ms latency depending on polling interval and OS file-system caching.

**Mitigation:**
- Signals operate on H1 bars — direction changes at most once per hour. Sub-second latency is irrelevant.
- Atomic writes: Python writes to `.tmp`, then `os.rename()` to the final path. EA never reads a half-written file.
- EA polls every 1 second — worst-case delivery delay is 1s, well within tolerance.
- Socket-based delivery (ZMQ, named pipes) would add deployment complexity for no measurable benefit at H1 granularity.

**What we build:** Atomic file writes, 1s EA poll loop, staleness check (reject signals older than 2 bars / 2 hours).

## 2. Model Staleness

**Risk:** GBDT models are trained once on historical data. Market regimes shift — a model that worked in 2023-2024 may degrade in 2025+. No live retraining loop exists.

**Mitigation:**
- Track rolling 30-day OOS accuracy in the signal server (compare predicted direction to actual H1 close direction).
- If rolling accuracy drops below 52% (random baseline + typical spread cost), suppress directional signals — emit HOLD only.
- Log staleness metrics (accuracy, confidence distribution, prediction entropy) to `logs/model_health.csv`.
- Retraining is a manual process triggered by the CTO when metrics degrade — we flag, we don't automate retraining yet.

**What we build:** `ModelHealthMonitor` class that tracks per-signal accuracy, logs metrics, and gates signal emission.

## 3. Feature Drift

**Risk:** Feature distributions shift over time (volatility regimes, correlation structure, session patterns). A model trained on 2023 features may receive 2025 inputs that are far out-of-distribution.

**Mitigation:**
- Store training-time feature statistics (mean, std, min, max) in each signal's config JSON.
- At inference time, compute z-scores of live features vs training distributions.
- If any feature exceeds |z| > 3.0, log a WARNING and reduce signal confidence by 50%.
- If >20% of features exceed |z| > 3.0 simultaneously, emit HOLD (regime has likely shifted).

**What we build:** Feature drift detector in `feature_engine.py`, training stats in signal config files.

## 4. Survivorship Bias

**Risk:** The 27 signals survived walk-forward validation across multiple model types and parameters. The selection process itself is a form of multiple hypothesis testing — some signals may be statistical flukes.

**Mitigation:**
- Tier-based allocation already discounts weaker signals: Tier A (Sharpe > 4.5) = 100%, Tier B (2.0-4.5) = 75%, Tier C (< 2.0) = 50%.
- 6-month paper-trading burn-in: new signals start at 50% of their tier allocation and scale up only if live accuracy exceeds 53%.
- The dashboard at UTradeDashboard shows live forward-test results — that is ground truth. Backtest Sharpe is marketing; live equity is real.
- Bonferroni-style adjustment: with 27 signals, expect ~1-2 false positives at p=0.05. The tier system absorbs this.

**What we build:** Tier-based sizing in `portfolio_manager.py`, paper-trade mode flag per signal, live accuracy tracking.

## 5. CHF Concentration Risk

**Risk:** 4 of 7 Tier A signals trade CHF pairs (CADCHF, AUDCHF, USDCHF, GBPCHF). CHF is the common factor — a single SNB intervention or CHF liquidity event would hit all four simultaneously.

**Mitigation:**
- Enforce max 40% portfolio notional exposure to any single currency across all open positions.
- When multiple CHF signals fire simultaneously, rank by confidence and allocate in order until the 40% currency cap is reached.
- Example: if CADCHF (P8, conf=0.85) and AUDCHF (P6, conf=0.80) and USDCHF (P7, conf=0.75) and GBPCHF (P11, conf=0.70) all fire, only the top 2-3 get full allocation; the remainder are reduced or skipped.
- Log all currency-cap rejections for post-analysis.

**What we build:** Currency exposure tracker in `portfolio_manager.py` with 40% per-currency cap, priority-by-confidence allocation.

## 6. Live vs Backtest Gap

**Risk:** The dashboard forward-test account is down 25.85%. Does this invalidate the entire approach?

**Analysis:**
- The live losses are from the 10 news-event EAs (Algo01-10) — rule-based event faders that are NOT the ML signals.
- The ML signals (P6-P27) are what USO-465 implements. They have not been live-traded yet.
- Backtest gaps for the news EAs were predictable: (a) spread costs absent from backtests, (b) slippage on news-event entries, (c) regime change since training period.
- The ML signals use H1 bars (not news events), GBDT models (not rules), and entry thresholds (not spike detection). Different architecture, different risk profile.

**Mitigation:**
- Include realistic spread costs in signal confidence (reduce confidence proportional to spread-to-ATR ratio).
- Track live fill quality vs signal price.
- If live ML signal performance diverges >2 Sharpe units from backtest within 3 months, trigger full review.

**What we build:** Spread-aware confidence adjustment, fill quality logging, performance divergence alerts.

## 7. Spread Widening

**Risk:** News events widen spreads 3-10x. If ML signals happen to fire during news windows, entry quality degrades.

**Analysis:** ML signals trade on H1 bar closes, not on news events. The probability of a signal coinciding with a high-spread window is lower than for news EAs, but not zero.

**Mitigation:**
- Before entry, check current spread < 2x the pair's typical spread (rolling 20-bar average spread).
- If spread exceeds threshold, skip this bar's entry and wait for next bar.
- Log all spread-at-entry values to detect systematic spread degradation.
- For pairs with consistently wide spreads (e.g., exotic CHF crosses), adjust the entry threshold upward.

**What we build:** Spread filter in the EA (`MLSignalFramework.mqh`), spread logging in signal metadata.

---

## Summary of Architectural Decisions

| Concern | Decision | Fallback |
|---------|----------|----------|
| Signal delivery | File-based JSON, atomic writes | Upgrade to ZMQ if latency proves problematic |
| Model health | Rolling accuracy monitor, auto-HOLD below 52% | Manual retrain trigger |
| Feature drift | Z-score monitor, confidence penalty at |z|>3 | HOLD if >20% features drifted |
| Multiple testing | Tier-based sizing, paper-trade burn-in | Demote/remove signals that fail live |
| CHF concentration | 40% per-currency cap | Reduce to 30% if correlation spikes |
| Live gap | Different system; spread-aware confidence | 3-month review gate |
| Spread widening | 2x spread filter, skip-bar logic | Pair-specific threshold tuning |

**Proceed with implementation. All mitigations are built into the code, not deferred.**
