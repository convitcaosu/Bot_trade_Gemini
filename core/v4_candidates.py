"""
V4 candidates — soft SMC/ICT features, no hard signal gate here.

A candidate is a *proposal* for the AI brain, not a trade signal.
Every numeric feature is computed from candles that are already closed,
so a later AI verdict cannot leak future prices into the features.
The AI judge (v4_ai_judge) and the gate (v4_gate) decide dispatch.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .mt5_data import CandleData


def _atr(candles: List[CandleData], period: int = 14) -> float:
    if len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i].high, candles[i].low, candles[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return float(sum(trs[-period:]) / len(trs[-period:])) if trs else 0.0


def _swing_levels(candles: List[CandleData], lookback: int = 3):
    highs, lows = [], []
    for i in range(lookback, len(candles) - lookback):
        if all(candles[i].high >= candles[j].high for j in range(i - lookback, i + lookback + 1) if j != i):
            highs.append((i, candles[i].high))
        if all(candles[i].low <= candles[j].low for j in range(i - lookback, i + lookback + 1) if j != i):
            lows.append((i, candles[i].low))
    return highs, lows


def _bos_choch(candles: List[CandleData], idx: int, direction: str) -> str:
    """Proper, minimal BOS/CHoCH: a close beyond the last swing in that direction.

    Returns 'BOS', 'CHoCH' or ''. CHoCH is used when the break is against
    the previous swing trend; otherwise it is a continuation BOS.
    This replaces the old half-vs-half heuristic in mt5_data.
    """
    if idx < 10:
        return ""
    highs, lows = _swing_levels(candles[:idx], lookback=3)
    if direction == "BUY":
        if not highs:
            return ""
        last_high = highs[-1][1]
        # trend before the break: last swing low trend
        prev_highs = [h for _, h in highs[:-1]]
        broke = candles[idx].close > last_high
        if not broke:
            return ""
        return "CHoCH" if prev_highs and last_high < max(prev_highs) else "BOS"
    if not lows:
        return ""
    last_low = lows[-1][1]
    prev_lows = [l for _, l in lows[:-1]]
    broke = candles[idx].close < last_low
    if not broke:
        return ""
    return "CHoCH" if prev_lows and last_low > min(prev_lows) else "BOS"


def _last_unmitigated_ob(candles: List[CandleData], idx: int, direction: str):
    """Last strong opposite candle whose body has not been fully retraced.

    For a BUY candidate we want a bearish OB *below* the current price that
    price has not yet closed through; for SELL the mirror image.  The old
    code returned any 60%-body candle in the last 50 bars, mitigated or not.
    """
    for i in range(idx - 1, max(1, idx - 60), -1):
        c, prev = candles[i], candles[i - 1]
        rng = c.high - c.low
        if rng <= 0:
            continue
        body_pct = abs(c.close - c.open) / rng * 100
        if body_pct < 60:
            continue
        if direction == "BUY" and c.close < c.open:
            # bearish OB: mitigated if a later candle closed below its low
            if any(x.close < c.low for x in candles[i + 1:idx]):
                continue
            return {"price": c.open, "low": c.low, "high": c.high, "idx": i}
        if direction == "SELL" and c.close > c.open:
            if any(x.close > c.high for x in candles[i + 1:idx]):
                continue
            return {"price": c.open, "low": c.low, "high": c.high, "idx": i}
    return None


def _fvg(candles: List[CandleData], idx: int, direction: str):
    """3-candle fair value gap ending at idx, with a displacement candle."""
    if idx < 2:
        return None
    a, b, c = candles[idx - 2], candles[idx - 1], candles[idx]
    if direction == "BUY" and c.low > a.high and (b.close - b.open) > 0:
        return {"top": c.low, "bottom": a.high, "size": c.low - a.high}
    if direction == "SELL" and c.high < a.low and (b.close - b.open) < 0:
        return {"top": a.low, "bottom": c.high, "size": a.low - c.high}
    return None


def _htf_trend(htf: List[CandleData]) -> str:
    if len(htf) < 20:
        return "unknown"
    closes = [c.close for c in htf[-20:]]
    ema_fast = sum(closes[-5:]) / 5
    ema_slow = sum(closes) / len(closes)
    if ema_fast > ema_slow * 1.0005:
        return "up"
    if ema_fast < ema_slow * 0.9995:
        return "down"
    return "range"


@dataclass
class Candidate:
    method_id: str
    symbol: str
    timeframe: str
    direction: str  # BUY / SELL
    timestamp: datetime
    entry_price: float
    # Soft features — all in price units unless noted
    atr: float = 0.0
    wick_percent: float = 0.0
    sweep_atr: float = 0.0          # sweep distance / ATR
    sweep_pips: float = 0.0
    bos_choch: str = ""             # '', 'BOS', 'CHoCH'
    ob_distance_atr: float = 999.0  # distance entry -> OB, in ATR; 999 = none
    has_ob: bool = False
    fvg_size_atr: float = 0.0
    has_fvg: bool = False
    htf_trend: str = "unknown"      # up / down / range / unknown
    htf_agrees: bool = False
    session: str = ""
    spread: float = 0.0             # price units at candidate time, 0 = unknown
    spread_atr: float = 0.0
    volume_ratio: float = 0.0
    # Suggested (not final) levels; AI may adjust, gate validates.
    stop_loss: float = 0.0
    tp1: float = 0.0
    tp2: float = 0.0
    tp3: float = 0.0
    confluence_score: float = 0.0   # 0..10, local ranking only, NOT an AI score
    notes: str = ""

    def to_feature_dict(self) -> dict:
        return {
            "method_id": self.method_id, "symbol": self.symbol,
            "timeframe": self.timeframe, "direction": self.direction,
            "entry_price": round(self.entry_price, 5),
            "atr": round(self.atr, 5), "wick_percent": round(self.wick_percent, 1),
            "sweep_atr": round(self.sweep_atr, 2), "sweep_pips": round(self.sweep_pips, 1),
            "bos_choch": self.bos_choch, "has_ob": self.has_ob,
            "ob_distance_atr": round(self.ob_distance_atr, 2) if self.ob_distance_atr < 900 else None,
            "has_fvg": self.has_fvg, "fvg_size_atr": round(self.fvg_size_atr, 2),
            "htf_trend": self.htf_trend, "htf_agrees": self.htf_agrees,
            "session": self.session, "spread_atr": round(self.spread_atr, 3),
            "volume_ratio": round(self.volume_ratio, 2),
            "suggested_sl": round(self.stop_loss, 5), "suggested_tp1": round(self.tp1, 5),
            "suggested_tp2": round(self.tp2, 5), "suggested_tp3": round(self.tp3, 5),
            "confluence_score": round(self.confluence_score, 1),
        }


def build_candidate(candles: List[CandleData], htf: Optional[List[CandleData]],
                    method_id: str, symbol: str, timeframe: str, direction: str,
                    session: str, spread: float = 0.0, point_mult: float = 10000.0) -> Optional[Candidate]:
    """Build one soft candidate from the last closed candle (idx = len-2).

    Returns None only when the candles themselves are unusable; weak
    features do NOT return None — weakness is what the AI must judge.
    """
    if len(candles) < 30:
        return None
    idx = len(candles) - 2
    target = candles[idx]
    rng = target.high - target.low
    if rng <= 0:
        return None
    atr = _atr(candles[:idx + 1]) or rng
    prior = candles[idx - 20:idx]
    lowest, highest = min(c.low for c in prior), max(c.high for c in prior)
    if direction == "BUY":
        wick = (min(target.open, target.close) - target.low) / rng * 100
        sweep = max(0.0, lowest - target.low)
    else:
        wick = (target.high - max(target.open, target.close)) / rng * 100
        sweep = max(0.0, target.high - highest)
    bos = _bos_choch(candles, idx, direction)
    ob = _last_unmitigated_ob(candles, idx, direction)
    fvg = _fvg(candles, idx, direction)
    htf_trend = _htf_trend(htf) if htf else "unknown"
    htf_agrees = (htf_trend == "up" and direction == "BUY") or (htf_trend == "down" and direction == "SELL")
    vol = target.volume
    avg_vol = sum(c.volume for c in prior[-5:]) / max(1, len(prior[-5:])) or 1
    # Dynamic SL/TP suggestion (same structure idea as v3, but AI can override)
    if direction == "BUY":
        sl = target.low - atr * 0.3
        risk = max(target.close - sl, atr * 0.2)
        tp1, tp2, tp3 = target.close + risk * 1.5, target.close + risk * 2.5, target.close + risk * 4.0
    else:
        sl = target.high + atr * 0.3
        risk = max(sl - target.close, atr * 0.2)
        tp1, tp2, tp3 = target.close - risk * 1.5, target.close - risk * 2.5, target.close - risk * 4.0
    ob_dist = abs(target.close - ob["price"]) / atr if ob else 999.0
    # Local ranking only: BOS/CHoCH and HTF agreement weigh most.
    score = 0.0
    score += 2.0 if bos == "BOS" else (2.5 if bos == "CHoCH" else 0.0)
    score += 1.5 if ob else 0.0
    score += 1.0 if fvg else 0.0
    score += 1.5 if htf_agrees else 0.0
    score += 1.0 if wick >= 55 else (0.5 if wick >= 40 else 0.0)
    score += 1.0 if sweep / atr >= 0.3 else (0.5 if sweep > 0 else 0.0)
    score += 0.5 if vol / avg_vol >= 1.2 else 0.0
    return Candidate(
        method_id=method_id, symbol=symbol, timeframe=timeframe, direction=direction,
        timestamp=target.time, entry_price=round(target.close, 5),
        atr=atr, wick_percent=round(wick, 1), sweep_atr=round(sweep / atr, 2) if atr else 0.0,
        sweep_pips=round(sweep * point_mult, 1), bos_choch=bos,
        ob_distance_atr=ob_dist, has_ob=bool(ob),
        fvg_size_atr=round(fvg["size"] / atr, 2) if fvg else 0.0, has_fvg=bool(fvg),
        htf_trend=htf_trend, htf_agrees=htf_agrees, session=session,
        spread=spread, spread_atr=round(spread / atr, 3) if atr and spread else 0.0,
        volume_ratio=round(vol / avg_vol, 2),
        stop_loss=round(sl, 5), tp1=round(tp1, 5), tp2=round(tp2, 5), tp3=round(tp3, 5),
        confluence_score=round(min(score, 10.0), 1),
    )
