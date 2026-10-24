"""
V4 tick reader — Python side of GeminiTickCollector.mq5.

Reads MQL5/Files/gemini_ticks/ticks_<SYMBOL>_YYYYMMDD.csv, deduplicates
by time_ms (realtime append can overlap history), and returns:
- spread_at(signal_time): median ask-bid in a window around the signal
- tick candles: resampled OHLC from bid ticks (for training features)

No MT5 connection is needed here; the EA already wrote the files.
On Windows, the folder is usually:
  %APPDATA%\\MetaQuotes\\Terminal\\<id>\\MQL5\\Files\\gemini_ticks
Copy that folder (or point tick_dir at it) before training.
"""
from __future__ import annotations

import csv
import glob
import os
import statistics
from datetime import datetime


def read_ticks(tick_dir: str, symbol: str):
    rows = {}
    for path in sorted(glob.glob(os.path.join(tick_dir, f"ticks_{symbol}_*.csv"))):
        try:
            with open(path, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    try:
                        ms = int(r["time_ms"])
                        rows[ms] = (float(r["bid"]), float(r["ask"]), float(r.get("last") or 0))
                    except Exception:
                        continue
        except Exception:
            continue
    return rows  # ms -> (bid, ask, last), deduplicated


def spread_around(ticks: dict, signal_time: datetime, window_sec: int = 60):
    """Median spread in [signal-window, signal+window]. None if no ticks."""
    if not ticks:
        return None
    centre = int(signal_time.timestamp() * 1000)
    spreads = [ask - bid for ms, (bid, ask, _l) in ticks.items()
               if abs(ms - centre) <= window_sec * 1000 and ask > bid]
    return statistics.median(spreads) if spreads else None
