"""
V4 training dataset — from MT5 candles + spread, with honest labels.

Dataset row = one candidate (see v4_candidates).  Label, computed ONLY
from candles after the candidate candle, after subtracting spread:
- hit_tp1_first: 1 if TP1 is touched before SL, else 0
- rr_net: realised R, where a loss is -1 and a TP1-first win is at least
  the TP1 R (partial) — full TP2/TP3 outcome is kept in tp_hit.

Walk-forward split is by time, never random: random splits leak the
future into training because neighbouring candles share structure.
A model trained here is a probability estimator, not a promise of
winrate.  sklearn is used only if installed; otherwise the module
still exports the dataset and per-method statistics, which is enough
to rank methods and to feed the gate's model_prob later.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import List, Tuple

from .mt5_data import CandleData
from .v4_candidates import Candidate

FEATURES = ["wick_percent", "sweep_atr", "bos_choch", "has_ob", "ob_distance_atr",
            "has_fvg", "fvg_size_atr", "htf_agrees", "spread_atr", "volume_ratio",
            "session", "method_id"]


@dataclass
class LabelledRow:
    candidate: Candidate
    hit_tp1_first: int
    rr_net: float
    tp_hit: str


def label_candidate(cand: Candidate, future: List[CandleData], spread: float = 0.0) -> LabelledRow:
    """Label from future candles only. Spread widens the effective SL."""
    entry, sl = cand.entry_price, cand.stop_loss
    # Effective entry is worse by spread for a market entry.
    eff_entry = entry + spread if cand.direction == "BUY" else entry - spread
    risk = abs(eff_entry - sl)
    if risk <= 0:
        return LabelledRow(cand, 0, 0.0, "INVALID")
    for c in future[:60]:
        if cand.direction == "BUY":
            if c.low <= sl:
                return LabelledRow(cand, 0, -1.0, "SL")
            if c.high >= cand.tp3:
                return LabelledRow(cand, 1, abs(cand.tp3 - eff_entry) / risk, "TP3")
            if c.high >= cand.tp2:
                return LabelledRow(cand, 1, abs(cand.tp2 - eff_entry) / risk, "TP2")
            if c.high >= cand.tp1:
                return LabelledRow(cand, 1, abs(cand.tp1 - eff_entry) / risk, "TP1")
        else:
            if c.high >= sl:
                return LabelledRow(cand, 0, -1.0, "SL")
            if c.low <= cand.tp3:
                return LabelledRow(cand, 1, abs(eff_entry - cand.tp3) / risk, "TP3")
            if c.low <= cand.tp2:
                return LabelledRow(cand, 1, abs(eff_entry - cand.tp2) / risk, "TP2")
            if c.low <= cand.tp1:
                return LabelledRow(cand, 1, abs(eff_entry - cand.tp1) / risk, "TP1")
    return LabelledRow(cand, 0, 0.0, "PENDING")


def walk_forward_split(rows: List[LabelledRow], train_frac: float = 0.7) -> Tuple[list, list]:
    rows = sorted(rows, key=lambda r: r.candidate.timestamp)
    n = int(len(rows) * train_frac)
    return rows[:n], rows[n:]


def export_csv(rows: List[LabelledRow], path: str) -> str:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "symbol", "timeframe", "method_id", "direction",
                    "wick_percent", "sweep_atr", "bos_choch", "has_ob", "ob_distance_atr",
                    "has_fvg", "fvg_size_atr", "htf_agrees", "spread_atr", "volume_ratio",
                    "session", "hit_tp1_first", "rr_net", "tp_hit"])
        for r in rows:
            c = r.candidate
            w.writerow([c.timestamp, c.symbol, c.timeframe, c.method_id, c.direction,
                        c.wick_percent, c.sweep_atr, c.bos_choch, int(c.has_ob),
                        c.ob_distance_atr, int(c.has_fvg), c.fvg_size_atr,
                        int(c.htf_agrees), c.spread_atr, c.volume_ratio, c.session,
                        r.hit_tp1_first, round(r.rr_net, 3), r.tp_hit])
    return path


def train_simple_model(rows: List[LabelledRow]):
    """Train a gradient-boosting classifier if sklearn is available.

    Returns (model, feature_names) or (None, reason).  The caller must
    still validate on the walk-forward test split and on demo forward
    data before using model_prob in the gate.
    """
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier
        import numpy as np
    except ImportError:
        return None, "sklearn_not_installed"
    if len(rows) < 50:
        return None, "not_enough_rows_min_50"
    def feats(r):
        c = r.candidate
        return [c.wick_percent, c.sweep_atr, 1 if c.bos_choch == "BOS" else (2 if c.bos_choch == "CHoCH" else 0),
                int(c.has_ob), min(c.ob_distance_atr, 10), int(c.has_fvg), c.fvg_size_atr,
                int(c.htf_agrees), c.spread_atr, c.volume_ratio]
    X = np.array([feats(r) for r in rows], dtype=float)
    y = np.array([r.hit_tp1_first for r in rows], dtype=int)
    if len(set(y.tolist())) < 2:
        return None, "only_one_class_in_labels"
    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3)
    model.fit(X, y)
    return model, ["wick", "sweep_atr", "bos", "has_ob", "ob_dist", "has_fvg",
                   "fvg_atr", "htf_agrees", "spread_atr", "volume_ratio"]
