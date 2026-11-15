"""Tests for the encoded playbook appendices (UGT-7).

Covers config/trade_cards.yaml (Appendix A), config/fx_strategies.yaml
(Appendix B), config/event_responses.yaml + signals/event_responses.py
(Appendix C) and the per-inefficiency GDELT keyword theming.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from newsetup.config import (load_event_responses, load_fx_strategies,
                              load_gdelt_keywords, load_instruments,
                              load_inefficiencies, load_trade_cards)
from newsetup.models import Event
from signals.event_responses import (EventResponseEngine, load_rules,
                                     match_event)
from signals.fx_strategies import evaluate_entry, get_strategy, load_strategies
from signals.layer1_scanner import Layer1Scanner


# ------------------------------------------------------------ Appendix A
class TestTradeCards:
    def test_40_cards_join_inefficiencies_by_id(self):
        cards = load_trade_cards()
        ineff_ids = {i.id for i in load_inefficiencies()}
        assert len(cards) == 40
        assert set(cards) == ineff_ids
        assert sorted(cards) == list(range(1, 41))

    def test_card_schema(self):
        cards = load_trade_cards()
        required = {"id", "name", "category", "status", "description",
                    "supply_concentration", "trigger_scenarios",
                    "primary_instruments", "proxy_instruments", "entry_rules",
                    "exit_rules", "invalidation_conditions",
                    "position_sizing", "correlations_note"}
        for cid, card in cards.items():
            missing = required - set(card)
            assert not missing, f"card #{cid} missing {missing}"
            assert card["entry_rules"]["raw"], f"card #{cid} entry rules empty"
            assert card["trigger_scenarios"], f"card #{cid} no trigger scenarios"

    def test_statuses_normalized(self):
        cards = load_trade_cards()
        allowed = {"ACTIVE", "MONITORING", "LOW_PRIORITY", "INDICATOR_ONLY",
                   "NOT_TRADEABLE"}
        for card in cards.values():
            assert card["status"] in allowed, card["status"]
        assert cards[20]["status"] == "NOT_TRADEABLE"       # Vanilla
        assert cards[36]["status"] == "INDICATOR_ONLY"       # Skilled labor
        tier1 = [c for c in cards.values() if c["status"] == "ACTIVE" and c["tier"] == 1]
        assert len(tier1) >= 6   # playbook marks 6+ Tier-1 opportunities

    def test_tradeable_cards_have_instruments_and_invalidation(self):
        cards = load_trade_cards()
        for cid, card in cards.items():
            if card["status"] in ("NOT_TRADEABLE", "INDICATOR_ONLY"):
                continue
            assert card["primary_instruments"], f"card #{cid} tradeable but no instruments"
            assert card["invalidation_conditions"], f"card #{cid} no invalidation"
            assert card["position_sizing"]["raw"], f"card #{cid} no sizing note"
            assert card["exit_rules"]["raw"] not in ("", "N/A"), f"card #{cid} no exits"

    def test_symbols_covered_by_instrument_map(self):
        known = set()
        for symbols in load_instruments().values():
            known.update(symbols)
        cards = load_trade_cards()
        for cid, card in cards.items():
            for sym in card["primary_instruments"] + card["proxy_instruments"]:
                assert sym in known, f"card #{cid}: {sym} not in instruments.yaml"

    def test_exit_rules_parsed(self):
        cards = load_trade_cards()
        helium = cards[1]
        assert helium["exit_rules"]["time_stop_days"] == 14
        assert any("2.5x ATR" in tp for tp in helium["exit_rules"]["take_profit"])
        ga = cards[3]
        assert ga["exit_rules"]["take_profit"] == ["250 pips / 8% REMX", "5%"]
        assert ga["position_sizing"]["sector_cap_pct"] == 15


# ------------------------------------------------------------ Appendix B
class TestFxStrategies:
    def test_6_strategies_loaded(self):
        strategies = load_strategies()
        assert [s.id for s in strategies] == [f"FX-{i}" for i in range(1, 7)]
        for s in strategies:
            assert s.exit_rules, f"{s.id} no exit rules"
            assert s.position_sizing, f"{s.id} no position sizing"
            assert s.entry_variants, f"{s.id} no entry variants"

    def test_fx1_basket_eligible(self):
        fx1 = get_strategy("FX-1")
        context = {
            "gdelt.supply_chain_disruption_index": 0.75,
            "dxy.below_200dma": True,
            "rsi.AUDUSD": 40, "rsi.USDCAD": 58, "rsi.USDNOK": 60,
        }
        result = evaluate_entry(fx1, context)
        assert result["eligible"], result["reasons"]
        assert {i.symbol for i in result["eligible_instruments"]} == \
            {"AUDUSD", "USDCAD", "USDNOK"}

    def test_fx1_rejected_when_dollar_strong(self):
        fx1 = get_strategy("FX-1")
        context = {
            "gdelt.supply_chain_disruption_index": 0.75,
            "dxy.below_200dma": False,             # dollar strengthening
            "rsi.AUDUSD": 40, "rsi.USDCAD": 58, "rsi.USDNOK": 60,
        }
        assert not evaluate_entry(fx1, context)["eligible"]

    def test_fx1_majority_needs_2_of_3(self):
        fx1 = get_strategy("FX-1")
        context = {
            "bcom.pct_above_200dma": 7,            # alt entry path
            "dxy.below_200dma": True,
            "rsi.AUDUSD": 40,                      # 1 of 3 RSI zones only
        }
        assert not evaluate_entry(fx1, context)["eligible"]

    def test_fx2_fast_variant(self):
        fx2 = get_strategy("FX-2")
        context = {
            "gdelt.china_mineral_export_ban_score": 0.9,
            "usdcnh.level": 7.25,
            "portfolio.china_minerals_open_positions": 0,
        }
        result = evaluate_entry(fx2, context)
        assert result["eligible"] and result["variant"] == "fast", result["reasons"]
        assert result["eligible_instruments"][0].symbol == "USDCNH"

    def test_fx2_confirmed_variant(self):
        fx2 = get_strategy("FX-2")
        context = {
            "finbert.china_export_news": -0.7,
            "macd.USDCNH.bearish_crossover": True,
        }
        result = evaluate_entry(fx2, context)
        assert result["eligible"] and result["variant"] == "confirmed"

    def test_fx3_severe_only_gates_audjpy(self):
        fx3 = get_strategy("FX-3")
        context = {"gdelt.chokepoint_score": 0.9, "oil.intraday_spike_pct": 4,
                   "rsi.USDNOK": 55, "rsi.USDCAD": 55, "rsi.USDINR": 60, "rsi.USDTRY": 65}
        normal = evaluate_entry(fx3, context)
        assert normal["eligible"]
        assert "AUDJPY" not in {i.symbol for i in normal["eligible_instruments"]}
        severe = evaluate_entry(fx3, context, severe_crisis=True)
        assert "AUDJPY" in {i.symbol for i in severe["eligible_instruments"]}

    def test_fx4_majority_min_2_of_4(self):
        fx4 = get_strategy("FX-4")
        one = {"gdelt.taiwan_military_score": 0.9}
        assert not evaluate_entry(fx4, one)["eligible"]
        two = {"gdelt.taiwan_military_score": 0.9, "vix.level": 30}
        assert evaluate_entry(fx4, two)["eligible"]

    def test_fx6_agricultural_crisis(self):
        fx6 = get_strategy("FX-6")
        context = {"black_sea.grain_disruption": True, "wheat.above_52wk_high": True,
                   "rsi.USDTRY": 70, "rsi.AUDUSD": 45}
        result = evaluate_entry(fx6, context)
        assert result["eligible"]
        assert {i.symbol for i in result["eligible_instruments"]} == {"USDTRY", "AUDUSD"}


# ------------------------------------------------------------ Appendix C
class TestEventResponses:
    def test_7_playbooks_loaded(self):
        rules = load_rules()
        assert [r.id for r in rules] == [f"C.{i}" for i in range(1, 8)]
        for rule in rules:
            assert rule.keywords, f"{rule.id} no signature keywords"
            assert rule.position_limits, f"{rule.id} no position limits"
            assert rule.de_escalation_criteria, f"{rule.id} no de-escalation"
            assert rule.trade_matrix or rule.strait_actions, f"{rule.id} no trades"

    def test_china_export_ban_end_to_end(self):
        engine = EventResponseEngine()
        event = Event(headline="China announces export ban on gallium and germanium",
                      themes=["export ban"], goldstein_score=-8.0, score=0.85)
        plan = engine.respond(event)
        assert plan is not None
        assert plan["playbook_id"] == "C.1"
        assert plan["position_limits"]["max_china_minerals_group_pct"] == 15
        assert plan["linked_fx_strategy_ids"] == ["FX-2"]
        rule = engine.rules[0]
        row = rule.matrix_row("Gallium/Germanium")
        assert row is not None
        assert row["primary"] == {"action": "SHORT", "symbol": "USDCNH"}
        assert row["secondary"]["symbol"] == "REMX.US"
        assert any("72h" in d for d in plan["de_escalation_criteria"])

    def test_strait_closure_severity_tiers(self):
        rules = {r.id: r for r in load_rules()}
        c2 = rules["C.2"]
        t1, t2, t3 = c2.tier("T1"), c2.tier("T2"), c2.tier("T3")
        assert t1 is not None and t1["response_level"].startswith("Moderate")
        assert t2 is not None and t2["response_level"].startswith("Aggressive")
        assert t3 is not None and t3["response_level"].startswith("Maximum")
        hormuz = c2.actions_for("Hormuz")
        assert hormuz and hormuz[0]["symbol"] == "XTIUSD" and hormuz[0]["size_pct"] == 5
        assert c2.tier("T9") is None

    def test_event_matching_prefers_most_keyword_hits(self):
        rules = load_rules()
        event = Event(headline="Iran closes Strait of Hormuz, oil tankers halt",
                      goldstein_score=-9.0, score=0.9)
        matched = match_event(event, rules)
        assert matched is not None and matched.id == "C.2"
        event = Event(headline="Copper mine strike in Chile after political unrest",
                      goldstein_score=-6.0, score=0.8)
        matched = match_event(event, rules)
        assert matched is not None and matched.id in ("C.4", "C.6")

    def test_benign_event_no_match(self):
        rules = load_rules()
        event = Event(headline="Central bank holds rates steady, markets calm",
                      goldstein_score=2.0, score=0.3)
        assert match_event(event, rules) is None

    def test_low_score_event_rejected(self):
        rules = load_rules()
        event = Event(headline="China announces export ban on rare earths",
                      goldstein_score=-2.0, score=0.4)   # below min_gdelt_score
        assert match_event(event, rules) is None

    def test_linked_inefficiency_ids_valid(self):
        rules = load_rules()
        valid = {i.id for i in load_inefficiencies()}
        for rule in rules:
            for iid in rule.linked_inefficiency_ids:
                assert iid in valid, f"{rule.id} links unknown inefficiency {iid}"

    def test_raw_yaml_matches_loader(self):
        raw = load_event_responses()
        assert {r["id"] for r in raw} == {f"C.{i}" for i in range(1, 8)}
        c7 = next(r for r in raw if r["id"] == "C.7")
        watch = c7["watchlist"]
        assert any(w["regulation"].startswith("China export controls")
                   and 2 in w["inefficiency_ids"] for w in watch)


# ------------------------------------------------------------ GDELT theming
class TestGdeltKeywordTheming:
    def test_all_40_inefficiencies_themed(self):
        kw = load_gdelt_keywords()
        assert set(kw) == {i.id for i in load_inefficiencies()}
        for iid, kws in kw.items():
            assert kws, f"inefficiency #{iid} has no keywords"

    def test_theme_content_from_cards(self):
        kw = load_gdelt_keywords()
        assert "rare earth" in kw[8]
        assert "gallium" in kw[3]
        assert "panama canal" in kw[18]
        assert "polysilicon" in kw[40]

    def test_scanner_uses_themed_keywords(self):
        class NoEvents:
            def get_events(self, since_hours=24):
                return []
        scanner = Layer1Scanner(NoEvents(), None)
        themed = scanner._keywords(scanner.inefficiencies[7])   # #8 Rare Earth
        assert "rare earth" in themed
        assert "export ban" in themed          # shared shock words retained
        # themed matching must not dilute: #38 copper card matches copper strike
        copper = scanner._keywords(scanner.inefficiencies[37])
        assert "copper" in copper

    def test_scanner_fires_on_themed_event(self):
        class OneEvent:
            def get_events(self, since_hours=24):
                return [Event(headline="China expands rare earth export controls",
                              goldstein_score=-7.0, score=0.8)]
        class NoPrices:
            def get_series(self, symbol, lookback_days=250):
                return []
        scanner = Layer1Scanner(OneEvent(), NoPrices())
        sigs = scanner.scan_all()
        assert any(s.inefficiency_id == 8 and s.trigger_type == "EVENT"
                   for s in sigs)
