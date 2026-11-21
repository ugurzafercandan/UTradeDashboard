"""Model inference wrapper for GBDT signal models (LightGBM/XGBoost/CatBoost)."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from ml_signal_server.signal_config import SignalConfig, ALL_SIGNALS

try:
    import joblib
    _HAS_JOBLIB = True
except ImportError:
    _HAS_JOBLIB = False


class ModelServer:
    def __init__(self, models_dir: str = "models/ml_signals"):
        self.models: dict[str, Any] = {}
        self.models_dir = models_dir

    def load_model(self, signal_id: str, config: SignalConfig) -> bool:
        """Load a trained model for the given signal. Returns True if loaded."""
        candidates = [
            os.path.join(self.models_dir, f"{signal_id}_{config.model_type}.pkl"),
            os.path.join(self.models_dir, f"{signal_id}_{config.model_type}.joblib"),
            os.path.join(self.models_dir, f"{signal_id}.pkl"),
        ]

        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                if _HAS_JOBLIB and path.endswith(".joblib"):
                    model = joblib.load(path)
                elif _HAS_JOBLIB:
                    try:
                        model = joblib.load(path)
                    except Exception:
                        with open(path, "rb") as f:
                            model = pickle.load(f)
                else:
                    with open(path, "rb") as f:
                        model = pickle.load(f)

                self.models[signal_id] = model
                # B4 fix: assert label convention {-1, 0, 1} → [SELL, HOLD, BUY].
                # predict() assumes proba[0]=SELL, proba[2]=BUY. If a model was trained
                # with labels {0,1,2} the mapping is silently inverted, causing systematic
                # BUY/SELL swaps. Catch this at load time, not at prediction time.
                if hasattr(model, "classes_"):
                    classes = list(model.classes_)
                    expected = [-1, 0, 1]
                    if classes != expected:
                        logger.error(
                            "Model {} has classes {} — expected {} (SELL=0, HOLD=1, BUY=2). "
                            "BUY/SELL would be swapped. Model NOT loaded.",
                            signal_id, classes, expected,
                        )
                        del self.models[signal_id]
                        return False
                    logger.debug("Model {} classes_ verified: {}", signal_id, classes)
                logger.info("Loaded model for {} from {}", signal_id, path)
                return True
            except Exception as exc:
                logger.warning("Failed to load model for {} from {}: {}", signal_id, path, exc)

        logger.debug("No model file found for {} (searched {})", signal_id, self.models_dir)
        return False

    def load_all(self, signals: dict[str, SignalConfig] | None = None) -> dict[str, bool]:
        """Load all available models. Returns status dict."""
        signals = signals or ALL_SIGNALS
        Path(self.models_dir).mkdir(parents=True, exist_ok=True)
        status: dict[str, bool] = {}
        for sid, cfg in signals.items():
            status[sid] = self.load_model(sid, cfg)
        loaded = sum(v for v in status.values())
        logger.info("Loaded {}/{} models from {}", loaded, len(signals), self.models_dir)
        return status

    def predict(
        self, signal_id: str, features: pd.DataFrame, config: SignalConfig | None = None,
    ) -> tuple[float, str]:
        """Run inference for a signal.

        Returns (confidence, direction) where confidence is 0-1 and
        direction is "BUY", "SELL", or "HOLD".
        """
        if signal_id not in self.models:
            return 0.0, "HOLD"

        model = self.models[signal_id]
        cfg = config or ALL_SIGNALS.get(signal_id)
        if cfg is None:
            return 0.0, "HOLD"

        row = features.iloc[[-1]]

        try:
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(row)[0]
                if len(proba) == 2:
                    buy_prob = float(proba[1])
                    sell_prob = 1.0 - buy_prob
                elif len(proba) >= 3:
                    sell_prob = float(proba[0])
                    buy_prob = float(proba[2]) if len(proba) > 2 else 0.0
                else:
                    return 0.0, "HOLD"

                confidence = max(buy_prob, sell_prob)
                if confidence >= cfg.entry_threshold:
                    direction = "BUY" if buy_prob >= sell_prob else "SELL"
                    return confidence, direction
                return confidence, "HOLD"
            else:
                pred = float(model.predict(row)[0])
                confidence = abs(pred)
                if confidence >= cfg.entry_threshold:
                    direction = "BUY" if pred > 0 else "SELL"
                    return min(confidence, 1.0), direction
                return min(confidence, 1.0), "HOLD"
        except Exception as exc:
            logger.error("Prediction failed for {}: {}", signal_id, exc)
            return 0.0, "HOLD"

    def predict_batch(
        self,
        features: pd.DataFrame,
        signals: dict[str, SignalConfig] | None = None,
    ) -> dict[str, tuple[float, str]]:
        """Run inference for all loaded models on the same features."""
        signals = signals or ALL_SIGNALS
        results: dict[str, tuple[float, str]] = {}
        for sid, cfg in signals.items():
            results[sid] = self.predict(sid, features, cfg)
        return results

    @property
    def loaded_count(self) -> int:
        return len(self.models)
