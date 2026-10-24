"""
=============================================================================
MT5 DATA CONNECTOR v3.0 — Dynamic SL/TP & Intelligent Analysis
- Quét nến + phát hiện setup SMC
- SL/TP linh động dựa trên cấu trúc thị trường (swing, OB, ATR)
- Backtest thông minh: nhiều mức TP, trailing, chốt lời từng phần
- Tự nhận diện symbol qua EA Bridge
=============================================================================
"""
import os
import sys
import time
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHARTS_DIR, COLORS

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


# =============================================================================
# DATA CLASSES
# =============================================================================
@dataclass
class CandleData:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


@dataclass
class SMCSetup:
    """Setup SMC — chứa toàn bộ thông tin với SL/TP linh động"""
    signal_id: str = ""
    timestamp: datetime = None
    symbol: str = ""
    timeframe: str = ""
    direction: str = "BUY"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    # TP linh động — nhiều mức
    tp1: float = 0.0          # TP bảo toàn (swing gần nhất)
    tp2: float = 0.0          # TP trung bình (OB hoặc cản tiếp)
    tp3: float = 0.0          # TP tham vọng (cấu trúc lớn)
    take_profit: float = 0.0  # TP chính (= tp2 mặc định)
    # Thông tin setup
    wick_percent: float = 0.0
    sweep_pips: float = 0.0
    atr: float = 0.0          # Average True Range
    rr_ratio: float = 0.0     # Risk:Reward thực tế
    session: str = ""
    has_fvg: bool = False
    has_ob: bool = False       # Order Block
    market_structure: str = "" # CHoCH / BOS / Range
    # AI
    ai_score: float = 0.0
    ai_analysis: str = ""
    chart_image_path: str = ""
    candles: List[CandleData] = field(default_factory=list)
    # Kết quả
    outcome: str = ""          # WIN / LOSS / PARTIAL / PENDING
    rr_achieved: float = 0.0
    tp_hit: str = ""           # TP1 / TP2 / TP3 / SL


# =============================================================================
# TIMEFRAME MAP
# =============================================================================
def _get_tf_map():
    if not MT5_AVAILABLE:
        return {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
                "H1": 60, "H4": 240, "D1": 1440}
    return {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }


def get_session(hour: int) -> str:
    if 6 <= hour < 14:
        return "Asian"
    elif 14 <= hour < 21:
        return "London"
    else:
        return "New York"


