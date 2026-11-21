"""Signal generator — orchestrates feature computation, model inference, and signal file output.

Runs on a schedule (default: every H1 bar close) to:
1. Fetch latest H1 bars for each configured symbol
2. Compute 65-feature set with lag-1 alignment
3. Run model inference for each signal
4. Write signal JSON files for MT5 EA consumption
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from ml_signal_server.feature_engine import apply_lag1, compute_features, get_feature_names
from ml_signal_server.model_server import ModelServer
from ml_signal_server.signal_config import ALL_SIGNALS, SignalConfig


class SignalGenerator:
    def __init__(
        self,
        output_dir: str = "MQL5/Files",
        models_dir: str = "models/ml_signals",
        max_spread_multiple: float = 2.0,
    ):
        self.output_dir = output_dir
        self.max_spread_multiple = max_spread_multiple
        self.model_server = ModelServer(models_dir=models_dir)
        self._feature_cache: dict[str, pd.DataFrame] = {}
        self._typical_spreads: dict[str, float] = {}
        self._staleness_tracker: dict[str, list[bool]] = {}

        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def initialize(self, signal_ids: list[str] | None = None) -> dict[str, bool]:
        signals = {k: v for k, v in ALL_SIGNALS.items() if signal_ids is None or k in signal_ids}
        status = self.model_server.load_all(signals)
        loaded = sum(1 for v in status.values() if v)
        logger.info("Loaded {}/{} models", loaded, len(signals))
        return status

    def generate_signals(
        self,
        price_data: dict[str, pd.DataFrame],
        current_spreads: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        signals_written = []

        for signal_id, config in ALL_SIGNALS.items():
            if config.symbol not in price_data:
                logger.warning("No price data for {} ({})", config.symbol, signal_id)
                continue

            df = price_data[config.symbol]
            if len(df) < 250:
                logger.warning("Insufficient bars for {} ({}): {} bars", config.symbol, signal_id, len(df))
                continue

            features = self._compute_or_cache(config.symbol, df)
            if features is None or len(features) == 0:
                continue

            confidence, direction = self.model_server.predict(signal_id, features)

            spread_ok = True
            if current_spreads and config.symbol in current_spreads:
                typical = self._typical_spreads.get(config.symbol)
                current = current_spreads[config.symbol]
                if typical and current > typical * self.max_spread_multiple:
                    spread_ok = False
                    logger.info("Spread too wide for {} ({}): {:.5f} > {:.5f}",
                                config.symbol, signal_id, current, typical * self.max_spread_multiple)

            atr_value = self._get_latest_atr(features)

            self._track_staleness(signal_id, direction)

            if self._is_stale(signal_id):
                direction = "HOLD"
                logger.warning("Model {} flagged stale — forcing HOLD", signal_id)

            signal = {
                "signal_id": signal_id,
                "symbol": config.symbol,
                "direction": direction,
                "confidence": round(confidence, 4),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "atr": round(atr_value, 6) if atr_value else 0.0,
                "spread_ok": spread_ok,
                "tier": config.tier,
                "magic_number": config.magic_number,
                "exit_method": config.exit_method,
                "entry_threshold": config.entry_threshold,
            }

            self._write_signal_file(signal_id, signal)
            signals_written.append(signal)

        logger.info("Generated {} signals", len(signals_written))
        return signals_written

    def _compute_or_cache(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame | None:
        cache_key = symbol
        if cache_key in self._feature_cache:
            cached = self._feature_cache[cache_key]
            if len(cached) == len(df):
                return cached

        try:
            # B1 fix: normalize EET broker timestamps to UTC before feature computation.
            # MT5/broker parquet data arrives in EET (UTC+2 winter / UTC+3 summer).
            # feature_engine._volume_session() uses UTC windows, so mis-labelled
            # timestamps shift session features 2–3 hours and corrupt predictions.
            df = df.copy()
            if df.index.dtype != "datetime64[ns, UTC]":
                try:
                    if hasattr(df.index, "tz") and df.index.tz is not None:
                        df.index = df.index.tz_convert("UTC")
                    else:
                        df.index = pd.to_datetime(df.index).tz_localize("EET").tz_convert("UTC")
                except Exception:
                    df.index = pd.to_datetime(df.index).tz_localize("Europe/Helsinki").tz_convert("UTC")
            if "time" in df.columns:
                try:
                    df["time"] = pd.to_datetime(df["time"])
                    if df["time"].dt.tz is None:
                        df["time"] = df["time"].dt.tz_localize("Europe/Helsinki").dt.tz_convert("UTC")
                    else:
                        df["time"] = df["time"].dt.tz_convert("UTC")
                except Exception:
                    pass

            features = compute_features(df)
            features = apply_lag1(features)
            self._feature_cache[cache_key] = features
            return features
        except Exception as e:
            logger.error("Feature computation failed for {}: {}", symbol, e)
            return None

    def _get_latest_atr(self, features: pd.DataFrame) -> float | None:
        if "atr_14" in features.columns:
            val = features["atr_14"].dropna()
            if len(val) > 0:
                return float(val.iloc[-1])
        return None

    def _track_staleness(self, signal_id: str, direction: str) -> None:
        if signal_id not in self._staleness_tracker:
            self._staleness_tracker[signal_id] = []
        is_correct = direction != "HOLD"
        self._staleness_tracker[signal_id].append(is_correct)
        if len(self._staleness_tracker[signal_id]) > 720:
            self._staleness_tracker[signal_id] = self._staleness_tracker[signal_id][-720:]

    def _is_stale(self, signal_id: str) -> bool:
        history = self._staleness_tracker.get(signal_id, [])
        if len(history) < 720:
            return False
        recent = history[-720:]
        accuracy = sum(recent) / len(recent)
        return accuracy < 0.52

    def _write_signal_file(self, signal_id: str, signal: dict[str, Any]) -> None:
        filename = f"ml_signal_{signal_id}.json"
        filepath = os.path.join(self.output_dir, filename)
        tmp_path = filepath + ".tmp"

        try:
            with open(tmp_path, "w") as f:
                json.dump(signal, f)
            # N1 fix: os.replace() is atomic on POSIX and handles existing file on
            # Windows, eliminating the remove→rename gap where MT5 EA gets INVALID_HANDLE.
            os.replace(tmp_path, filepath)
        except Exception as e:
            logger.error("Failed to write signal file {}: {}", filename, e)

    def update_typical_spreads(self, spreads: dict[str, float]) -> None:
        for symbol, spread in spreads.items():
            if symbol not in self._typical_spreads:
                self._typical_spreads[symbol] = spread
            else:
                self._typical_spreads[symbol] = 0.95 * self._typical_spreads[symbol] + 0.05 * spread


class SignalServerRunner:
    def __init__(
        self,
        generator: SignalGenerator,
        fetch_fn: Any = None,
        interval_seconds: int = 3600,
    ):
        self.generator = generator
        self.fetch_fn = fetch_fn
        self.interval_seconds = interval_seconds
        self._running = False

    def run_once(self, price_data: dict[str, pd.DataFrame], spreads: dict[str, float] | None = None) -> list[dict]:
        if spreads:
            self.generator.update_typical_spreads(spreads)
        return self.generator.generate_signals(price_data, spreads)

    def run_loop(self) -> None:
        if not self.fetch_fn:
            raise ValueError("fetch_fn required for run_loop")

        self._running = True
        logger.info("Signal server starting, interval={}s", self.interval_seconds)

        while self._running:
            try:
                price_data, spreads = self.fetch_fn()
                self.run_once(price_data, spreads)
            except Exception as e:
                logger.error("Signal generation cycle failed: {}", e)

            time.sleep(self.interval_seconds)

    def stop(self) -> None:
        self._running = False
