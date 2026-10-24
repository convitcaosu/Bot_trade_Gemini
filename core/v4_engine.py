"""
V4 engine — candidate -> AI judge -> gate -> Signal (or SKIP, logged).

This is the only V4 entry point main.py needs.  It does NOT replace the
legacy EA-screenshot path; main.py keeps that path but now refuses to
dispatch entry/SL/TP == 0 signals (see main.py V4 patch).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .mt5_data import CandleData
from .signal_dispatcher import Signal
from .v4_ai_judge import judge_with_gemini
from .v4_candidates import Candidate
from .v4_gate import gate
from .v4_methods import generate_candidates
from .v4_symbols import SymbolUniverse


class V4Engine:
    def __init__(self, mt5_connector, gemini_brain, preset: str = "balanced",
                 universe: Optional[SymbolUniverse] = None, model_prob_fn=None):
        self.mt5 = mt5_connector
        self.gemini = gemini_brain
        self.preset = preset
        self.universe = universe or SymbolUniverse()
        self.model_prob_fn = model_prob_fn  # fn(candidate) -> float|None
        self.skipped: List[dict] = []  # SKIP reasons, shown in UI / logs

    def scan_symbol(self, symbol: str, spread: float = 0.0, point_mult: float = 10000.0) -> List[Signal]:
        """Scan one symbol with V4. Returns dispatched signals (usually 0-1)."""
        try:
            candles = self.mt5.get_candles(symbol, 120)
            htf = []
            try:
                # HTF context: reuse the connector timeframe switch is
                # avoided here — callers that have H1 candles pass them in
                # via scan_symbol_htf(); without HTF, trend is 'unknown'
                # and the AI must weigh that explicitly.
                pass
            except Exception:
                htf = []
            return self.scan_candles(symbol, candles, htf, spread, point_mult)
        except Exception as e:
            self.skipped.append({"symbol": symbol, "reason": f"scan_error: {e}"})
            return []

    def scan_candles(self, symbol: str, candles: List[CandleData],
                    htf: Optional[List[CandleData]] = None, spread: float = 0.0,
                    point_mult: float = 10000.0) -> List[Signal]:
        timeframe = getattr(self.mt5, "timeframe_str", "M5")
        candidates = generate_candidates(candles, htf, symbol, timeframe, spread, point_mult)
        ranked = self.universe.rank_candidates(candidates)
        signals: List[Signal] = []
        for cand in ranked:
            if not self.universe.can_call_ai():
                self.skipped.append({"symbol": symbol, "method": cand.method_id, "reason": "ai_rate_limit"})
                continue
            self.universe.record_ai_call(cand)
            verdict = judge_with_gemini(self.gemini, cand)
            if verdict.decision == "SKIP":
                self.skipped.append({"symbol": symbol, "method": cand.method_id, "reason": verdict.reason})
                continue
            prob = self.model_prob_fn(cand) if self.model_prob_fn else None
            g = gate(cand, verdict, preset=self.preset, model_prob=prob, spread=spread)
            if not g.allowed:
                self.skipped.append({"symbol": symbol, "method": cand.method_id, "reason": g.reason})
                continue
            signals.append(Signal(
                signal_id=f"V4_{symbol}_{cand.method_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
                symbol=symbol, timeframe=timeframe, direction=verdict.decision,
                entry_price=verdict.entry_price, stop_loss=verdict.stop_loss,
                take_profit=verdict.tp2, tp1=verdict.tp1, tp2=verdict.tp2, tp3=verdict.tp3,
                ai_score=verdict.confidence, ai_analysis=verdict.reason,
                session=cand.session, wick_percent=cand.wick_percent,
                sweep_pips=cand.sweep_pips, has_fvg=cand.has_fvg, has_ob=cand.has_ob,
                market_structure=cand.bos_choch, atr=cand.atr, rr_ratio=g.rr_tp2,
                outcome="PENDING", method_id=cand.method_id, ai_reason=verdict.reason,
                ai_components=verdict.components,
            ))
        return signals
