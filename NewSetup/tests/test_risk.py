"""Tests for the NewSetup RiskEnforcer (playbook 7.2, Appendix D).

Each playbook risk cap and drawdown circuit breaker is exercised with
directly constructed AccountState / Trade / SizedSignal dataclasses.
"""

from __future__ import annotations

import pytest

from execution.risk_enforcer import RiskEnforcer
from newsetup.models import AccountState

from _risk_helpers import make_sized, make_trade

SECTOR = "ENERGY_MINING:Test Inefficiency"
OTHER_SECTOR = "FOOD_SHIPPING:Other Inefficiency"


def account(equity: float = 1000.0, margin: float = 0.0) -> AccountState:
    return AccountState(balance=equity, equity=equity, margin_used=margin,
                        open_positions=0)


# ----------------------------------------------------------------- pass case
def test_pass_case_returns_ok():
    re = RiskEnforcer()
    sized = make_sized(sector=SECTOR)
    result = re.check(sized, account(10000.0), [])
    assert result == (True, "ok")
    assert re.allowed(sized, account(10000.0), [])


# -------------------------------------------------------------------- margin
def test_margin_rejection():
    re = RiskEnforcer()  # max_margin_used_pct = 25
    sized = make_sized()
    # 300/1000 = 30% > 25% -> reject
    assert re.check(sized, account(1000.0, margin=300.0), []) == (False, "margin")
    # 200/1000 = 20% <= 25% -> passes margin (and everything else)
    assert re.check(sized, account(1000.0, margin=200.0), []) == (True, "ok")


# ------------------------------------------------------------- max positions
def test_max_positions_rejection():
    re = RiskEnforcer()  # max_open_positions = 7
    sized = make_sized()
    six_open = [make_trade() for _ in range(6)]
    assert re.check(sized, account(10000.0), six_open) == (True, "ok")
    seven_open = [make_trade() for _ in range(7)]
    assert re.check(sized, account(10000.0), seven_open) == (False, "max_positions")


# ---------------------------------------------------------- sector exposure
def test_sector_exposure_rejection():
    re = RiskEnforcer()  # max_sector_exposure_pct = 20
    # equity 1000; three open trades in the same sector at 100 * 1 lot
    # -> 300 exposure; new signal adds 100 -> 40% > 20% -> reject
    open_trades = [make_trade(entry=100.0, lot=1.0, sector=SECTOR)
                   for _ in range(3)]
    sized = make_sized(entry=100.0, lot=1.0, sector=SECTOR)
    assert re.check(sized, account(1000.0), open_trades) == (False, "sector_exposure")

    # same open book but the new signal is in a different sector:
    # exposure = 100/1000 = 10% -> passes sector check (and heat below)
    sized_other = make_sized(entry=100.0, lot=0.1, sector=OTHER_SECTOR)
    assert re.check(sized_other, account(1000.0), open_trades) == (True, "ok")


# ------------------------------------------------------------ portfolio heat
def test_portfolio_heat_rejection():
    re = RiskEnforcer()  # max_portfolio_heat_pct = 3
    # three open trades, other sector, each |100-90| * 1 = 10 risk
    # new signal adds 10 -> total 40 / 1000 equity = 4% > 3% -> reject
    open_trades = [make_trade(entry=100.0, stop=90.0, lot=1.0,
                              sector=OTHER_SECTOR)
                   for _ in range(3)]
    sized = make_sized(entry=100.0, sl=90.0, lot=1.0, sector=SECTOR)
    assert re.check(sized, account(1000.0), open_trades) == (False, "heat")

    # a single open trade: (10 + 10) / 1000 = 2% <= 3% -> ok
    one_open = open_trades[:1]
    assert re.check(sized, account(1000.0), one_open) == (True, "ok")


# ----------------------------------------------------- drawdown breakers 5/8/12
def test_drawdown_breakers():
    re = RiskEnforcer()  # pause 5 / week halt 8 / full halt 12
    sized = make_sized()
    acct = account(10000.0)

    # below 5%: no breaker
    re.update_drawdown(960.0, 1000.0)  # 4%
    assert re.current_breaker() == "none"
    assert re.check(sized, acct, []) == (True, "ok")

    # 5% -> pause
    re.update_drawdown(950.0, 1000.0)
    assert re.current_breaker() == "pause"
    assert re.check(sized, acct, []) == (False, "dd_pause")

    # 8% -> week halt
    re.update_drawdown(920.0, 1000.0)
    assert re.current_breaker() == "week_halt"
    assert re.check(sized, acct, []) == (False, "dd_week_halt")

    # 12% -> full halt
    re.update_drawdown(880.0, 1000.0)
    assert re.current_breaker() == "full_halt"
    assert re.check(sized, acct, []) == (False, "dd_full_halt")

    # recovery below 5% clears the breaker
    re.update_drawdown(970.0, 1000.0)
    assert re.current_breaker() == "none"


# --------------------------------------------------------------- daily loss
def test_daily_loss_rejection():
    re = RiskEnforcer()  # max_daily_loss_pct = 2
    sized = make_sized()
    acct = account(1000.0)

    # day pnl -30 on 1000 equity: -30 <= -1000*2% = -20 -> reject
    re.set_day_pnl(-30.0, 1000.0)
    assert re.check(sized, acct, []) == (False, "daily_loss")

    # day pnl -10: -10 > -20 -> allowed
    re.set_day_pnl(-10.0, 1000.0)
    assert re.check(sized, acct, []) == (True, "ok")


# -------------------------------------------------- enforcer is state-scoped
def test_fresh_enforcer_has_no_breaker_state():
    re = RiskEnforcer()
    assert re.current_breaker() == "none"
    assert re.check(make_sized(), account(10000.0), []) == (True, "ok")
