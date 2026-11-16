"""UGT-15: one position per (instrument, direction) - batch + open book."""

from newsetup.models import ConfirmedSignal, RawSignal, SizedSignal, utcnow


def _sized(iid, instrument, direction, conf):
    raw = RawSignal(inefficiency_id=iid, inefficiency_name="x",
                    instrument=instrument, direction=direction,
                    trigger_type="EVENT", trigger_description="t",
                    confidence=conf, ts=utcnow())
    cs = ConfirmedSignal(raw=raw, confirmed=True, score=conf)
    return SizedSignal(signal=cs, lot_size=0.1, entry_price=100.0,
                       stop_loss=95.0, take_profit=110.0, sector=":X",
                       confidence=conf)


class _T:
    def __init__(self, instrument, direction):
        self.instrument = instrument
        self.direction = direction


def test_batch_dedup_keeps_highest_confidence():
    from main import _dedup_by_instrument
    sized = [
        _sized(1, "USDCNH", "BUY", 0.80),
        _sized(2, "USDCNH", "BUY", 0.95),
        _sized(3, "USDCNH", "BUY", 0.89),
        _sized(4, "LIN.US", "BUY", 0.70),
    ]
    out = _dedup_by_instrument(sized, [])
    assert len(out) == 2
    usd = [s for s in out if s.signal.raw.instrument == "USDCNH"]
    assert len(usd) == 1 and usd[0].signal.raw.confidence == 0.95


def test_open_trade_blocks_new_signal():
    from main import _dedup_by_instrument
    sized = [_sized(9, "USDCNH", "BUY", 0.9)]
    out = _dedup_by_instrument(sized, [_T("USDCNH", "BUY")])
    assert out == []


def test_opposite_direction_allowed():
    from main import _dedup_by_instrument
    sized = [_sized(9, "USDCNH", "SELL", 0.9)]
    out = _dedup_by_instrument(sized, [_T("USDCNH", "BUY")])
    assert len(out) == 1
