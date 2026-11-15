"""Event response layer (playbook Appendix C).

Loads the 7 declarative event response playbooks from
config/event_responses.yaml and matches incoming news events against their
event signatures:

    event signature -> severity tier -> trade matrix -> position limits
                    -> de-escalation criteria

The playbooks are plain config data; this module provides the loader, the
event-to-playbook matching and helpers to resolve a matched playbook into
concrete trade actions and limits for the layer-2/3 pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from newsetup.config import load_event_responses
from newsetup.models import Event


@dataclass
class EventResponseRule:
    """One Appendix C playbook in machine-checkable form."""

    id: str
    name: str
    scenario: str
    keywords: list[str]
    min_gdelt_score: float
    severity_tiers: list[dict] = field(default_factory=list)
    immediate_actions: list[dict] = field(default_factory=list)
    strait_actions: dict[str, list[dict]] = field(default_factory=dict)
    trade_matrix: list[dict] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    position_limits: dict = field(default_factory=dict)
    de_escalation_criteria: list[str] = field(default_factory=list)
    linked_inefficiency_ids: list[int] = field(default_factory=list)
    linked_fx_strategy_ids: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    def keyword_hits(self, text: str) -> list[str]:
        """Which of this rule's signature keywords appear in ``text``."""
        return [k for k in self.keywords if k in text]

    def matches(self, event: Event) -> bool:
        if event.score < self.min_gdelt_score:
            return False
        return bool(self.keyword_hits(event.headline.lower()))

    def tier(self, tier_id: str) -> dict | None:
        for t in self.severity_tiers:
            if str(t.get("tier")) == tier_id:
                return t
        return None

    def matrix_row(self, trigger: str) -> dict | None:
        for row in self.trade_matrix:
            if row.get("trigger", "").lower() == trigger.lower():
                return row
        return None

    def actions_for(self, strait: str) -> list[dict]:
        """Priority-ordered trade actions for a named strait (C.2 only)."""
        return self.strait_actions.get(strait, [])


def _rule_from_raw(raw: dict) -> EventResponseRule:
    sig = raw["event_signature"]
    return EventResponseRule(
        id=raw["id"],
        name=raw["name"],
        scenario=raw.get("scenario", ""),
        keywords=list(sig["keywords"]),
        min_gdelt_score=float(sig["min_gdelt_score"]),
        severity_tiers=raw.get("severity_tiers", []),
        immediate_actions=raw.get("immediate_actions", []),
        strait_actions=raw.get("strait_actions", {}),
        trade_matrix=raw.get("trade_matrix", []),
        timeline=raw.get("timeline", []),
        position_limits=raw.get("position_limits", {}),
        de_escalation_criteria=raw.get("de_escalation_criteria", []),
        linked_inefficiency_ids=raw.get("linked_inefficiency_ids", []),
        linked_fx_strategy_ids=raw.get("linked_fx_strategy_ids", []),
        raw=raw,
    )


def load_rules() -> list[EventResponseRule]:
    """All 7 event response rules as domain objects."""
    return [_rule_from_raw(r) for r in load_event_responses()]


def match_event(event: Event, rules: list[EventResponseRule] | None = None
                ) -> EventResponseRule | None:
    """Best-matching playbook for ``event`` (most keyword hits wins)."""
    rules = rules if rules is not None else load_rules()
    best: EventResponseRule | None = None
    best_hits: list[str] = []
    for rule in rules:
        if not rule.matches(event):
            continue
        hits = rule.keyword_hits(event.headline.lower())
        if len(hits) > len(best_hits):
            best, best_hits = rule, hits
    return best


class EventResponseEngine:
    """End-to-end wrapper: event in -> response plan out."""

    def __init__(self, rules: list[EventResponseRule] | None = None):
        self.rules = rules if rules is not None else load_rules()

    def respond(self, event: Event) -> dict | None:
        """Resolve ``event`` into a concrete response plan dict, or None."""
        rule = match_event(event, self.rules)
        if rule is None:
            return None
        return {
            "playbook_id": rule.id,
            "playbook_name": rule.name,
            "matched_keywords": rule.keyword_hits(event.headline.lower()),
            "immediate_actions": rule.immediate_actions,
            "trade_matrix": rule.trade_matrix,
            "strait_actions": rule.strait_actions,
            "position_limits": rule.position_limits,
            "de_escalation_criteria": rule.de_escalation_criteria,
            "linked_inefficiency_ids": rule.linked_inefficiency_ids,
            "linked_fx_strategy_ids": rule.linked_fx_strategy_ids,
        }