# =============================================================================
# MT5 CONNECTOR CLASS v3.0
# =============================================================================
class MT5Connector:
    """Kết nối MetaTrader 5 — Dynamic SL/TP, intelligent backtest"""

    def __init__(self, symbols=None, timeframe_str="M5", lookback=500):
        self.symbols = symbols or ["XAUUSD", "EURUSD", "GBPUSD"]
        self.timeframe_str = timeframe_str
        self.lookback = lookback
        self.connected = False
        self._tf_map = _get_tf_map()
        self._last_signal_time = {}

    @property
    def is_available(self):
        return MT5_AVAILABLE

    def connect(self) -> Tuple[bool, str]:
        if not MT5_AVAILABLE:
            return False, "⚠️ Package MetaTrader5 chưa được cài.\npip install MetaTrader5"
        try:
            if not mt5.initialize():
                err = mt5.last_error()
                return False, f"❌ Không kết nối được MT5: {err}"
            self.connected = True
            info = mt5.terminal_info()
            # Auto-detect symbols từ Market Watch
            self._auto_detect_symbols()
            return True, f"✅ Đã kết nối MT5 | Build: {info.build if info else 'N/A'}"
        except Exception as e:
            return False, f"❌ Lỗi kết nối: {str(e)}"

    def disconnect(self):
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
            self.connected = False

    def get_account_info(self) -> Optional[dict]:
        if not self.connected:
            return None
        try:
            info = mt5.account_info()
            if info:
                return {
                    "balance": info.balance,
                    "equity": info.equity,
                    "profit": info.profit,
                    "leverage": info.leverage,
                    "server": info.server,
                    "name": info.name,
                }
        except Exception:
            pass
        return None

    def _auto_detect_symbols(self):
        """Tự nhận diện symbols từ Market Watch hoặc file current_symbol.txt từ EA Bridge"""
        detected = []

        # 1. Đọc từ file current_symbol.txt do EA Bridge ghi ra khi gắn vào chart
        import glob
        from config import MT5_SIGNALS_DIR
        search_dirs = [MT5_SIGNALS_DIR]
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            mt_roaming = os.path.join(appdata, "MetaQuotes", "Terminal")
            if os.path.exists(mt_roaming):
                for tid in os.listdir(mt_roaming):
                    sig_path = os.path.join(mt_roaming, tid, "MQL5", "Files", "mt5_signals")
                    if os.path.exists(sig_path):
                        search_dirs.append(sig_path)

        for sdir in search_dirs:
            cur_file = os.path.join(sdir, "current_symbol.txt")
            if os.path.exists(cur_file):
                try:
                    with open(cur_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("symbol="):
                                sym = line.split("=", 1)[1].strip()
                                if sym and sym not in detected:
                                    detected.insert(0, sym)
                                    print(f"[MT5] Phát hiện symbol từ EA Bridge: {sym}")
                except Exception:
                    pass

        # 2. Quét từ MT5 API
        if self.connected and MT5_AVAILABLE:
            try:
                all_syms = mt5.symbols_get()
                if all_syms:
                    visible = [s.name for s in all_syms if s.visible]
                    if visible:
                        known_bases = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "GBPJPY",
                                       "EURJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF",
                                       "BTCUSD", "US30", "NAS100", "SPX500"]
                        for v in visible:
                            clean = v.upper().replace("C", "").replace("M", "").replace(".PRO", "").replace("_", "")
                            for base in known_bases:
                                if base in clean or clean.startswith(base[:6]):
                                    if v not in detected:
                                        detected.append(v)
                                    break
            except Exception as e:
                print(f"[MT5] Lỗi auto-detect: {e}")

        if detected:
            self.symbols = detected
            print(f"[MT5] Symbols danh sách: {detected}")

    def resolve_symbol(self, symbol: str) -> str:
        """Tự động khớp tên symbol với broker (hỗ trợ đuôi c, m, pro, etc.)"""
        if not self.connected or not MT5_AVAILABLE:
            return symbol
        info = mt5.symbol_info(symbol)
        if info:
            if not info.visible:
                mt5.symbol_select(symbol, True)
            return symbol

        all_syms = mt5.symbols_get()
        if all_syms:
            sym_upper = symbol.upper()
            for s in all_syms:
                if sym_upper == s.name.upper():
                    if not s.visible:
                        mt5.symbol_select(s.name, True)
                    return s.name
            # Fuzzy match
            sym_clean = sym_upper.replace(".PRO", "").replace("C", "").replace("M", "")
            for s in all_syms:
                s_clean = s.name.upper().replace(".PRO", "").replace("C", "").replace("M", "")
                if sym_clean == s_clean or s.name.upper().startswith(sym_clean):
                    if not s.visible:
                        mt5.symbol_select(s.name, True)
                    return s.name
        return symbol

    def get_candles(self, symbol: str, count: int = None) -> List[CandleData]:
        """Lấy N nến gần nhất từ MT5 (trực tiếp qua API hoặc qua file CSV của EA Bridge)"""
        count = count or self.lookback
        candles = []

        # 1. Thử qua MT5 Python API
        if self.connected and MT5_AVAILABLE:
            resolved_sym = self.resolve_symbol(symbol)
            tf = self._tf_map.get(self.timeframe_str, 5)
            try:
                rates = mt5.copy_rates_from_pos(resolved_sym, tf, 0, count)
                if rates is not None and len(rates) > 0:
                    for r in rates:
                        candles.append(CandleData(
                            time=datetime.fromtimestamp(r["time"]),
                            open=float(r["open"]),
                            high=float(r["high"]),
                            low=float(r["low"]),
                            close=float(r["close"]),
                            volume=int(r["tick_volume"]),
                        ))
                    return candles
            except Exception:
                pass

        # 2. Fallback: Đọc từ file CSV do EA Bridge xuất (history_<symbol>.csv)
        import glob
        from config import MT5_SIGNALS_DIR
        search_dirs = [MT5_SIGNALS_DIR]
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            mt_roaming = os.path.join(appdata, "MetaQuotes", "Terminal")
            if os.path.exists(mt_roaming):
                for tid in os.listdir(mt_roaming):
                    sig_path = os.path.join(mt_roaming, tid, "MQL5", "Files", "mt5_signals")
                    if os.path.exists(sig_path):
                        search_dirs.append(sig_path)

        clean_sym = symbol.upper().replace(".PRO", "").replace("C", "").replace("M", "")
        for sdir in search_dirs:
            pattern = os.path.join(sdir, f"history_*{clean_sym}*.csv")
            matches = glob.glob(pattern)
            if not matches:
                pattern = os.path.join(sdir, "history_*.csv")
                matches = glob.glob(pattern)

            for match_file in matches:
                try:
                    import pandas as pd
                    df = pd.read_csv(match_file)
                    if not df.empty and "open" in df.columns:
                        for _, row in df.tail(count).iterrows():
                            t_str = str(row.get("timestamp", ""))
                            try:
                                dt = datetime.strptime(t_str, "%Y.%m.%d %H:%M")
                            except Exception:
                                try:
                                    dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M")
                                except Exception:
                                    dt = datetime.now()
                            candles.append(CandleData(
                                time=dt,
                                open=float(row["open"]),
                                high=float(row["high"]),
                                low=float(row["low"]),
                                close=float(row["close"]),
                                volume=int(row.get("volume", 0)),
                            ))
                        if candles:
                            print(f"[MT5Connector] ✅ Đã nạp {len(candles)} nến từ file EA: {match_file}")
                            return candles
                except Exception as e:
                    print(f"[MT5Connector] Lỗi đọc CSV {match_file}: {e}")

        return candles

    # ─────────────────────────────────────────────────────────
    # TÍNH TOÁN CẤU TRÚC THỊ TRƯỜNG
    # ─────────────────────────────────────────────────────────
    def _calc_atr(self, candles: List[CandleData], period: int = 14) -> float:
        """Tính Average True Range — dùng cho SL/TP linh động"""
        if len(candles) < period + 1:
            return 0
        trs = []
        for i in range(1, len(candles)):
            h = candles[i].high
            l = candles[i].low
            pc = candles[i - 1].close
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)
        if len(trs) < period:
            return np.mean(trs) if trs else 0
        return np.mean(trs[-period:])

    def _find_swing_levels(self, candles: List[CandleData], lookback: int = 5) -> Tuple[list, list]:
        """Tìm các swing high/low — dùng cho TP linh động"""
        swing_highs = []
        swing_lows = []
        for i in range(lookback, len(candles) - lookback):
            # Swing High
            is_swing_high = all(candles[i].high >= candles[i + j].high for j in range(-lookback, lookback + 1) if j != 0)
            if is_swing_high:
                swing_highs.append((i, candles[i].high))
            # Swing Low
            is_swing_low = all(candles[i].low <= candles[i + j].low for j in range(-lookback, lookback + 1) if j != 0)
            if is_swing_low:
                swing_lows.append((i, candles[i].low))
        return swing_highs, swing_lows

    def _find_order_blocks(self, candles: List[CandleData], direction: str, start_idx: int) -> list:
        """Tìm Order Blocks (OB) gần nhất — vùng cản cho TP"""
        obs = []
        for i in range(max(2, start_idx - 50), start_idx):
            c = candles[i]
            prev = candles[i - 1]
            body = abs(c.close - c.open)
            full_range = c.high - c.low
            if full_range <= 0:
                continue
            body_pct = body / full_range * 100

            if direction == "BUY":
                # Bearish OB phía trên (cản TP)
                if c.close < c.open and body_pct > 60:
                    obs.append({"type": "bearish_ob", "price": c.open, "idx": i})
            else:
                # Bullish OB phía dưới (cản TP)
                if c.close > c.open and body_pct > 60:
                    obs.append({"type": "bullish_ob", "price": c.open, "idx": i})
        return obs

    def _detect_market_structure(self, candles: List[CandleData], idx: int) -> str:
        """Phát hiện cấu trúc thị trường: CHoCH, BOS, Range"""
        if idx < 30:
            return "Range"
        recent = candles[max(0, idx - 30):idx]
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]

        # Kiểm tra Higher Highs, Higher Lows (Uptrend)
        mid = len(highs) // 2
        first_half_high = max(highs[:mid]) if mid > 0 else 0
        second_half_high = max(highs[mid:]) if mid > 0 else 0
        first_half_low = min(lows[:mid]) if mid > 0 else 0
        second_half_low = min(lows[mid:]) if mid > 0 else 0

        if second_half_high > first_half_high and second_half_low > first_half_low:
            return "Uptrend"
        elif second_half_high < first_half_high and second_half_low < first_half_low:
            return "Downtrend"
        else:
            return "Range"

    def _calc_dynamic_sl_tp(self, candles: List[CandleData], target_idx: int,
                             direction: str, entry: float, sweep_low: float = 0,
                             sweep_high: float = 0) -> dict:
        """
        Tính SL/TP linh động dựa trên cấu trúc thị trường:
        - SL: Dưới/trên râu nến sweep + buffer ATR
        - TP1: Swing gần nhất (bảo toàn)
        - TP2: Order Block hoặc cản tiếp theo
        - TP3: Cấu trúc lớn hơn
        """
        target = candles[target_idx]
        atr = self._calc_atr(candles[:target_idx + 1], 14)
        if atr <= 0:
            atr = abs(target.high - target.low)

        swing_highs, swing_lows = self._find_swing_levels(candles[:target_idx], lookback=3)
        obs = self._find_order_blocks(candles, direction, target_idx)

        if direction == "BUY":
            # ─── SL: Dưới râu nến + buffer ATR ───
            sl = target.low - (atr * 0.3)
            risk = entry - sl
            if risk <= 0:
                sl = target.low - atr
                risk = entry - sl

            # ─── TP1: Swing high gần nhất phía trên entry ───
            tp1 = entry + risk * 1.5  # Fallback
            relevant_highs = [h for _, h in swing_highs if h > entry]
            if relevant_highs:
                tp1 = min(relevant_highs)  # Swing high gần nhất
                if tp1 - entry < risk * 0.8:  # Quá gần, lấy cái tiếp
                    higher = [h for h in relevant_highs if h > tp1]
                    tp1 = min(higher) if higher else entry + risk * 1.5

            # ─── TP2: Order Block hoặc swing xa hơn ───
            tp2 = entry + risk * 2.5  # Fallback
            bearish_obs = [ob["price"] for ob in obs if ob["type"] == "bearish_ob" and ob["price"] > tp1]
            if bearish_obs:
                tp2 = min(bearish_obs)
            else:
                further_highs = [h for h in relevant_highs if h > tp1]
                if further_highs:
                    tp2 = min(further_highs)

            # ─── TP3: Cấu trúc lớn — swing cao nhất hoặc fibo extension ───
            tp3 = entry + risk * 4.0  # Fallback
            if relevant_highs:
                tp3 = max(relevant_highs)
                if tp3 <= tp2:
                    tp3 = entry + risk * 4.0

        else:  # SELL
            # ─── SL: Trên râu nến + buffer ATR ───
            sl = target.high + (atr * 0.3)
            risk = sl - entry
            if risk <= 0:
                sl = target.high + atr
                risk = sl - entry

            # ─── TP1: Swing low gần nhất phía dưới entry ───
            tp1 = entry - risk * 1.5
            relevant_lows = [l for _, l in swing_lows if l < entry]
            if relevant_lows:
                tp1 = max(relevant_lows)
                if entry - tp1 < risk * 0.8:
                    lower = [l for l in relevant_lows if l < tp1]
                    tp1 = max(lower) if lower else entry - risk * 1.5

            # ─── TP2: Order Block hoặc swing xa hơn ───
            tp2 = entry - risk * 2.5
            bullish_obs = [ob["price"] for ob in obs if ob["type"] == "bullish_ob" and ob["price"] < tp1]
            if bullish_obs:
                tp2 = max(bullish_obs)
            else:
                further_lows = [l for l in relevant_lows if l < tp1]
                if further_lows:
                    tp2 = max(further_lows)

            # ─── TP3: Swing thấp nhất ───
            tp3 = entry - risk * 4.0
            if relevant_lows:
                tp3 = min(relevant_lows)
                if tp3 >= tp2:
                    tp3 = entry - risk * 4.0

        # Tính RR cho TP chính (tp2)
        rr = abs(tp2 - entry) / abs(risk) if risk != 0 else 0

        return {
            "sl": round(sl, 5),
            "tp1": round(tp1, 5),
            "tp2": round(tp2, 5),
            "tp3": round(tp3, 5),
            "atr": round(atr, 5),
            "risk": round(abs(risk), 5),
            "rr": round(rr, 1),
        }

    # ─────────────────────────────────────────────────────────
    # PHÁT HIỆN SETUP SMC (Liquidity Sweep + Pin Bar)
    # ─────────────────────────────────────────────────────────
    def detect_smc_setup(self, symbol: str, swing_lookback: int = 20,
                         min_wick_pct: float = 55.0) -> Optional[SMCSetup]:
        """
        Kiểm tra nến vừa đóng có phải setup SMC không:
        1. Quét thanh khoản (sweep low/high cũ)
        2. Pin Bar (râu dài)
        3. Dynamic SL/TP từ cấu trúc
        4. FVG + OB check
        """
        candles = self.get_candles(symbol, swing_lookback + 50)
        if len(candles) < swing_lookback + 5:
            return None

        target_idx = len(candles) - 2
        target = candles[target_idx]

        # Tránh spam cùng 1 nến
        sig_key = f"{symbol}_{target.time}"
        if sig_key in self._last_signal_time:
            return None

        # Tìm đáy/đỉnh trong N nến trước
        prior = candles[target_idx - swing_lookback:target_idx]
        if not prior:
            return None
        lowest_low = min(c.low for c in prior)
        highest_high = max(c.high for c in prior)

        total_range = target.high - target.low
        if total_range <= 0:
            return None

        point_mult = 10 if "JPY" in symbol.upper() else (1 if "XAU" in symbol.upper() else 10000)

        # ─── BUY SETUP ───
        is_buy_swept = target.low < lowest_low and target.close > lowest_low
        lower_wick = min(target.open, target.close) - target.low
        buy_wick_pct = (lower_wick / total_range) * 100.0
        is_buy_pinbar = target.close >= target.open and buy_wick_pct >= min_wick_pct

        # ─── SELL SETUP ───
        is_sell_swept = target.high > highest_high and target.close < highest_high
        upper_wick = target.high - max(target.open, target.close)
        sell_wick_pct = (upper_wick / total_range) * 100.0
        is_sell_pinbar = target.close <= target.open and sell_wick_pct >= min_wick_pct

        direction = None
        wick_pct = 0.0
        sweep_pips = 0.0
        entry = target.close

        if is_buy_swept and is_buy_pinbar:
            direction = "BUY"
            wick_pct = buy_wick_pct
            sweep_pips = abs(lowest_low - target.low) * point_mult
        elif is_sell_swept and is_sell_pinbar:
            direction = "SELL"
            wick_pct = sell_wick_pct
            sweep_pips = abs(target.high - highest_high) * point_mult
        else:
            return None

        # ─── Dynamic SL/TP ───
        levels = self._calc_dynamic_sl_tp(candles, target_idx, direction, entry)

        # ─── FVG Check ───
        has_fvg = False
        if target_idx >= 3:
            c_prev2 = candles[target_idx - 2]
            if direction == "BUY" and target.low > c_prev2.high:
                has_fvg = True
            elif direction == "SELL" and target.high < c_prev2.low:
                has_fvg = True

        # ─── OB Check ───
        obs = self._find_order_blocks(candles, direction, target_idx)
        has_ob = len(obs) > 0

        # ─── Market Structure ───
        structure = self._detect_market_structure(candles, target_idx)

        # ─── Session ───
        session = get_session(target.time.hour)

        # Đánh dấu đã xử lý
        self._last_signal_time[sig_key] = True
        sig_id = f"{symbol}_{target.time.strftime('%Y%m%d_%H%M')}"

        return SMCSetup(
            signal_id=sig_id,
            timestamp=target.time,
            symbol=symbol,
            timeframe=self.timeframe_str,
            direction=direction,
            entry_price=round(entry, 5),
            stop_loss=levels["sl"],
            tp1=levels["tp1"],
            tp2=levels["tp2"],
            tp3=levels["tp3"],
            take_profit=levels["tp2"],  # TP chính = TP2
            wick_percent=round(wick_pct, 1),
            sweep_pips=round(sweep_pips, 1),
            atr=levels["atr"],
            rr_ratio=levels["rr"],
            session=session,
            has_fvg=has_fvg,
            has_ob=has_ob,
            market_structure=structure,
            candles=candles[-60:] if len(candles) >= 60 else candles,
        )

    # ─────────────────────────────────────────────────────────
    # BACKTEST THÔNG MINH — Dynamic SL/TP + Trailing
    # ─────────────────────────────────────────────────────────
    def scan_historical_setups(self, symbol: str, swing_lookback: int = 20,
                                min_wick_pct: float = 55.0, max_candles: int = None) -> list:
        """
        Quét lịch sử 2 tháng — tìm setup SMC với SL/TP linh động.
        Kiểm tra outcome thông minh: trailing SL, nhiều mức TP.
        """
        count = max_candles or self.lookback
        all_candles = self.get_candles(symbol, count)
        if len(all_candles) < swing_lookback + 30:
            return []

        point_mult = 10 if "JPY" in symbol.upper() else (1 if "XAU" in symbol.upper() else 10000)
        setups = []

        for i in range(swing_lookback + 2, len(all_candles) - 30):
            target = all_candles[i]
            prior = all_candles[i - swing_lookback:i]

            lowest_low = min(c.low for c in prior)
            highest_high = max(c.high for c in prior)

            total_range = target.high - target.low
            if total_range <= 0:
                continue

            # BUY check
            is_buy_swept = target.low < lowest_low and target.close > lowest_low
            lower_wick = min(target.open, target.close) - target.low
            buy_wick_pct = (lower_wick / total_range) * 100.0
            is_buy_pinbar = target.close >= target.open and buy_wick_pct >= min_wick_pct

            # SELL check
            is_sell_swept = target.high > highest_high and target.close < highest_high
            upper_wick = target.high - max(target.open, target.close)
            sell_wick_pct = (upper_wick / total_range) * 100.0
            is_sell_pinbar = target.close <= target.open and sell_wick_pct >= min_wick_pct

            direction = None
            wick_pct = 0.0
            sweep_pips = 0.0
            entry = target.close

            if is_buy_swept and is_buy_pinbar:
                direction = "BUY"
                wick_pct = buy_wick_pct
                sweep_pips = abs(lowest_low - target.low) * point_mult
            elif is_sell_swept and is_sell_pinbar:
                direction = "SELL"
                wick_pct = sell_wick_pct
                sweep_pips = abs(target.high - highest_high) * point_mult
            else:
                continue

            # ─── Dynamic SL/TP ───
            levels = self._calc_dynamic_sl_tp(all_candles, i, direction, entry)
            sl = levels["sl"]
            tp1 = levels["tp1"]
            tp2 = levels["tp2"]
            tp3 = levels["tp3"]
            atr_val = levels["atr"]

            # ─── Kiểm tra outcome thông minh từ nến tương lai ───
            future = all_candles[i + 1:min(i + 60, len(all_candles))]
            if not future:
                continue

            outcome, rr_achieved, tp_hit = self._evaluate_outcome_smart(
                direction, entry, sl, tp1, tp2, tp3, future
            )

            # Market structure & OB
            structure = self._detect_market_structure(all_candles, i)
            has_fvg = False
            if i >= 3:
                c_prev2 = all_candles[i - 2]
                if direction == "BUY" and target.low > c_prev2.high:
                    has_fvg = True
                elif direction == "SELL" and target.high < c_prev2.low:
                    has_fvg = True

            obs = self._find_order_blocks(all_candles, direction, i)
            session = get_session(target.time.hour)

            clean_sym = symbol
            for suffix in ["c", "m", ".pro", ".raw", ".ecn"]:
                clean_sym = clean_sym.replace(suffix, "").replace(suffix.upper(), "")

            setups.append({
                "trade_id": f"BT_{clean_sym}_{target.time.strftime('%Y%m%d_%H%M')}",
                "timestamp": target.time.strftime("%Y-%m-%d %H:%M"),
                "symbol": clean_sym,
                "timeframe": self.timeframe_str,
                "session": session,
                "wick_percent": round(wick_pct, 1),
                "sweep_pips": round(sweep_pips, 1),
                "volume_ratio": round(target.volume / max(1, np.mean([c.volume for c in prior[-5:]])), 2),
                "has_fvg": has_fvg,
                "direction": direction,
                "entry_price": round(entry, 5),
                "stop_loss": round(sl, 5),
                "take_profit": round(tp2, 5),
                "tp1": round(tp1, 5),
                "tp2": round(tp2, 5),
                "tp3": round(tp3, 5),
                "atr": round(atr_val, 5),
                "rr_target": round(levels["rr"], 1),
                "market_structure": structure,
                "has_ob": len(obs) > 0,
                "outcome": outcome,
                "rr_achieved": round(rr_achieved, 2),
                "tp_hit": tp_hit,
                "ai_score": 0.0,
                "ai_analysis": "",
                "image_path": "",
                "notes": f"Backtest | {structure} | {'FVG' if has_fvg else ''} {'OB' if obs else ''}"
            })

        return setups

    def _evaluate_outcome_smart(self, direction: str, entry: float, sl: float,
                                  tp1: float, tp2: float, tp3: float,
                                  future: List[CandleData]) -> Tuple[str, float, str]:
        """
        Đánh giá outcome thông minh:
        - Nếu hit TP1 → trailing SL lên breakeven → check TP2, TP3
        - Nếu hit SL trước → LOSS
        - Trả về: (outcome, rr_achieved, tp_hit)
        """
        risk = abs(entry - sl)
        if risk <= 0:
            return "PENDING", 0, ""

        trailing_sl = sl  # SL ban đầu
        tp1_hit = False

        for candle in future:
            if direction == "BUY":
                # Check SL trước
                if candle.low <= trailing_sl:
                    if tp1_hit:
                        # Đã hit TP1, trailing SL = breakeven → PARTIAL WIN
                        rr = abs(tp1 - entry) / risk
                        return "PARTIAL", round(rr, 2), "TP1+Trail"
                    else:
                        return "LOSS", -1.0, "SL"

                # Check TP3 (max)
                if candle.high >= tp3:
                    rr = abs(tp3 - entry) / risk
                    return "WIN", round(rr, 2), "TP3"

                # Check TP2
                if candle.high >= tp2:
                    rr = abs(tp2 - entry) / risk
                    return "WIN", round(rr, 2), "TP2"

                # Check TP1 → trailing
                if candle.high >= tp1 and not tp1_hit:
                    tp1_hit = True
                    trailing_sl = entry  # Move SL to breakeven

            else:  # SELL
                # Check SL trước
                if candle.high >= trailing_sl:
                    if tp1_hit:
                        rr = abs(entry - tp1) / risk
                        return "PARTIAL", round(rr, 2), "TP1+Trail"
                    else:
                        return "LOSS", -1.0, "SL"

                # Check TP3
                if candle.low <= tp3:
                    rr = abs(entry - tp3) / risk
                    return "WIN", round(rr, 2), "TP3"

                # Check TP2
                if candle.low <= tp2:
                    rr = abs(entry - tp2) / risk
                    return "WIN", round(rr, 2), "TP2"

                # Check TP1 → trailing
                if candle.low <= tp1 and not tp1_hit:
                    tp1_hit = True
                    trailing_sl = entry

        if tp1_hit:
            rr = abs(tp1 - entry) / risk if direction == "BUY" else abs(entry - tp1) / risk
            return "PARTIAL", round(rr, 2), "TP1"

        return "PENDING", 0, ""

    def backtest_historical_range(self, symbols=None, lookback_bars: int = 15000,
                                   swing_lookback: int = 20, min_wick_pct: float = 55.0) -> list:
        """Quét toàn diện lịch sử 2 tháng cho tất cả symbol"""
        symbols = symbols or self.symbols
        all_results = []
        for sym in symbols:
            resolved = self.resolve_symbol(sym)
            results = self.scan_historical_setups(
                resolved,
                swing_lookback=swing_lookback,
                min_wick_pct=min_wick_pct,
                max_candles=lookback_bars
            )
            all_results.extend(results)

        all_results.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_results

    # ─────────────────────────────────────────────────────────
    # RENDER CHART — Vẽ candlestick với Entry/SL/TP1/TP2/TP3
    # ─────────────────────────────────────────────────────────
    def render_chart(self, setup: SMCSetup, save_dir: str = None) -> str:
        """Render chart pro với nhiều mức TP"""
        candles = setup.candles
        if not candles or len(candles) < 5:
            return ""

        save_dir = save_dir or CHARTS_DIR
        os.makedirs(save_dir, exist_ok=True)

        fig, ax = plt.subplots(figsize=(14, 7))
        fig.patch.set_facecolor("#131722")
        ax.set_facecolor("#131722")

        n = len(candles)
        for i, c in enumerate(candles):
            is_bull = c.close >= c.open
            color = "#26a69a" if is_bull else "#ef5350"
            body_bot = min(c.open, c.close)
            body_h = abs(c.close - c.open) or (c.high - c.low) * 0.01

            ax.plot([i, i], [max(c.open, c.close), c.high],
                    color=color, linewidth=1.2, solid_capstyle="round")
            ax.plot([i, i], [c.low, body_bot],
                    color=color, linewidth=1.2, solid_capstyle="round")
            rect = Rectangle((i - 0.35, body_bot), 0.7, body_h,
                              facecolor=color, edgecolor=color, linewidth=0.8)
            ax.add_patch(rect)

        pad = n * 0.02

        # Entry
        if setup.entry_price > 0:
            ax.axhline(y=setup.entry_price, color="#2962ff", linestyle="--",
                        linewidth=1.8, alpha=0.85, xmin=0.02, xmax=0.98)
            ax.text(n + pad, setup.entry_price,
                    f"  ENTRY  {setup.entry_price}",
                    color="#2962ff", fontsize=10, fontweight="bold",
                    va="center", fontfamily="monospace",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#2962ff",
                              edgecolor="none", alpha=0.15))

        # SL
        if setup.stop_loss > 0:
            ax.axhline(y=setup.stop_loss, color="#ef5350", linestyle="--",
                        linewidth=1.8, alpha=0.85, xmin=0.02, xmax=0.98)
            ax.text(n + pad, setup.stop_loss,
                    f"  SL  {setup.stop_loss}",
                    color="#ef5350", fontsize=10, fontweight="bold",
                    va="center", fontfamily="monospace",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#ef5350",
                              edgecolor="none", alpha=0.15))

        # TP1 - Bảo toàn
        if setup.tp1 > 0:
            ax.axhline(y=setup.tp1, color="#f7931a", linestyle="-.",
                        linewidth=1.2, alpha=0.6, xmin=0.02, xmax=0.98)
            ax.text(n + pad, setup.tp1,
                    f"  TP1  {setup.tp1}",
                    color="#f7931a", fontsize=9, fontweight="bold",
                    va="center", fontfamily="monospace",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#f7931a",
                              edgecolor="none", alpha=0.1))

        # TP2 - Chính
        if setup.tp2 > 0:
            ax.axhline(y=setup.tp2, color="#26a69a", linestyle="--",
                        linewidth=1.8, alpha=0.85, xmin=0.02, xmax=0.98)
            ax.text(n + pad, setup.tp2,
                    f"  TP2  {setup.tp2}",
                    color="#26a69a", fontsize=10, fontweight="bold",
                    va="center", fontfamily="monospace",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#26a69a",
                              edgecolor="none", alpha=0.15))

        # TP3 - Tham vọng
        if setup.tp3 > 0:
            ax.axhline(y=setup.tp3, color="#00e5ff", linestyle="-.",
                        linewidth=1.2, alpha=0.5, xmin=0.02, xmax=0.98)
            ax.text(n + pad, setup.tp3,
                    f"  TP3  {setup.tp3}",
                    color="#00e5ff", fontsize=9, fontweight="bold",
                    va="center", fontfamily="monospace",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#00e5ff",
                              edgecolor="none", alpha=0.1))

        # Risk/Reward zones
        if setup.entry_price > 0 and setup.stop_loss > 0:
            ax.axhspan(min(setup.stop_loss, setup.entry_price),
                       max(setup.stop_loss, setup.entry_price),
                       alpha=0.06, color="#ef5350")
        if setup.entry_price > 0 and setup.tp2 > 0:
            ax.axhspan(min(setup.entry_price, setup.tp2),
                       max(setup.entry_price, setup.tp2),
                       alpha=0.06, color="#26a69a")

        # Title
        title = f"{setup.symbol}  {setup.timeframe}  |  {setup.direction}  |  "
        title += f"Wick: {setup.wick_percent}%  |  {setup.session}"
        if setup.rr_ratio > 0:
            title += f"  |  R:R ≈ 1:{setup.rr_ratio}"
        if setup.market_structure:
            title += f"  |  {setup.market_structure}"
        ax.set_title(title, color="#d1d4dc", fontsize=12, fontweight="bold",
                     pad=15, fontfamily="monospace")

        ax.tick_params(colors="#787b86", labelsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("#2a2e39")
        ax.spines["left"].set_color("#2a2e39")
        ax.grid(True, alpha=0.08, color="#363a45", linestyle="-")
        ax.set_xlim(-1, n + n * 0.18)

        all_prices = [c.low for c in candles] + [c.high for c in candles]
        for price in [setup.stop_loss, setup.tp1, setup.tp2, setup.tp3]:
            if price > 0:
                all_prices.append(price)
        y_pad = (max(all_prices) - min(all_prices)) * 0.1
        ax.set_ylim(min(all_prices) - y_pad, max(all_prices) + y_pad)

        plt.tight_layout()

        filename = f"{setup.symbol}_{setup.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = os.path.join(save_dir, filename)
        plt.savefig(save_path, dpi=150, facecolor="#131722", bbox_inches="tight")
        plt.close()

        setup.chart_image_path = save_path
        return save_path
