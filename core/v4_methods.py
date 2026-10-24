"""
V4 methods — six soft SMC/ICT candidate generators.

Each method returns candidates, never signals.  A method that finds
nothing returns [].  Weakness is not filtered here: e.g. a sweep with a
tiny sweep_atr is still returned so the AI can see it and SKIP it with
a reason, instead of the old code silently treating every sweep as equal.
"""
from __future__ import annotations

from typing import List, Optional

from .mt5_data import CandleData, get_session
from .v4_candidates import build_candidate, Candidate

METHODS = {
    "A_sweep_bos_ob": "Sweep + BOS/CHoCH + hồi về OB chưa bị phá",
    "B_sweep_displacement_fvg": "Sweep + displacement + FVG entry",
    "C_ob_fvg_trend": "OB + FVG thuận xu hướng HTF (không cần sweep)",
    "D_breaker_mitigation": "Breaker block / mitigation sau khi OB cũ bị phá",
    "E_asia_liquidity_reversal": "Liquidity grab Asia + đảo chiều London/New York",
    "F_asia_range_bos": "Breakout range Asia có xác nhận BOS",
}


def _direction_from_sweep(candles, idx):
    prior = candles[idx - 20:idx]
    low, high = min(c.low for c in prior), max(c.high for c in prior)
    t = candles[idx]
    if t.low < low and t.close > low:
        return "BUY"
    if t.high > high and t.close < high:
        return "SELL"
    return None


def _session_of(c):
    return get_session(c.time.hour)


def generate_candidates(candles: List[CandleData], htf: Optional[list],
                        symbol: str, timeframe: str, spread: float = 0.0,
                        point_mult: float = 10000.0) -> List[Candidate]:
    if len(candles) < 30:
        return []
    idx = len(candles) - 2
    session = _session_of(candles[idx])
    out: List[Candidate] = []
    sweep_dir = _direction_from_sweep(candles, idx)

    def mk(method, direction):
        c = build_candidate(candles, htf, method, symbol, timeframe, direction,
                            session, spread, point_mult)
        if c:
            out.append(c)
        return c

    # A: sweep + BOS/CHoCH — the main method; still returned even without
    # BOS so the AI can judge the missing confirmation explicitly.
    if sweep_dir:
        mk("A_sweep_bos_ob", sweep_dir)
    # B: sweep + displacement — same sweep, different entry logic (FVG).
    if sweep_dir:
        c = mk("B_sweep_displacement_fvg", sweep_dir)
        if c and not c.has_fvg:
            c.notes = "No FVG at entry candle; AI should weigh displacement alone."
    # C: trend continuation — direction from HTF, no sweep required.
    if htf:
        from .v4_candidates import _htf_trend
        trend = _htf_trend(htf)
        if trend == "up":
            mk("C_ob_fvg_trend", "BUY")
        elif trend == "down":
            mk("C_ob_fvg_trend", "SELL")
    # D: breaker — only meaningful when price broke an OB; approximated by
    # a BOS against the previous trend (see _bos_choch CHoCH case).
    if sweep_dir:
        c = mk("D_breaker_mitigation", sweep_dir)
        if c:
            c.notes = "Breaker candidate: requires a prior OB break; AI must verify mitigation zone on chart."
    # E: Asia liquidity reversal — only in London/New York session labels.
    if sweep_dir and session in ("London", "New York"):
        mk("E_asia_liquidity_reversal", sweep_dir)
    # F: Asia range breakout — BOS in the current session direction.
    if session in ("London", "New York"):
        c = build_candidate(candles, htf, "F_asia_range_bos", symbol, timeframe,
                            sweep_dir or "BUY", session, spread, point_mult)
        if c and c.bos_choch:
            out.append(c)
    # De-duplicate identical method+direction (F can duplicate A/B direction
    # with a different method_id, which is intentional — methods differ).
    return out
