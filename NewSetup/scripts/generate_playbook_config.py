"""Generate NewSetup playbook config files from the SCI playbook source.

Parses Appendix A (the 40 inefficiency trade cards) directly out of
docs/sci_playbook_v1.md and encodes Appendix B (6 forex strategies) and
Appendix C (7 event response playbooks) as reviewed literals, then emits:

  config/trade_cards.yaml      - per-inefficiency entry/exit/invalidation/sizing
  config/fx_strategies.yaml    - FX-1..FX-6 strategy definitions
  config/event_responses.yaml  - C.1..C.7 event response playbooks
  config/gdelt_keywords.yaml   - per-inefficiency GDELT keyword theming

Run:  C:/Python314/python.exe NewSetup/scripts/generate_playbook_config.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "sci_playbook_v1.md"
CONFIG = ROOT / "config"

# Trade-card symbols that are referenced by the playbook but were missing
# from the original instruments.yaml. The generator asserts every referenced
# symbol is covered by instruments.yaml; add new ones here when the playbook
# introduces them (also append them to config/instruments.yaml).
INSTRUMENT_EXTENSIONS = [
    # forex (playbook Appendix B: FX-3, FX-4)
    "AUDJPY", "CHFJPY", "USDINR",
    # commodity CFDs (cards #21, #37 proxies; FX-4 / Appendix C safe haven)
    "SOYBEAN", "XAUUSD",
    # equity CFDs (card #11/#12 proxy instruments)
    "BA.US", "F.US", "GM.US",
]

STATUS_MAP = [
    ("🟢", "ACTIVE"),
    ("🟡", "MONITORING"),
    ("⚫", "NOT_TRADEABLE"),
    ("⚪", None),   # LOW PRIORITY / INDICATOR ONLY spelled out in text
]

# Symbols the playbook mentions only to state they are NOT available on
# Pepperstone (cards instruct to use the listed proxy instead).
NOT_ON_PLATFORM = {"USDMYR", "USDPEN", "USDTHB", "USDKRW", "USDTWD", "USDCLP"}


# --------------------------------------------------------------------------
# Appendix A parsing
# --------------------------------------------------------------------------
CARD_RE = re.compile(r"^## Trade Card #(\d+): (.+?)\s*$")
ROW_RE = re.compile(r"^\| \*\*([^|]+?)\*\* \| (.*) \|\s*$")
SYMBOL_RE = re.compile(r"`([A-Z0-9][A-Z0-9./]*)`")
TIME_STOP_RE = re.compile(r"[Tt]ime stop:?\s*(\d+)\s*day")
TP_RE = re.compile(r"TP:?\s*([^|]+?)(?=\s*(?:\||SL:|SL\s|$))")
SL_RE = re.compile(r"SL:?\s*([^|]+?)(?=\s*(?:\||Trailing|TP:|$))")
TRAILING_RE = re.compile(r"[Tt]railing[^|]*")
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _split_sections(text: str) -> str:
    start = text.index("# APPENDIX A:")
    end = text.index("# APPENDIX B:")
    return text[start:end]


def _normalize_status(raw: str) -> str:
    status = raw
    for emoji, name in STATUS_MAP:
        if emoji in status:
            status = status.replace(emoji, "").strip()
            if name:
                status = name if status == "" else f"{name} ({status})"
            break
    status = status.strip(" ()")
    if status.startswith("LOW PRIORITY"):
        return "LOW_PRIORITY"
    if status.startswith("INDICATOR ONLY"):
        return "INDICATOR_ONLY"
    if status.startswith("NOT TRADEABLE"):
        return "NOT_TRADEABLE"
    base = status.split(" (")[0].strip()
    return base or "MONITORING"


def _parse_exit_rules(raw: str) -> dict:
    components = [c.strip() for c in raw.split(" | ") if c.strip()]
    time_stop_days = None
    m = TIME_STOP_RE.search(raw)
    if m:
        time_stop_days = int(m.group(1))
    tps = [t.strip().rstrip() for t in TP_RE.findall(raw)]
    sls = [s.strip() for s in SL_RE.findall(raw)]
    trailing = TRAILING_RE.search(raw)
    return {
        "raw": raw,
        "components": components,
        "take_profit": tps,
        "stop_loss": sls,
        "time_stop_days": time_stop_days,
        "trailing": trailing.group(0).strip() if trailing else None,
    }


def _parse_position_sizing(raw: str) -> dict:
    pcts = [float(p) for p in PCT_RE.findall(raw)]
    sector_cap = None
    m = re.search(r"cap (\d+(?:\.\d+)?)%", raw)
    if m:
        sector_cap = float(m.group(1))
    combined = None
    m = re.search(r"(\d+(?:\.\d+)?)%\s*combined|combined\s*(\d+(?:\.\d+)?)%", raw, re.I)
    if m:
        combined = float(m.group(1) or m.group(2))
    return {
        "raw": raw,
        "max_position_pct": pcts[0] if pcts else None,
        "max_combined_pct": combined,
        "sector_cap_pct": sector_cap,
        "all_pcts": pcts,
    }


def parse_trade_cards() -> list[dict]:
    text = DOC.read_text(encoding="utf-8")
    section = _split_sections(text)
    cards: list[dict] = []
    current: dict | None = None
    for line in section.splitlines():
        m = CARD_RE.match(line)
        if m:
            current = {"id": int(m.group(1)), "name": m.group(2).strip(), "fields": {}}
            cards.append(current)
            continue
        if current is None:
            continue
        m = ROW_RE.match(line)
        if m:
            current["fields"][m.group(1).strip()] = m.group(2).strip()
    out: list[dict] = []
    for c in cards:
        f = c["fields"]
        status_raw = f.get("Status", "")
        tier = None
        score = None
        tm = re.search(r"Tier (\d)", status_raw)
        if tm:
            tier = int(tm.group(1))
        sm = re.search(r"score (\d+(?:\.\d+)?)/10", status_raw)
        if sm:
            score = float(sm.group(1))
        entry_raw = f.get("Entry Rules", "")
        exit_raw = f.get("Exit Rules", "")
        sizing_raw = f.get("Position Sizing", "")
        exit_parsed = _parse_exit_rules(exit_raw)
        invalidation = []
        if exit_parsed["stop_loss"]:
            invalidation.append(f"Stop loss: {', '.join(exit_parsed['stop_loss'])}")
        if exit_parsed["time_stop_days"]:
            invalidation.append(f"Time stop: {exit_parsed['time_stop_days']} days")
        if exit_parsed["trailing"]:
            invalidation.append(exit_parsed["trailing"])
        primary = [s for s in SYMBOL_RE.findall(f.get("Primary Instruments", ""))
                   if s not in NOT_ON_PLATFORM]
        proxy = [s for s in SYMBOL_RE.findall(f.get("Proxy Instruments", ""))
                 if s not in NOT_ON_PLATFORM]
        out.append({
            "id": c["id"],
            "name": c["name"],
            "category": f.get("Category", ""),
            "status": _normalize_status(status_raw),
            "tier": tier,
            "opportunity_score": score,
            "description": f.get("Description", ""),
            "supply_concentration": f.get("Supply Concentration", ""),
            "trigger_scenarios": [s.strip() for s in f.get("Trigger Scenarios", "").split(";") if s.strip()],
            "primary_instruments": primary,
            "proxy_instruments": proxy,
            "entry_rules": {
                "raw": entry_raw,
                "scenarios": [s.strip() for s in entry_raw.split(" | ") if s.strip()],
            },
            "exit_rules": exit_parsed,
            "invalidation_conditions": invalidation,
            "position_sizing": _parse_position_sizing(sizing_raw),
            "correlations_note": f.get("Correlations", ""),
            "backtest_results": f.get("Backtest Results", ""),
        })
    return out


# --------------------------------------------------------------------------
# Appendix B: forex strategies (encoded literals from playbook B.1-B.7)
# --------------------------------------------------------------------------
FX_STRATEGIES = [
    {
        "id": "FX-1",
        "name": "Commodity Currency Basket",
        "description": ("Trade AUD, CAD, NOK as commodity proxy currencies during broad "
                        "supply chain disruption events that push commodity prices higher."),
        "trigger": "Broad commodity cycle",
        "avg_duration_days": [5, 15],
        "expected_frequency": "2-4 /month",
        "instruments": [
            {"symbol": "AUDUSD", "direction": "LONG", "risk_pct": 3,
             "rationale": "Australia = iron ore, copper, gold, bauxite, coal",
             "entry": {"metric": "rsi.AUDUSD", "op": "<", "value": 45}},
            {"symbol": "USDCAD", "direction": "SHORT", "risk_pct": 3,
             "rationale": "Canada = oil, uranium, potash, forestry",
             "entry": {"metric": "rsi.USDCAD", "op": ">", "value": 55}},
            {"symbol": "USDNOK", "direction": "SHORT", "risk_pct": 2,
             "rationale": "Norway = oil, gas, fish, metals (wider spreads -> smaller size)",
             "entry": {"metric": "rsi.USDNOK", "op": ">", "value": 55}},
        ],
        "entry_variants": {
            "default": [
                {"any": [
                    {"metric": "gdelt.supply_chain_disruption_index", "op": ">", "value": 0.6},
                    {"metric": "bcom.pct_above_200dma", "op": ">", "value": 5},
                ]},
                {"all": [{"metric": "dxy.below_200dma", "op": "==", "value": True}]},
                {"majority": {"min_required": 2, "conditions": [
                    {"metric": "rsi.AUDUSD", "op": "<", "value": 45},
                    {"metric": "rsi.USDCAD", "op": ">", "value": 55},
                    {"metric": "rsi.USDNOK", "op": ">", "value": 55},
                ]}},
            ],
        },
        "position_sizing": {
            "max_total_risk_pct": 8,
            "per_instrument_risk_pct": {"AUDUSD": 3, "USDCAD": 3, "USDNOK": 2},
            "stop": "1.5x ATR(14) from entry",
            "take_profit": "3.0x ATR(14) from entry (2:1 R:R)",
        },
        "exit_rules": [
            "Profit target: TP hit on individual pairs -> close that pair",
            "Stop loss: SL hit on individual pairs -> close that pair",
            "Basket close: if 2 of 3 pairs hit SL -> close remaining pair immediately",
            "Time stop: 15 trading days maximum",
            "Regime change: DXY crosses above 200-DMA -> close all",
        ],
    },
    {
        "id": "FX-2",
        "name": "China Export Ban Event",
        "description": ("Fast-acting event trade when China announces or signals export "
                        "restrictions on critical minerals (gallium, germanium, antimony, "
                        "rare earths, graphite, magnesium, polysilicon)."),
        "trigger": "China critical mineral restriction",
        "avg_duration_days": [2, 7],
        "expected_frequency": "1-3 /quarter",
        "instruments": [
            {"symbol": "USDCNH", "direction": "SHORT", "risk_pct": 3,
             "rationale": "CNH strengthens on export control (reduced supply -> higher value of Chinese goods)",
             "entry": {"metric": "usdcnh.level", "op": ">", "value": 7.10}},
            {"symbol": "AUDUSD", "direction": "LONG", "risk_pct": 2,
             "rationale": "Australia benefits as alternative supplier",
             "entry": None},
        ],
        "entry_variants": {
            "fast": [
                {"any": [
                    {"metric": "gdelt.china_mineral_export_ban_score", "op": ">", "value": 0.8},
                    {"metric": "news.confirmed_headline_reuters_bloomberg", "op": "==", "value": True},
                ]},
                {"all": [
                    {"metric": "usdcnh.level", "op": ">", "value": 7.10},
                    {"metric": "portfolio.china_minerals_open_positions", "op": "==", "value": 0},
                ]},
            ],
            "confirmed": [
                {"all": [{"metric": "finbert.china_export_news", "op": "<", "value": -0.5}]},
                {"any": [
                    {"metric": "macd.USDCNH.bearish_crossover", "op": "==", "value": True},
                    {"metric": "macd.AUDUSD.bullish_crossover", "op": "==", "value": True},
                ]},
            ],
        },
        "position_sizing": {
            "max_total_risk_pct": 5,
            "per_instrument_risk_pct": {"USDCNH": 3, "AUDUSD": 2},
            "stop_pips": {"USDCNH": 120, "AUDUSD": 60},
            "take_profit_pips": {"USDCNH": 250, "AUDUSD": 120},
        },
        "exit_rules": [
            "Profit target: scale out 50% at 150 pips (CNH) / 80 pips (AUD), remainder at full TP",
            "Stop loss: hard stop, no averaging down",
            "Reversal: if China announces exemptions/rollback within 48h -> close immediately",
            "Time stop: 7 trading days (event fading)",
        ],
    },
    {
        "id": "FX-3",
        "name": "Chokepoint / Oil Shock",
        "description": ("Trade oil-correlated currencies when a major maritime chokepoint is "
                        "disrupted (Red Sea, Hormuz, Malacca, Panama)."),
        "trigger": "Strait closure / oil spike",
        "avg_duration_days": [3, 10],
        "expected_frequency": "1-2 /quarter",
        "instruments": [
            {"symbol": "USDNOK", "direction": "SHORT", "risk_pct": 3,
             "rationale": "Norway is major oil exporter -> NOK strengthens",
             "entry": {"metric": "rsi.USDNOK", "op": ">", "value": 50}},
            {"symbol": "USDCAD", "direction": "SHORT", "risk_pct": 3,
             "rationale": "Canada is major oil exporter -> CAD strengthens",
             "entry": {"metric": "rsi.USDCAD", "op": ">", "value": 50}},
            {"symbol": "USDINR", "direction": "LONG", "risk_pct": 2,
             "rationale": "India is major oil importer -> INR weakens (wider spread)",
             "entry": {"metric": "rsi.USDINR", "op": "<", "value": 65}},
            {"symbol": "USDTRY", "direction": "LONG", "risk_pct": 2,
             "rationale": "Turkey is energy importer + Bosphorus proximity (volatile, carry cost)",
             "entry": {"metric": "rsi.USDTRY", "op": "<", "value": 70}},
            {"symbol": "AUDJPY", "direction": "SHORT", "risk_pct": None,
             "rationale": "Both affected, but JPY safe-haven bid dominates",
             "severe_only": True,
             "entry": None},
        ],
        "entry_variants": {
            "default": [
                {"all": [
                    {"metric": "gdelt.chokepoint_score", "op": ">", "value": 0.8},
                    {"metric": "oil.intraday_spike_pct", "op": ">", "value": 3},
                ]},
            ],
        },
        "position_sizing": {
            "max_total_risk_pct": 10,
            "per_instrument_risk_pct": {"USDNOK": 3, "USDCAD": 3, "USDINR": 2, "USDTRY": 2},
            "stop": "2.0x ATR(14) from entry",
            "take_profit": "3.0x ATR(14) from entry",
        },
        "exit_rules": [
            "Oil reversal: if crude drops >3% from event peak -> reduce 50%",
            "Resolution signal: if strait reopens / attacks stop -> close within 4h",
            "Time stop: 10 trading days",
            "Carry consideration: USDTRY short has high negative swap - limit hold time",
        ],
    },
    {
        "id": "FX-4",
        "name": "Taiwan Tension Hedge",
        "description": ("Risk-off trade during Taiwan Strait military tension. JPY and CHF "
                        "appreciate as safe havens; Asia-Pacific currencies weaken."),
        "trigger": "Cross-strait military tension",
        "avg_duration_days": [1, 5],
        "expected_frequency": "0-2 /year",
        "instruments": [
            {"symbol": "AUDJPY", "direction": "SHORT", "risk_pct": 3,
             "rationale": "AUD weakens (risk-off), JPY strengthens (safe haven) - primary trade",
             "stop_pips": 150, "take_profit_pips": 300,
             "entry": None},
            {"symbol": "CHFJPY", "direction": "LONG", "risk_pct": 2,
             "rationale": "Both safe havens, but CHF outperforms on European distance from conflict",
             "stop_pips": 100, "take_profit_pips": 200,
             "entry": None},
            {"symbol": "USDJPY", "direction": "SHORT", "risk_pct": 1,
             "rationale": "JPY safe-haven bid dominates - smallest size (already correlated)",
             "stop_pips": 100, "take_profit_pips": 200,
             "entry": None},
        ],
        "entry_variants": {
            "default": [
                {"majority": {"min_required": 2, "conditions": [
                    {"metric": "gdelt.taiwan_military_score", "op": ">", "value": 0.85},
                    {"metric": "vix.level", "op": ">", "value": 25},
                    {"metric": "usdjpy.dropping", "op": "==", "value": True},
                    {"metric": "gold.intraday_change_pct", "op": ">", "value": 1},
                ]}},
            ],
        },
        "position_sizing": {
            "max_total_risk_pct": 6,
            "per_instrument_risk_pct": {"AUDJPY": 3, "CHFJPY": 2, "USDJPY": 1},
            "note": "EXTREME CAUTION - only trade on HIGH-CONVICTION signals",
        },
        "exit_rules": [
            "De-escalation: close 50% immediately on confirmed de-escalation signal",
            "False alarm: if VIX drops below 20 within 48h -> close all",
            "Time stop: 5 trading days (unless active military operations continue)",
            "Profit lock: trailing stop at 1.5x ATR after 150 pips profit",
        ],
    },
    {
        "id": "FX-5",
        "name": "Mining Country Shock",
        "description": ("Trade FX pairs when major mining countries experience domestic "
                        "disruption (strikes, power crisis, political instability)."),
        "trigger": "Mine closure / political instability",
        "avg_duration_days": [3, 14],
        "expected_frequency": "1-3 /quarter",
        "scenarios": [
            {"id": "ZA_POWER_STRIKE", "scenario": "S.Africa power/strike",
             "symbol": "USDZAR", "direction": "LONG",
             "trigger": "Eskom load-shedding, mining strikes"},
            {"id": "AU_MINE_DISRUPTION", "scenario": "Australia mine disruption",
             "symbol": "AUDUSD", "direction": "SHORT_THEN_LONG",
             "trigger": "Cyclone, flooding, environmental halt (initially SHORT, then LONG as price spike benefits)"},
            {"id": "CL_SOCIAL_UNREST", "scenario": "Chile social unrest",
             "symbol": "COPPER", "direction": "LONG",
             "trigger": "Political instability, water restrictions"},
            {"id": "PE_POLITICAL_CRISIS", "scenario": "Peru political crisis",
             "symbol": "AUDUSD", "direction": "LONG",
             "trigger": "President impeachment, mining protests"},
        ],
        "instruments": [],
        "entry_variants": {
            "default": [
                {"all": [
                    {"metric": "gdelt.country_disruption_score", "op": ">", "value": 0.7},
                    {"metric": "commodity.responding", "op": "==", "value": True},
                    {"metric": "finbert.country_news", "op": "<", "value": -0.3},
                ]},
                {"all": [{"metric": "technical.pair_confirmation", "op": "==", "value": True}]},
            ],
        },
        "position_sizing": {
            "max_per_pair_risk_pct": 3,
            "stop": "2.5x ATR(14) - wider for exotic pairs (ZAR volatility)",
            "take_profit": "4.0x ATR(14)",
        },
        "exit_rules": [
            "Per-event: max 3% of equity per pair",
            "Stop: 2.5x ATR(14), TP 4.0x ATR(14)",
        ],
    },
    {
        "id": "FX-6",
        "name": "Agricultural Crisis",
        "description": ("Trade currencies affected by agricultural supply disruptions "
                        "(wheat, fertilizer, food security)."),
        "trigger": "Wheat/food supply disruption",
        "avg_duration_days": [5, 21],
        "expected_frequency": "1-2 /quarter",
        "instruments": [
            {"symbol": "USDTRY", "direction": "LONG", "risk_pct": 2,
             "rationale": "Turkey wheat import dependency + inflation",
             "entry": {"metric": "rsi.USDTRY", "op": "<", "value": 75}},
            {"symbol": "AUDUSD", "direction": "LONG", "risk_pct": 3,
             "rationale": "Australia wheat exporter benefits",
             "entry": {"metric": "rsi.AUDUSD", "op": "<", "value": 50}},
        ],
        "entry_variants": {
            "default": [
                {"any": [
                    {"metric": "black_sea.grain_disruption", "op": "==", "value": True},
                    {"metric": "food.crisis_escalation", "op": "==", "value": True},
                ]},
                {"all": [{"metric": "wheat.above_52wk_high", "op": "==", "value": True}]},
            ],
        },
        "position_sizing": {
            "max_total_risk_pct": 5,
            "per_instrument_risk_pct": {"USDTRY": 2, "AUDUSD": 3},
            "note": "USDTRY high volatility + negative swap on short",
            "stop": "2.0x ATR(14)",
            "take_profit": "3.0x ATR(14)",
        },
        "exit_rules": [
            "Stop: 2.0x ATR(14), TP 3.0x ATR(14)",
            "Time stop: aligned with agricultural crisis duration (5-21 days)",
        ],
    },
]


# --------------------------------------------------------------------------
# Appendix C: event response playbooks (encoded literals from C.1-C.7)
# --------------------------------------------------------------------------
EVENT_RESPONSES = [
    {
        "id": "C.1",
        "name": "China Export Ban Response",
        "scenario": ("China announces export restrictions on one or more critical minerals "
                     "(gallium, germanium, antimony, rare earths, graphite, magnesium, polysilicon)."),
        "event_signature": {
            "keywords": ["export ban", "export restriction", "export control",
                         "gallium", "germanium", "antimony", "rare earth", "graphite",
                         "magnesium", "polysilicon", "china export"],
            "min_gdelt_score": 0.8,
            "sources_required": 2,
            "verification_sources": ["Reuters", "Bloomberg", "Xinhua"],
        },
        "immediate_actions": [
            {"step": "Verify news from 2+ sources (Reuters, Bloomberg, Xinhua)", "priority": "P0"},
            {"step": "Identify which minerals affected", "priority": "P0"},
            {"step": "Check current portfolio exposure to China Minerals group", "priority": "P0"},
            {"step": "If under sector cap: execute FX-2 (China Export Ban) strategy", "priority": "P0"},
            {"step": "Queue equity/ETF signals for affected minerals", "priority": "P1"},
        ],
        "trade_matrix": [
            {"trigger": "Gallium/Germanium", "primary": {"action": "SHORT", "symbol": "USDCNH"},
             "secondary": {"action": "LONG", "symbol": "REMX.US"},
             "tertiary": {"action": "SHORT", "symbol": "SOXX.US"}},
            {"trigger": "Rare Earths", "primary": {"action": "SHORT", "symbol": "USDCNH"},
             "secondary": {"action": "LONG", "symbol": "MP.US"},
             "tertiary": {"action": "LONG", "symbol": "REMX.US"}},
            {"trigger": "Antimony", "primary": {"action": "SHORT", "symbol": "USDCNH"},
             "secondary": {"action": "LONG", "symbol": "REMX.US"}, "tertiary": None},
            {"trigger": "Graphite", "primary": {"action": "SHORT", "symbol": "USDCNH"},
             "secondary": {"action": "LONG", "symbol": "AUDUSD"}, "tertiary": None},
            {"trigger": "Magnesium", "primary": {"action": "SHORT", "symbol": "USDCNH"},
             "secondary": None, "tertiary": None},
            {"trigger": "Polysilicon", "primary": {"action": "SHORT", "symbol": "USDCNH"},
             "secondary": {"action": "LONG", "symbol": "TAN.US"},
             "tertiary": {"action": "LONG", "symbol": "ENPH.US"}},
            {"trigger": "ALL (nuclear option)", "primary": {"action": "SHORT", "symbol": "USDCNH", "note": "max"},
             "secondary": {"action": "LONG", "symbol": "AUDUSD"},
             "tertiary": {"action": "LONG", "symbol": None, "note": "all alternative suppliers"}},
        ],
        "position_limits": {
            "max_china_minerals_group_pct": 15,
            "max_single_fx_pct": 3,
            "max_single_equity_pct": 4,
            "max_total_margin_pct": 50,
            "note": "Reduce other positions if needed to stay within 50% total margin",
        },
        "de_escalation_criteria": [
            "China announces exemptions -> reduce 50% immediately",
            "72h with no additional escalation -> start scaling out",
            "Full reversal announced -> close all event positions within 4h",
        ],
        "linked_inefficiency_ids": [2, 3, 4, 6, 8, 11, 12, 40],
        "linked_fx_strategy_ids": ["FX-2"],
    },
    {
        "id": "C.2",
        "name": "Strait Closure Response",
        "scenario": ("Major maritime chokepoint closure or severe disruption (Hormuz, "
                     "Suez/Red Sea, Malacca, Taiwan Strait, Bosphorus)."),
        "event_signature": {
            "keywords": ["strait closure", "hormuz", "suez", "red sea", "malacca",
                         "taiwan strait", "bosphorus", "chokepoint", "canal closure",
                         "ever given", "houthi"],
            "min_gdelt_score": 0.8,
        },
        "severity_tiers": [
            {"tier": "T1", "description": "Partial disruption, alternative routes available",
             "example": "Houthi attacks (ships reroute)",
             "response_level": "Moderate - gradual positioning"},
            {"tier": "T2", "description": "Full closure, short duration expected (<2 weeks)",
             "example": "Ever Given grounding",
             "response_level": "Aggressive - immediate positions"},
            {"tier": "T3", "description": "Full closure, extended/indefinite",
             "example": "Iran closes Hormuz",
             "response_level": "Maximum - activate all chokepoint trades"},
        ],
        "strait_actions": {
            "Hormuz": [
                {"priority": "P0", "action": "LONG", "symbol": "XTIUSD", "size_pct": 5,
                 "note": "crude oil, 21% global oil"},
                {"priority": "P0", "action": "SHORT", "symbol": "USDNOK", "size_pct": 3},
                {"priority": "P0", "action": "SHORT", "symbol": "USDCAD", "size_pct": 3},
                {"priority": "P1", "action": "LONG", "symbol": "STNG.US", "size_pct": 3,
                 "note": "or FRO.US"},
                {"priority": "P1", "action": "LONG", "symbol": "XAUUSD", "size_pct": 3,
                 "note": "gold safe haven"},
                {"priority": "P2", "action": "LONG", "symbol": "USDINR", "size_pct": 2},
                {"priority": "P2", "action": "LONG", "symbol": "USDTRY", "size_pct": 2},
            ],
            "Suez_Red_Sea": [
                {"priority": "P0", "action": "LONG", "symbol": "XTIUSD", "size_pct": 3},
                {"priority": "P0", "action": "LONG", "symbol": "ZIM.US", "size_pct": 3,
                 "note": "shipping rates surge"},
                {"priority": "P1", "action": "SHORT", "symbol": "USDNOK", "size_pct": 3},
                {"priority": "P1", "action": "LONG", "symbol": "STNG.US", "size_pct": 3,
                 "note": "tanker stocks (STNG/FRO)"},
                {"priority": "P2", "action": "LONG", "symbol": "WHEAT", "size_pct": 3,
                 "note": "if grain transit affected"},
            ],
            "Taiwan_Strait": [
                {"priority": "P0", "action": "ACTIVATE_FX", "symbol": "FX-4", "size_pct": 6,
                 "note": "Taiwan Tension Hedge"},
                {"priority": "P0", "action": "SHORT", "symbol": "TSM.US", "size_pct": 4},
                {"priority": "P1", "action": "SHORT", "symbol": "SOXX.US", "size_pct": 3},
                {"priority": "P1", "action": "LONG", "symbol": "XAUUSD", "size_pct": 4},
                {"priority": "P1", "action": "LONG", "symbol": "LMT.US", "size_pct": 3,
                 "note": "defense"},
                {"priority": "P1", "action": "LONG", "symbol": "RTX.US", "size_pct": 3,
                 "note": "defense"},
                {"priority": "P2", "action": "EVALUATE_CIRCUIT_BREAKER", "symbol": None,
                 "note": "may exceed drawdown limits"},
            ],
        },
        "monitoring": {
            "every_30_minutes": [
                "Check MarineTraffic for vessel rerouting data",
                "Monitor GDELT for escalation/de-escalation signals",
                "Update crude oil / shipping rate proxies",
                "Check portfolio correlation (chokepoint trades cluster)",
                "Review margin utilization (volatile markets = wider swings)",
            ],
            "every_4_hours": [
                "FinBERT sentiment on chokepoint news",
                "Update P&L and drawdown",
                "Reassess position sizes",
            ],
        },
        "position_limits": {
            "max_oil_position_pct": 5,
            "max_fx_position_pct": 3,
            "max_equity_position_pct": 4,
            "max_fx_strategy_total_pct": 6,
        },
        "de_escalation_criteria": [
            "Strait reopens / attacks stop -> close within 4h",
            "Vessel traffic resumed on original route -> scale out chokepoint trades",
            "Crude drops >3% from event peak -> reduce 50%",
        ],
        "linked_inefficiency_ids": [18, 19, 29],
        "linked_fx_strategy_ids": ["FX-3", "FX-4"],
    },
    {
        "id": "C.3",
        "name": "Undersea Cable Cut Response",
        "scenario": ("Major undersea telecommunications cable severed (physical damage, "
                     "sabotage, or earthquake)."),
        "event_signature": {
            "keywords": ["undersea cable", "submarine cable", "cable cut", "cable severed",
                         "internet disruption", "cable repair"],
            "min_gdelt_score": 0.7,
        },
        "severity_tiers": [
            {"tier": "Low", "criteria": "Single cable, redundant capacity exists",
             "market_impact": "Minimal - no trade"},
            {"tier": "Medium", "criteria": "Multiple cables on same route, some latency impact",
             "market_impact": "Moderate - equity trades"},
            {"tier": "High", "criteria": "Critical route severed (Asia-Europe or Trans-Atlantic), major internet disruption",
             "market_impact": "Significant - multi-instrument"},
        ],
        "trade_matrix": [
            {"trigger": "Low", "primary": {"action": "MONITOR", "symbol": None},
             "secondary": None, "fx": None},
            {"trigger": "Medium", "primary": {"action": "LONG", "symbol": "TE.US", "size_pct": 3},
             "secondary": {"action": "LONG", "symbol": "NOK.US", "size_pct": 3}, "fx": None},
            {"trigger": "High",
             "primary": {"action": "LONG", "symbol": "TE.US", "size_pct": 3},
             "secondary": {"action": "LONG", "symbol": "NOK.US", "size_pct": 3,
                           "note": "plus SHORT affected region tech stocks"},
             "fx": {"action": "LONG", "note": "safe-haven FX (CHF, JPY)"}},
        ],
        "timeline": [
            {"window": "0-1h", "action": "Assess severity from news, submarine cable map"},
            {"window": "1-4h", "action": "Execute primary trades if medium+ severity"},
            {"window": "4-24h", "action": "Execute secondary trades if impact confirmed"},
            {"window": "1-7d", "action": "Hold positions while repair ship en route"},
            {"window": "7-30d", "action": "Monitor repair progress, scale out as capacity restored"},
        ],
        "position_limits": {
            "max_single_equity_pct": 3,
        },
        "de_escalation_criteria": [
            "Repair capacity restored -> scale out as capacity returns (7-30d window)",
            "Only single cable with redundancy -> no trade taken",
        ],
        "linked_inefficiency_ids": [27],
        "linked_fx_strategy_ids": [],
    },
    {
        "id": "C.4",
        "name": "Mine Disruption Response",
        "scenario": "Major mining operation disrupted (accident, strike, weather, political).",
        "event_signature": {
            "keywords": ["mine accident", "mine closure", "mine strike", "mining disruption",
                         "tailings", "nationalization", "mine flood", "pit collapse"],
            "min_gdelt_score": 0.7,
        },
        "assessment_factors": [
            {"factor": "Mine size", "low": "<5% of global supply", "medium": "5-15%",
             "high": ">15%"},
            {"factor": "Duration", "low": "<1 week", "medium": "1-4 weeks", "high": ">1 month"},
            {"factor": "Alternatives", "low": "Many alternative sources",
             "medium": "Some alternatives", "high": "Few/no alternatives"},
            {"factor": "Stockpiles", "low": ">6 months industry", "medium": "3-6 months",
             "high": "<3 months"},
        ],
        "trade_matrix": [
            {"trigger": "Copper/Chile", "primary": {"action": "LONG", "symbol": "COPPER", "size_pct": 4},
             "secondary": {"action": "LONG", "symbol": "FCX.US", "size_pct": 3}},
            {"trigger": "Copper/DRC", "primary": {"action": "LONG", "symbol": "COPPER", "size_pct": 4}},
            {"trigger": "Cobalt/DRC", "primary": {"action": "LONG", "symbol": "COPPER", "size_pct": 3,
                                                   "note": "proxy"}},
            {"trigger": "Bauxite/Guinea", "primary": {"action": "LONG", "symbol": "ALUMINIUM", "size_pct": 3},
             "secondary": {"action": "LONG", "symbol": "AA.US", "size_pct": 3}},
            {"trigger": "Manganese/S.Africa", "primary": {"action": "LONG", "symbol": "USDZAR", "size_pct": 3}},
            {"trigger": "Uranium/Kazakhstan", "primary": {"action": "LONG", "symbol": "CCJ.US", "size_pct": 3},
             "secondary": {"action": "LONG", "symbol": "URA.US", "size_pct": 3}},
            {"trigger": "Rare Earths/China", "primary": {"action": "SHORT", "symbol": "USDCNH", "size_pct": 3},
             "secondary": {"action": "LONG", "symbol": "MP.US", "size_pct": 3}},
            {"trigger": "Platinum/S.Africa", "primary": {"action": "LONG", "symbol": "USDZAR", "size_pct": 3}},
        ],
        "position_limits": {
            "max_single_commodity_pct": 4,
            "max_single_equity_pct": 3,
        },
        "de_escalation_criteria": [
            "Mine restart confirmed -> scale out within days",
            "Alternative supply absorbed price move -> exit on TP/time stop",
        ],
        "linked_inefficiency_ids": [5, 8, 9, 10, 25, 38],
        "linked_fx_strategy_ids": ["FX-5"],
    },
    {
        "id": "C.5",
        "name": "Weather Event Response",
        "scenario": "Severe weather affecting agricultural or mining production.",
        "event_signature": {
            "keywords": ["el niño", "el nino", "la niña", "la nina", "drought", "cyclone",
                         "hurricane", "flood", "heatwave", "crop failure"],
            "min_gdelt_score": 0.7,
        },
        "trade_matrix": [
            {"trigger": "El Niño declared", "affected": ["Fishmeal (Peru)", "Cocoa (W.Africa)"],
             "primary": {"action": "LONG", "symbol": "COCOA"},
             "secondary": {"action": "LONG", "symbol": "MOWI.US"}, "timeframe": "2-6 months"},
            {"trigger": "La Niña declared", "affected": ["Wheat (Australia)", "Copper (Chile dry)"],
             "primary": {"action": "LONG", "symbol": "WHEAT"},
             "secondary": {"action": "LONG", "symbol": "COPPER"}, "timeframe": "2-6 months"},
            {"trigger": "W.Africa drought", "affected": ["Cocoa", "Coffee"],
             "primary": {"action": "LONG", "symbol": "COCOA"}, "timeframe": "1-3 months"},
            {"trigger": "Thailand flood", "affected": ["Natural rubber", "Rice"],
             "primary": {"action": "LONG", "symbol": "USDJPY"}, "timeframe": "1-4 weeks"},
            {"trigger": "Australian cyclone", "affected": ["Iron ore", "Bauxite"],
             "primary": {"action": "SHORT", "symbol": "AUDUSD", "note": "short-term"},
             "timeframe": "1-2 weeks"},
            {"trigger": "US heatwave", "affected": ["Corn", "Soybeans", "Power grid"],
             "primary": {"action": "LONG", "symbol": "SOYBEAN"},
             "secondary": {"action": "LONG", "symbol": "ETN.US"}, "timeframe": "2-6 weeks"},
        ],
        "decision_tree": [
            "Severity < moderate -> monitor only",
            "Severity = moderate AND crop/commodity affected AND inventory low (<3 months) -> enter immediately (2% risk)",
            "Severity = moderate AND inventory adequate -> wait for price confirmation",
            "Severity = moderate AND duration forecast < 2 weeks -> likely no trade",
            "Severity = moderate AND duration forecast > 2 weeks -> enter on confirmation",
            "Severity = severe/extreme -> enter immediately (3% risk) + wider stops (3x ATR)",
        ],
        "position_limits": {
            "moderate_risk_pct": 2,
            "severe_risk_pct": 3,
            "severe_stop_atr_mult": 3,
        },
        "de_escalation_criteria": [
            "Weather event passes without crop damage -> cancel pending entries",
            "Crop impact confirmed smaller than forecast -> exit on TP/time stop",
        ],
        "linked_inefficiency_ids": [15, 20, 21, 22, 23, 24, 25],
        "linked_fx_strategy_ids": ["FX-6"],
    },
    {
        "id": "C.6",
        "name": "Political Instability Response",
        "scenario": "Coup, revolution, or severe political crisis in a key commodity-producing nation.",
        "event_signature": {
            "keywords": ["coup", "revolution", "impeachment", "political crisis", "unrest",
                         "military takeover", "government collapse", "civil war"],
            "min_gdelt_score": 0.7,
        },
        "trade_matrix": [
            {"trigger": "DRC", "commodities": ["Cobalt", "Copper"],
             "primary": {"action": "LONG", "symbol": "COPPER"}, "risk_level": "High (conflict zone)"},
            {"trigger": "Guinea", "commodities": ["Bauxite"],
             "primary": {"action": "LONG", "symbol": "ALUMINIUM"}, "risk_level": "High"},
            {"trigger": "Peru", "commodities": ["Copper", "Fishmeal"],
             "primary": {"action": "LONG", "symbol": "COPPER"}, "risk_level": "Medium"},
            {"trigger": "Chile", "commodities": ["Copper"],
             "primary": {"action": "LONG", "symbol": "COPPER"},
             "secondary": {"action": "LONG", "symbol": "FCX.US"},
             "fx": {"action": "SHORT", "symbol": "AUDUSD", "note": "briefly"}, "risk_level": "Medium"},
            {"trigger": "S.Africa", "commodities": ["Manganese", "PGMs"],
             "fx": {"action": "LONG", "symbol": "USDZAR"}, "risk_level": "Medium"},
            {"trigger": "Myanmar", "commodities": ["Antimony", "Rare Earths"],
             "primary": {"action": "SHORT", "symbol": "USDCNH"}, "risk_level": "High"},
            {"trigger": "Gabon", "commodities": ["Manganese"], "risk_level": "Low (small impact)"},
            {"trigger": "Kazakhstan", "commodities": ["Uranium"],
             "primary": {"action": "LONG", "symbol": "CCJ.US"}, "risk_level": "Medium"},
            {"trigger": "Panama", "commodities": ["Canal transit"],
             "primary": {"action": "LONG", "symbol": "ZIM.US"}, "risk_level": "Low"},
        ],
        "timeline": [
            {"window": "Hour 0-4", "action": "ASSESS - verify event, estimate severity"},
            {"window": "Hour 4-24", "action": "POSITION - enter primary trades if severity > medium"},
            {"window": "Day 1-7", "action": "MONITOR - track developments, adjust positions"},
            {"window": "Day 7-30", "action": "REVIEW - scale out if situation stabilizing"},
            {"window": "Day 30+", "action": "REBASE - adjust supply concentration estimates"},
        ],
        "position_limits": {
            "max_single_position_pct": 4,
            "high_risk_countries_entry_required_severity": "medium",
        },
        "de_escalation_criteria": [
            "Situation stabilizing (Day 7-30 window) -> scale out",
            "New government confirms mining/export continuity -> close event positions",
        ],
        "linked_inefficiency_ids": [5, 8, 9, 10, 18, 25, 38],
        "linked_fx_strategy_ids": ["FX-5"],
    },
    {
        "id": "C.7",
        "name": "Regulatory Change Response",
        "scenario": ("Major regulatory change affecting supply chain (export controls, "
                     "environmental regulations, trade agreements, sanctions)."),
        "event_signature": {
            "keywords": ["export control", "sanction", "tariff", "regulation", "trade agreement",
                         "subsidy", "cbam", "forced labor", "deforestation", "kigali"],
            "min_gdelt_score": 0.6,
        },
        "trade_matrix": [
            {"trigger": "Export ban (immediate)", "speed": "FAST",
             "action": "Execute event trade within 2h", "example": "China Ga/Ge ban"},
            {"trigger": "Sanction expansion", "speed": "FAST",
             "action": "Adjust exposure within 4h", "example": "Russia SWIFT"},
            {"trigger": "Environmental regulation", "speed": "SLOW",
             "action": "Gradual positioning over 1-4 weeks", "example": "EU deforestation law"},
            {"trigger": "Trade agreement change", "speed": "SLOW",
             "action": "Research and position over 2-4 weeks", "example": "USMCA modification"},
            {"trigger": "Subsidy/incentive", "speed": "SLOW",
             "action": "Gradual positioning over 1-4 weeks", "example": "US CHIPS Act, IRA"},
        ],
        "watchlist": [
            {"regulation": "China export controls (minerals)", "status": "Active, expanding",
             "inefficiency_ids": [2, 3, 4, 6, 8, 11, 12, 40], "frequency": "Daily"},
            {"regulation": "EU CBAM (Carbon Border)", "status": "Implementing",
             "inefficiency_ids": [25, 38, 40], "frequency": "Weekly"},
            {"regulation": "US CHIPS Act", "status": "Implementing",
             "inefficiency_ids": [28, 29, 30, 31], "frequency": "Weekly"},
            {"regulation": "US IRA (Inflation Reduction Act)", "status": "Active",
             "inefficiency_ids": [10, 38, 40], "frequency": "Weekly"},
            {"regulation": "EU Deforestation Regulation", "status": "Implementing",
             "inefficiency_ids": [21, 23, 24], "frequency": "Monthly"},
            {"regulation": "Kigali Amendment (HFCs)", "status": "Active",
             "inefficiency_ids": [16], "frequency": "Quarterly"},
            {"regulation": "Basel III endgame (banking)", "status": "Proposed",
             "inefficiency_ids": [32], "frequency": "Monthly"},
            {"regulation": "IMO 2030 shipping rules", "status": "Proposed",
             "inefficiency_ids": [17, 18, 19], "frequency": "Quarterly"},
        ],
        "position_limits": {
            "fast_events_max_risk_pct": 3,
            "slow_events_position_window_weeks": 4,
        },
        "de_escalation_criteria": [
            "Regulation watered down or delayed -> unwind gradual positions",
            "Exemptions granted for affected commodities -> reduce 50% immediately",
        ],
        "linked_inefficiency_ids": [2, 3, 4, 6, 8, 10, 11, 12, 16, 17, 18, 19, 21, 23, 24,
                                    25, 28, 29, 30, 31, 32, 38, 40],
        "linked_fx_strategy_ids": ["FX-2"],
    },
]


# --------------------------------------------------------------------------
# GDELT keyword theming (per-inefficiency, derived from the trade cards)
# --------------------------------------------------------------------------
# Deterministic alias map: commodity-specific phrases the layer-1 scanner
# should match for each inefficiency's news events. Name tokens are appended
# automatically; shared disruption shock-words are appended by the scanner.
GDELT_ALIASES: dict[int, list[str]] = {
    1: ["helium", "blm plant"],
    2: ["antimony"],
    3: ["gallium", "germanium", "ga/ge"],
    4: ["graphite"],
    5: ["manganese", "richards bay"],
    6: ["fluorspar", "fluoride chemical"],
    7: ["phosphate", "dap fertilizer", "fertilizer"],
    8: ["rare earth", "rare earths"],
    9: ["cobalt", "lobito"],
    10: ["uranium", "enrichment", "tenex", "rosatom"],
    11: ["titanium", "titanium sponge"],
    12: ["magnesium"],
    13: ["potash"],
    14: ["seed genetics", "gmo", "monsanto", "corteva"],
    15: ["pollination", "colony collapse", "honeybee", "almond"],
    16: ["refrigerant", "hfc", "kigali"],
    17: ["container shortage", "port congestion", "scfi"],
    18: ["panama canal"],
    19: ["red sea", "suez", "hormuz", "houthi"],
    20: ["vanilla"],
    21: ["palm oil"],
    22: ["fishmeal", "el niño", "el nino", "anchovy"],
    23: ["cocoa", "ivory coast", "swollen shoot"],
    24: ["natural rubber", "rubber"],
    25: ["bauxite", "alumina", "aluminium"],
    26: ["wheat", "black sea", "bosphorus", "grain corridor"],
    27: ["undersea cable", "submarine cable", "cable cut"],
    28: ["asml", "euv", "lithography"],
    29: ["tsmc", "taiwan semiconductor", "advanced chips"],
    30: ["neon gas", "neon"],
    31: ["ultra-pure water", "ultrapure water"],
    32: ["swift", "swift disconnection"],
    33: ["gps", "gnss", "spoofing", "jamming", "galileo"],
    34: ["power transformer", "transformer shortage", "grid emergency"],
    35: ["hvdc", "hvdc converter"],
    36: ["labor shortage", "skilled labor", "manufacturing pmi"],
    37: ["cloud outage", "aws", "azure", "cloud provider"],
    38: ["copper", "lme copper"],
    39: ["sand mining", "construction sand", "aggregate"],
    40: ["polysilicon", "xinjiang", "uyghur"],
}

SHARED_SHOCK_WORDS = [
    "export ban", "restriction", "sanction", "disruption", "shutdown",
    "mine strike", "coup", "closure", "earthquake", "flood", "halt",
]


def build_gdelt_keywords(cards: list[dict]) -> dict[int, list[str]]:
    keywords: dict[int, list[str]] = {}
    for card in cards:
        iid = card["id"]
        seen: list[str] = []
        for kw in GDELT_ALIASES.get(iid, []):
            if kw not in seen:
                seen.append(kw)
        for token in card["name"].replace("/", " ").lower().split():
            token = token.strip("()")
            if len(token) >= 3 and token not in ("and",) and token not in seen:
                seen.append(token)
        keywords[iid] = seen
    return keywords


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def validate(cards, fx, events, keywords) -> None:
    problems: list[str] = []

    known = set()
    inst_path = CONFIG / "instruments.yaml"
    with open(inst_path, "r", encoding="utf-8") as f:
        for symbols in yaml.safe_load(f).values():
            known.update(symbols)
    known.update(INSTRUMENT_EXTENSIONS)

    ids = [c["id"] for c in cards]
    if ids != list(range(1, 41)):
        problems.append(f"trade cards ids are not 1..40 in order: {ids}")
    for c in cards:
        for sym in c["primary_instruments"] + c["proxy_instruments"]:
            if sym not in known:
                problems.append(f"card #{c['id']}: unknown instrument {sym}")
        if c["status"] not in ("NOT_TRADEABLE", "INDICATOR_ONLY"):
            if not c["primary_instruments"]:
                problems.append(f"card #{c['id']}: no primary instruments but tradeable")
            if not c["entry_rules"]["raw"]:
                problems.append(f"card #{c['id']}: missing entry rules")

    fx_ids = [s["id"] for s in fx]
    if fx_ids != [f"FX-{i}" for i in range(1, 7)]:
        problems.append(f"fx strategy ids wrong: {fx_ids}")
    for s in fx:
        syms = [i["symbol"] for i in s.get("instruments", [])] + \
               [i["symbol"] for i in s.get("scenarios", [])]
        if not syms:
            problems.append(f"{s['id']}: no instruments")
        for sym in syms:
            if sym not in known:
                problems.append(f"{s['id']}: unknown instrument {sym}")
        for vid, groups in s["entry_variants"].items():
            for g in groups:
                for kind in ("all", "any"):
                    for cond in g.get(kind, []):
                        if set(cond) - {"metric", "op", "value"}:
                            problems.append(f"{s['id']}/{vid}: bad condition {cond}")
                if "majority" in g:
                    if g["majority"]["min_required"] > len(g["majority"]["conditions"]):
                        problems.append(f"{s['id']}/{vid}: majority min_required too large")

    ev_ids = [e["id"] for e in events]
    if ev_ids != [f"C.{i}" for i in range(1, 8)]:
        problems.append(f"event response ids wrong: {ev_ids}")
    for e in events:
        sig = e["event_signature"]
        if not sig["keywords"] or sig["min_gdelt_score"] <= 0:
            problems.append(f"{e['id']}: bad event signature")
        matrix = e.get("trade_matrix")
        if not matrix and not e.get("strait_actions"):
            problems.append(f"{e['id']}: empty trade matrix")
        if not e["de_escalation_criteria"]:
            problems.append(f"{e['id']}: no de-escalation criteria")
        rows = list(matrix or [])
        for strait in e.get("strait_actions", {}).values():
            rows.extend(strait)
        for row in rows:
            if not isinstance(row, dict):
                continue
            for leg in ("primary", "secondary", "tertiary", "fx"):
                act = row.get(leg)
                if isinstance(act, dict) and act.get("symbol") and act["symbol"] not in known:
                    problems.append(f"{e['id']}: unknown matrix symbol {act['symbol']}")

    if set(keywords) != set(range(1, 41)):
        problems.append("gdelt keywords do not cover ids 1..40")
    for iid, kws in keywords.items():
        if not kws:
            problems.append(f"gdelt keywords for #{iid} empty")

    if problems:
        for p in problems:
            print(f"VALIDATION ERROR: {p}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    cards = parse_trade_cards()
    keywords = build_gdelt_keywords(cards)
    validate(cards, FX_STRATEGIES, EVENT_RESPONSES, keywords)

    header = ("# Generated by scripts/generate_playbook_config.py from "
              "docs/sci_playbook_v1.md (SCI Playbook v1.0). Do not hand-edit.\n")

    with open(CONFIG / "trade_cards.yaml", "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "# Appendix A: 40 inefficiency trade cards. Join key: id "
                         "(inefficiencies.yaml).\n")
        yaml.safe_dump(cards, f, sort_keys=False, allow_unicode=True, width=110)

    with open(CONFIG / "fx_strategies.yaml", "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "# Appendix B: forex strategy playbook (FX-1..FX-6).\n")
        yaml.safe_dump(FX_STRATEGIES, f, sort_keys=False, allow_unicode=True, width=110)

    with open(CONFIG / "event_responses.yaml", "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "# Appendix C: event response playbooks (C.1..C.7).\n")
        yaml.safe_dump(EVENT_RESPONSES, f, sort_keys=False, allow_unicode=True, width=110)

    with open(CONFIG / "gdelt_keywords.yaml", "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "# Per-inefficiency GDELT keyword theming derived from the "
                         "trade cards.\n# Scanner appends shared shock-words at match time.\n")
        yaml.safe_dump(keywords, f, sort_keys=True, allow_unicode=True)

    print(f"trade_cards.yaml: {len(cards)} cards")
    print(f"fx_strategies.yaml: {len(FX_STRATEGIES)} strategies")
    print(f"event_responses.yaml: {len(EVENT_RESPONSES)} playbooks")
    print(f"gdelt_keywords.yaml: {len(keywords)} inefficiency keyword sets")


if __name__ == "__main__":
    main()
