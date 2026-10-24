"""
V4 gate — the only place that may turn a candidate + AI verdict into a signal.

Presets (user-selectable in Settings, not hard-coded per trade):
- conservative: confidence >= 8, min RR (TP2) >= 2.0, local model prob >= 0.60 if available
- balanced:     confidence >= 7, min RR >= 1.5, local model prob >= 0.50 if available
- aggressive:   confidence >= 6, min RR >= 1.2, no local-model requirement
"""
from __future__ import annotations

from dataclasses import dataclass

from .v4_ai_judge import AIVerdict
from .v4_candidates import Candidate

PRESETS = {
    "conservative": {"min_confidence": 8.0, "min_rr": 2.0, "min_model_prob": 0.60},
    "balanced": {"min_confidence": 7.0, "min_rr": 1.5, "min_model_prob": 0.50},
    "aggressive": {"min_confidence": 6.0, "min_rr": 1.2, "min_model_prob": None},
}


@dataclass
class GateResult:
    allowed: bool
    reason: str
    rr_tp2: float = 0.0


def _rr(entry, sl, tp):
    risk = abs(entry - sl)
    if risk <= 0:
        return 0.0
    return abs(tp - entry) / risk


def gate(candidate: Candidate, verdict: AIVerdict, preset: str = "balanced",
         model_prob: float | None = None, spread: float = 0.0) -> GateResult:
    cfg = PRESETS.get(preset, PRESETS["balanced"])
    if verdict.decision == "SKIP":
        return GateResult(False, f"AI SKIP: {verdict.reason or 'no reason'}")
    if verdict.decision != candidate.direction:
        return GateResult(False, "ai_direction_mismatch")
    if verdict.confidence < cfg["min_confidence"]:
        return GateResult(False, f"confidence {verdict.confidence} < {cfg['min_confidence']}")
    # Validity: no zero/placeholder levels, risk must exceed spread.
    entry, sl, tp1, tp2 = verdict.entry_price, verdict.stop_loss, verdict.tp1, verdict.tp2
    if entry <= 0 or sl <= 0 or tp1 <= 0 or tp2 <= 0:
        return GateResult(False, "invalid_levels_entry_sl_tp_zero")
    risk = abs(entry - sl)
    if risk <= 0 or (spread and risk <= spread):
        return GateResult(False, "risk_not_greater_than_spread")
    if candidate.direction == "BUY" and not (sl < entry < tp1 <= tp2):
        return GateResult(False, "levels_not_ordered_buy")
    if candidate.direction == "SELL" and not (sl > entry > tp1 >= tp2):
        return GateResult(False, "levels_not_ordered_sell")
    rr = _rr(entry, sl, tp2)
    if rr < cfg["min_rr"]:
        return GateResult(False, f"rr {rr:.2f} < {cfg['min_rr']}")
    if cfg["min_model_prob"] is not None and model_prob is not None and model_prob < cfg["min_model_prob"]:
        return GateResult(False, f"local_model_prob {model_prob:.2f} < {cfg['min_model_prob']}")
    return GateResult(True, "passed", rr_tp2=round(rr, 2))
