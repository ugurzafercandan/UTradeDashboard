"""65-feature computation engine for ML signal server.

Computes 7 categories of features on H1 OHLCV bars with strict lag-1
alignment to prevent look-ahead bias.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtesting.indicators import (
    compute_atr,
    compute_bollinger_bands,
    compute_macd,
    compute_rsi,
)

_EPSILON = 1e-10

FEATURE_NAMES: list[str] = [
    # Category 1: Candle Structure (7)
    "body_size",
    "body_ratio",
    "upper_shadow",
    "lower_shadow",
    "upper_shadow_ratio",
    "lower_shadow_ratio",
    "is_bullish",
    # Category 2: Returns & Momentum (7)
    "ret_1",
    "ret_5",
    "ret_15",
    "ret_60",
    "roc_5",
    "roc_10",
    "roc_20",
    # Category 3: Moving Averages (12)
    "sma_5",
    "sma_10",
    "sma_20",
    "sma_50",
    "sma_100",
    "sma_200",
    "ema_5",
    "ema_10",
    "ema_20",
    "ema_50",
    "ema_100",
    "ema_200",
    # Category 4: Price vs MA (8)
    "close_vs_sma_20",
    "close_vs_sma_50",
    "close_vs_sma_100",
    "close_vs_sma_200",
    "close_vs_ema_20",
    "close_vs_ema_50",
    "close_vs_ema_100",
    "close_vs_ema_200",
    # Category 5: Oscillators (8)
    "rsi_7",
    "rsi_14",
    "rsi_21",
    "macd_line",
    "macd_signal",
    "macd_hist",
    "stoch_k",
    "stoch_d",
    # Category 6: Volatility (9)
    "bb_upper",
    "bb_lower",
    "bb_mid",
    "bb_width",
    "bb_position",
    "atr_7",
    "atr_14",
    "atr_ratio",
    "range_pct",
    # Category 7: Volume & Session (14)
    "vol_sma_5",
    "vol_sma_20",
    "vol_ratio",
    "vwap",
    "close_vs_vwap",
    "session_asia",
    "session_london",
    "session_newyork",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "is_london_open",
    "is_ny_open",
]

assert len(FEATURE_NAMES) == 65


def get_feature_names() -> list[str]:
    """Return ordered list of all 65 feature names."""
    return list(FEATURE_NAMES)


def _candle_structure(df: pd.DataFrame) -> pd.DataFrame:
    o = df["open"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)  # noqa: E741
    c = df["close"].astype(float)

    body_size = (c - o).abs()
    hl_range = h - l + _EPSILON
    upper_body = np.maximum(o, c)
    lower_body = np.minimum(o, c)

    return pd.DataFrame(
        {
            "body_size": body_size,
            "body_ratio": body_size / hl_range,
            "upper_shadow": h - upper_body,
            "lower_shadow": lower_body - l,
            "upper_shadow_ratio": (h - upper_body) / hl_range,
            "lower_shadow_ratio": (lower_body - l) / hl_range,
            "is_bullish": (c > o).astype(float),
        },
        index=df.index,
    )


def _returns_momentum(closes: pd.Series) -> pd.DataFrame:
    log_close = np.log(closes.clip(lower=_EPSILON))
    return pd.DataFrame(
        {
            "ret_1": log_close.diff(1),
            "ret_5": log_close.diff(5),
            "ret_15": log_close.diff(15),
            "ret_60": log_close.diff(60),
            "roc_5": closes.pct_change(5) * 100,
            "roc_10": closes.pct_change(10) * 100,
            "roc_20": closes.pct_change(20) * 100,
        },
        index=closes.index,
    )


def _moving_averages(closes: pd.Series) -> pd.DataFrame:
    result: dict[str, pd.Series] = {}
    for p in (5, 10, 20, 50, 100, 200):
        result[f"sma_{p}"] = closes.rolling(window=p).mean()
    for p in (5, 10, 20, 50, 100, 200):
        result[f"ema_{p}"] = closes.ewm(span=p, adjust=False).mean()
    return pd.DataFrame(result, index=closes.index)


def _price_vs_ma(closes: pd.Series, ma_df: pd.DataFrame) -> pd.DataFrame:
    result: dict[str, pd.Series] = {}
    for p in (20, 50, 100, 200):
        sma = ma_df[f"sma_{p}"]
        result[f"close_vs_sma_{p}"] = (closes - sma) / (sma + _EPSILON)
    for p in (20, 50, 100, 200):
        ema = ma_df[f"ema_{p}"]
        result[f"close_vs_ema_{p}"] = (closes - ema) / (ema + _EPSILON)
    return pd.DataFrame(result, index=closes.index)


def _oscillators(
    closes: pd.Series,
    highs: pd.Series,
    lows: pd.Series,
) -> pd.DataFrame:
    rsi_7 = compute_rsi(closes, period=7)
    rsi_14 = compute_rsi(closes, period=14)
    rsi_21 = compute_rsi(closes, period=21)

    macd_line, macd_signal_line, macd_histogram = compute_macd(closes)

    # Stochastic %K (14,3): smooth raw %K with 3-period SMA
    lowest_14 = lows.rolling(window=14).min()
    highest_14 = highs.rolling(window=14).max()
    raw_k = (closes - lowest_14) / (highest_14 - lowest_14 + _EPSILON) * 100
    stoch_k = raw_k.rolling(window=3).mean()
    stoch_d = stoch_k.rolling(window=3).mean()

    return pd.DataFrame(
        {
            "rsi_7": rsi_7,
            "rsi_14": rsi_14,
            "rsi_21": rsi_21,
            "macd_line": macd_line,
            "macd_signal": macd_signal_line,
            "macd_hist": macd_histogram,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
        },
        index=closes.index,
    )


def _volatility(
    closes: pd.Series,
    highs: pd.Series,
    lows: pd.Series,
) -> pd.DataFrame:
    bb_upper, bb_mid, bb_lower = compute_bollinger_bands(closes, period=20, num_std=2.0)
    bb_width = bb_upper - bb_lower
    bb_position = (closes - bb_lower) / (bb_width + _EPSILON)

    atr_7 = compute_atr(highs, lows, closes, period=7)
    atr_14 = compute_atr(highs, lows, closes, period=14)

    return pd.DataFrame(
        {
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_mid": bb_mid,
            "bb_width": bb_width,
            "bb_position": bb_position,
            "atr_7": atr_7,
            "atr_14": atr_14,
            "atr_ratio": atr_7 / (atr_14 + _EPSILON),
            "range_pct": (highs - lows) / (closes + _EPSILON) * 100,
        },
        index=closes.index,
    )


def _volume_session(df: pd.DataFrame) -> pd.DataFrame:
    volume = df["volume"].astype(float)
    closes = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)

    vol_sma_5 = volume.rolling(window=5).mean()
    vol_sma_20 = volume.rolling(window=20).mean()
    vol_ratio = volume / (vol_sma_20 + _EPSILON)

    # VWAP with daily reset
    typical_price = (highs + lows + closes) / 3.0
    vp = volume * typical_price

    time_col = pd.to_datetime(df["time"])
    dates = time_col.dt.date
    cum_vp = vp.groupby(dates).cumsum()
    cum_vol = volume.groupby(dates).cumsum()
    vwap = cum_vp / (cum_vol + _EPSILON)

    # Session and time features from UTC hour
    hour = time_col.dt.hour
    dow = time_col.dt.day_of_week  # 0=Monday

    session_asia = ((hour >= 0) & (hour < 8)).astype(float)
    session_london = ((hour >= 8) & (hour < 16)).astype(float)
    session_newyork = ((hour >= 13) & (hour < 21)).astype(float)

    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)
    dow_sin = np.sin(2 * np.pi * dow / 5)
    dow_cos = np.cos(2 * np.pi * dow / 5)

    is_london_open = ((hour >= 7) & (hour <= 9)).astype(float)
    is_ny_open = ((hour >= 13) & (hour <= 15)).astype(float)

    close_vs_vwap = (closes - vwap) / (vwap + _EPSILON)

    return pd.DataFrame(
        {
            "vol_sma_5": vol_sma_5,
            "vol_sma_20": vol_sma_20,
            "vol_ratio": vol_ratio,
            "vwap": vwap,
            "close_vs_vwap": close_vs_vwap,
            "session_asia": session_asia,
            "session_london": session_london,
            "session_newyork": session_newyork,
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "dow_sin": dow_sin,
            "dow_cos": dow_cos,
            "is_london_open": is_london_open,
            "is_ny_open": is_ny_open,
        },
        index=df.index,
    )


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all 65 features on H1 OHLCV data.

    Args:
        df: DataFrame with columns: time, open, high, low, close, volume.
            Must be sorted by time ascending.

    Returns:
        DataFrame with 65 feature columns added. First ~200 rows will have
        NaNs due to lookback requirements (SMA-200 is the longest).
    """
    closes = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)

    cat1 = _candle_structure(df)
    cat2 = _returns_momentum(closes)
    cat3 = _moving_averages(closes)
    cat4 = _price_vs_ma(closes, cat3)
    cat5 = _oscillators(closes, highs, lows)
    cat6 = _volatility(closes, highs, lows)
    cat7 = _volume_session(df)

    features = pd.concat([cat1, cat2, cat3, cat4, cat5, cat6, cat7], axis=1)
    assert list(features.columns) == FEATURE_NAMES
    return features


def apply_lag1(features: pd.DataFrame) -> pd.DataFrame:
    """Shift all features by 1 bar to prevent look-ahead bias.

    The prediction target at bar[t] uses features from bar[t-1].
    Session/time features are NOT shifted — they describe bar[t] itself
    and are known in advance.
    """
    time_known = {
        "session_asia",
        "session_london",
        "session_newyork",
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "is_london_open",
        "is_ny_open",
    }
    shifted = features.copy()
    cols_to_shift = [c for c in features.columns if c not in time_known]
    shifted[cols_to_shift] = features[cols_to_shift].shift(1)
    return shifted
