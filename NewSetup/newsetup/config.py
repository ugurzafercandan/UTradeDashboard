"""Configuration loading for NewSetup."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import yaml

from .models import Inefficiency, Trigger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT, "config")


def _read_yaml(name: str) -> Any:
    with open(os.path.join(CONFIG_DIR, name), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_settings() -> dict:
    """Global settings dict (config/settings.yaml)."""
    return _read_yaml("settings.yaml")


def load_instruments() -> dict:
    """Pepperstone instrument map (config/instruments.yaml)."""
    return _read_yaml("instruments.yaml")


@lru_cache(maxsize=1)
def load_inefficiencies() -> list[Inefficiency]:
    """All 40 inefficiency definitions with triggers, as domain objects."""
    raw = _read_yaml("inefficiencies.yaml")
    result: list[Inefficiency] = []
    seen_categories = {}
    # category assignment by id range per playbook section 3.1
    for item in raw:
        iid = item["id"]
        if iid <= 12:
            cat = "ENERGY_MINING"
        elif iid <= 26:
            cat = "FOOD_SHIPPING"
        else:
            cat = "TECH_INFRA"
        seen_categories[cat] = seen_categories.get(cat, 0) + 1
        triggers = [
            Trigger(
                id=t["id"],
                inefficiency_id=iid,
                trigger_type=t["trigger_type"],
                condition=t.get("condition", ""),
                threshold=t.get("threshold", ""),
                data_source=t.get("data_source", ""),
                scan_freq=t.get("scan_freq", ""),
            )
            for t in item.get("triggers", [])
        ]
        result.append(
            Inefficiency(
                id=iid,
                name=item["name"],
                category=cat,
                concentration=item.get("concentration", ""),
                instruments=item.get("instruments", {}),
                trade_type=item.get("trade_type", ""),
                triggers=triggers,
            )
        )
    return result


def sector_for(inefficiency: Inefficiency) -> str:
    """Correlation sector grouping used for exposure caps (playbook D.4)."""
    return f"{inefficiency.category}:{inefficiency.name}"
