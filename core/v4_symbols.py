"""
V4 symbol universe — unlimited list, tiered AI use.

Tier 1 (cheap, local, every scan): all visible MT5 symbols, feature
computation only.  Tier 2 (expensive, Gemini): top-N candidates by
confluence_score, with a per-symbol cooldown, so "unlimited symbols"
does not mean unlimited Gemini calls.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List

from .v4_candidates import Candidate


@dataclass
class SymbolSpec:
    name: str
    digits: int = 5
    point: float = 0.00001
    point_mult: float = 10000.0  # price -> pips, derived from digits, not hard-coded per pair
    spread: float = 0.0

    @classmethod
    def from_digits(cls, name: str, digits: int, spread: float = 0.0):
        if "XAU" in name.upper() or "GOLD" in name.upper():
            mult = 1.0  # XAUUSD price units are already dollars; v3 used 1, keep it explicit
        elif "JPY" in name.upper():
            mult = 100.0 if digits == 3 else 10.0
        else:
            mult = 10000.0 if digits in (4, 5) else 100.0
        point = 10 ** (-digits) if digits else 0.00001
        return cls(name=name, digits=digits, point=point, point_mult=mult, spread=spread)


class SymbolUniverse:
    def __init__(self, max_ai_per_minute: int = 10, top_n_per_scan: int = 5,
                 cooldown_sec: int = 300):
        self.max_ai_per_minute = max_ai_per_minute
        self.top_n_per_scan = top_n_per_scan
        self.cooldown_sec = cooldown_sec
        self._last_ai: dict[str, float] = {}
        self._ai_calls: List[float] = []

    def rank_candidates(self, candidates: List[Candidate], now: float | None = None) -> List[Candidate]:
        now = now or time.time()
        # Cooldown: a symbol that just got an AI verdict is not re-judged.
        fresh = [c for c in candidates
                 if now - self._last_ai.get(f"{c.symbol}:{c.method_id}", 0) >= self.cooldown_sec]
        fresh.sort(key=lambda c: c.confluence_score, reverse=True)
        return fresh[:self.top_n_per_scan]

    def can_call_ai(self, now: float | None = None) -> bool:
        now = now or time.time()
        self._ai_calls = [t for t in self._ai_calls if now - t < 60]
        return len(self._ai_calls) < self.max_ai_per_minute

    def record_ai_call(self, candidate: Candidate, now: float | None = None):
        now = now or time.time()
        self._ai_calls.append(now)
        self._last_ai[f"{candidate.symbol}:{candidate.method_id}"] = now
