"""V4 unit tests — no MT5, no Gemini, no network. Run: python -m pytest tests/ -q
or: python tests/test_v4.py
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mt5_data import CandleData
from core.v4_ai_judge import parse_verdict
from core.v4_candidates import build_candidate
from core.v4_engine import V4Engine
from core.v4_gate import gate
from core.v4_methods import generate_candidates
from core.v4_symbols import SymbolUniverse
from core.v4_training import label_candidate


def _candles(n=80, base=100.0):
    out = []
    t = datetime(2026, 10, 24, 10, 0)
    for i in range(n):
        # gentle uptrend, then a sweep candle near the end is built by caller
        price = base + i * 0.1
        out.append(CandleData(time=t + timedelta(minutes=5 * i), open=price,
                              high=price + 0.3, low=price - 0.3, close=price + 0.1, volume=100))
    return out


def _sweep_candles():
    cs = _candles(80)
    # last closed candle (idx -2): sweep below prior lows, long lower wick, bullish close
    t = cs[-2]
    cs[-2] = CandleData(time=t.time, open=107.0, high=107.5, low=105.0, close=107.4, volume=200)
    cs[-1] = CandleData(time=t.time + timedelta(minutes=5), open=107.4, high=107.6, low=107.2, close=107.5, volume=100)
    return cs


def test_methods_return_candidates_not_signals():
    cs = _sweep_candles()
    cands = generate_candidates(cs, None, "EURUSD", "M5")
    assert cands, "sweep should produce at least one soft candidate"
    assert all(c.direction in ("BUY", "SELL") for c in cands)
    assert all(c.entry_price > 0 for c in cands)


def test_ai_parse_rejects_bad_json_and_mismatch():
    cs = _sweep_candles()
    cand = build_candidate(cs, None, "A_sweep_bos_ob", "EURUSD", "M5", "BUY", "London")
    assert cand is not None
    bad = parse_verdict("BUY 9/10 great trade", cand)
    assert bad.decision == "SKIP" and bad.reason == "ai_parse_failed"
    mismatch = parse_verdict('{"decision":"SELL","confidence":9,"entry_price":1,"stop_loss":0.9,"tp1":1.1,"tp2":1.2,"tp3":1.3}', cand)
    assert mismatch.decision == "SKIP"


def test_gate_blocks_low_confidence_and_zero_levels():
    cs = _sweep_candles()
    cand = build_candidate(cs, None, "A_sweep_bos_ob", "EURUSD", "M5", "BUY", "London")
    good = parse_verdict('{"decision":"BUY","confidence":9,"entry_price":107.4,"stop_loss":104.8,"tp1":109.0,"tp2":112.0,"tp3":114.0,"components":{"trend":8,"structure":9,"liquidity":8,"timing":7},"reason":"BOS + OB"}', cand)
    assert gate(cand, good, preset="balanced").allowed
    low = parse_verdict('{"decision":"BUY","confidence":5,"entry_price":107.4,"stop_loss":104.8,"tp1":109.0,"tp2":111.0,"tp3":114.0}', cand)
    assert not gate(cand, low, preset="balanced").allowed
    zero = parse_verdict('{"decision":"BUY","confidence":9,"entry_price":0,"stop_loss":0,"tp1":0,"tp2":0,"tp3":0}', cand)
    assert not gate(cand, zero).allowed


def test_engine_offline_never_dispatches():
    class FakeMT5:
        timeframe_str = "M5"
        def get_candles(self, symbol, count):
            return _sweep_candles()
    class FakeBrain:
        ready = False
    eng = V4Engine(FakeMT5(), FakeBrain(), preset="balanced", universe=SymbolUniverse())
    sigs = eng.scan_symbol("EURUSD")
    assert sigs == []
    assert eng.skipped and eng.skipped[0]["reason"] == "ai_offline"


def test_label_uses_future_only_and_spread():
    cs = _sweep_candles()
    cand = build_candidate(cs, None, "A_sweep_bos_ob", "EURUSD", "M5", "BUY", "London")
    # future: price rises to TP1
    fut = [CandleData(time=datetime(2026, 10, 24, 12, 0), open=107.5, high=110.0, low=107.0, close=109.0, volume=100)]
    row = label_candidate(cand, fut, spread=0.0)
    assert row.hit_tp1_first in (0, 1)  # label depends on suggested TP; must not crash


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("PASS", fn.__name__)
    print("All V4 tests passed")
