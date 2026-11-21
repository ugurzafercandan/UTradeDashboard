"""Configuration for all 27 ML trading signals from AlgoSignal Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalConfig:
    signal_id: str
    symbol: str
    model_type: str  # "xgboost", "lightgbm", "catboost"
    exit_method: str  # "simple" or "triple_barrier"
    entry_threshold: float
    sharpe: float
    tier: str  # "A", "B", "C"
    magic_number: int
    label_forward: int  # lookahead bars for labeling (120 or 240)


TIER_SIZING: dict[str, float] = {"A": 1.0, "B": 0.75, "C": 0.50}

MAX_CURRENCY_EXPOSURE_PCT: float = 40.0

ALL_SIGNALS: dict[str, SignalConfig] = {
    # --- Tier A (7 signals) ---
    "P8": SignalConfig(
        signal_id="P8", symbol="CADCHF", model_type="lightgbm",
        exit_method="simple", entry_threshold=0.62, sharpe=39.40,
        tier="A", magic_number=46008, label_forward=120,
    ),
    "P6": SignalConfig(
        signal_id="P6", symbol="AUDCHF", model_type="xgboost",
        exit_method="simple", entry_threshold=0.65, sharpe=34.48,
        tier="A", magic_number=46006, label_forward=120,
    ),
    "P7": SignalConfig(
        signal_id="P7", symbol="USDCHF", model_type="xgboost",
        exit_method="triple_barrier", entry_threshold=0.58, sharpe=28.12,
        tier="A", magic_number=46007, label_forward=240,
    ),
    "P11": SignalConfig(
        signal_id="P11", symbol="GBPCHF", model_type="xgboost",
        exit_method="simple", entry_threshold=0.60, sharpe=24.58,
        tier="A", magic_number=46011, label_forward=120,
    ),
    "P16": SignalConfig(
        signal_id="P16", symbol="GBPAUD", model_type="xgboost",
        exit_method="simple", entry_threshold=0.60, sharpe=8.50,
        tier="A", magic_number=46016, label_forward=120,
    ),
    "P17": SignalConfig(
        signal_id="P17", symbol="GBPUSD", model_type="lightgbm",
        exit_method="simple", entry_threshold=0.60, sharpe=6.20,
        tier="A", magic_number=46017, label_forward=120,
    ),
    "P18": SignalConfig(
        signal_id="P18", symbol="CHFJPY", model_type="xgboost",
        exit_method="simple", entry_threshold=0.60, sharpe=4.50,
        tier="A", magic_number=46018, label_forward=120,
    ),
    # --- Tier B (10 signals) ---
    "P9": SignalConfig(
        signal_id="P9", symbol="NZDCHF", model_type="lightgbm",
        exit_method="simple", entry_threshold=0.58, sharpe=3.50,
        tier="B", magic_number=46009, label_forward=120,
    ),
    "P10": SignalConfig(
        signal_id="P10", symbol="EURCHF", model_type="xgboost",
        exit_method="simple", entry_threshold=0.60, sharpe=3.20,
        tier="B", magic_number=46010, label_forward=120,
    ),
    "P12": SignalConfig(
        signal_id="P12", symbol="AUDJPY", model_type="catboost",
        exit_method="simple", entry_threshold=0.58, sharpe=2.80,
        tier="B", magic_number=46012, label_forward=120,
    ),
    "P13": SignalConfig(
        signal_id="P13", symbol="EURAUD", model_type="xgboost",
        exit_method="triple_barrier", entry_threshold=0.55, sharpe=2.50,
        tier="B", magic_number=46013, label_forward=240,
    ),
    "P14": SignalConfig(
        signal_id="P14", symbol="NZDUSD", model_type="lightgbm",
        exit_method="simple", entry_threshold=0.58, sharpe=2.20,
        tier="B", magic_number=46014, label_forward=120,
    ),
    "P15": SignalConfig(
        signal_id="P15", symbol="CADJPY", model_type="xgboost",
        exit_method="simple", entry_threshold=0.60, sharpe=2.00,
        tier="B", magic_number=46015, label_forward=120,
    ),
    "P19": SignalConfig(
        signal_id="P19", symbol="GBPJPY", model_type="lightgbm",
        exit_method="simple", entry_threshold=0.58, sharpe=1.80,
        tier="B", magic_number=46019, label_forward=120,
    ),
    "P20": SignalConfig(
        signal_id="P20", symbol="EURUSD", model_type="xgboost",
        exit_method="simple", entry_threshold=0.55, sharpe=1.50,
        tier="B", magic_number=46020, label_forward=120,
    ),
    "P21": SignalConfig(
        signal_id="P21", symbol="USDJPY", model_type="catboost",
        exit_method="triple_barrier", entry_threshold=0.55, sharpe=1.20,
        tier="B", magic_number=46021, label_forward=240,
    ),
    "P22": SignalConfig(
        signal_id="P22", symbol="AUDUSD", model_type="xgboost",
        exit_method="simple", entry_threshold=0.55, sharpe=1.00,
        tier="B", magic_number=46022, label_forward=120,
    ),
    # --- Tier C (10 signals) ---
    "P23": SignalConfig(
        signal_id="P23", symbol="NZDJPY", model_type="lightgbm",
        exit_method="simple", entry_threshold=0.55, sharpe=0.80,
        tier="C", magic_number=46023, label_forward=120,
    ),
    "P24": SignalConfig(
        signal_id="P24", symbol="EURGBP", model_type="xgboost",
        exit_method="simple", entry_threshold=0.55, sharpe=0.70,
        tier="C", magic_number=46024, label_forward=120,
    ),
    "P25": SignalConfig(
        signal_id="P25", symbol="EURJPY", model_type="catboost",
        exit_method="simple", entry_threshold=0.55, sharpe=0.60,
        tier="C", magic_number=46025, label_forward=120,
    ),
    "P26": SignalConfig(
        signal_id="P26", symbol="GBPCAD", model_type="xgboost",
        exit_method="simple", entry_threshold=0.55, sharpe=0.50,
        tier="C", magic_number=46026, label_forward=120,
    ),
    "P27": SignalConfig(
        signal_id="P27", symbol="AUDCAD", model_type="lightgbm",
        exit_method="simple", entry_threshold=0.55, sharpe=0.40,
        tier="C", magic_number=46027, label_forward=120,
    ),
    "P28": SignalConfig(
        signal_id="P28", symbol="NZDCAD", model_type="xgboost",
        exit_method="simple", entry_threshold=0.55, sharpe=0.35,
        tier="C", magic_number=46028, label_forward=120,
    ),
    "P29": SignalConfig(
        signal_id="P29", symbol="CADJPY", model_type="lightgbm",
        exit_method="triple_barrier", entry_threshold=0.55, sharpe=0.30,
        tier="C", magic_number=46029, label_forward=240,
    ),
    "P30": SignalConfig(
        signal_id="P30", symbol="AUDNZD", model_type="xgboost",
        exit_method="simple", entry_threshold=0.55, sharpe=0.25,
        tier="C", magic_number=46030, label_forward=120,
    ),
    "P31": SignalConfig(
        signal_id="P31", symbol="GBPNZD", model_type="catboost",
        exit_method="simple", entry_threshold=0.55, sharpe=0.20,
        tier="C", magic_number=46031, label_forward=120,
    ),
    "P32": SignalConfig(
        signal_id="P32", symbol="EURNZD", model_type="xgboost",
        exit_method="simple", entry_threshold=0.55, sharpe=0.15,
        tier="C", magic_number=46032, label_forward=120,
    ),
}


def get_signals_by_tier(tier: str) -> dict[str, SignalConfig]:
    return {k: v for k, v in ALL_SIGNALS.items() if v.tier == tier}


def get_signals_by_symbol(symbol: str) -> dict[str, SignalConfig]:
    return {k: v for k, v in ALL_SIGNALS.items() if v.symbol == symbol}


def get_currency_signals(currency: str) -> dict[str, SignalConfig]:
    """Return signals where the currency appears in the pair."""
    return {
        k: v for k, v in ALL_SIGNALS.items()
        if currency in v.symbol[:3] or currency in v.symbol[3:]
    }
