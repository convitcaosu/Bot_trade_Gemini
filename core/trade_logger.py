"""
=============================================================================
TRADE LOGGER v3.0 — Database kinh nghiệm giao dịch & Backtest
- Hỗ trợ Dynamic SL/TP: TP1, TP2, TP3, trailing
- Lưu trữ mọi setup thực chiến & backtest
- Thread-safe, hỗ trợ string / int trade_id
=============================================================================
"""
import os
import shutil
import random
import threading
import pandas as pd
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CSV_FILE

COLUMNS = [
    "trade_id", "timestamp", "symbol", "timeframe", "session",
    "wick_percent", "sweep_pips", "volume_ratio", "has_fvg",
    "direction", "entry_price", "stop_loss", "take_profit",
    "tp1", "tp2", "tp3", "atr", "market_structure", "has_ob",
    "outcome", "rr_achieved", "tp_hit", "ai_score", "ai_analysis",
    "image_path", "notes", "method_id", "ai_reason"
]


class TradeLogger:
    """Quản lý database CSV — nhật ký kinh nghiệm và kết quả backtest"""

    def __init__(self, csv_path=None):
        self.csv_path = csv_path or CSV_FILE
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            if not os.path.exists(self.csv_path):
                df = pd.DataFrame(columns=COLUMNS)
                df.to_csv(self.csv_path, index=False, encoding="utf-8")
            else:
                # Kiểm tra và tự nâng cấp cột nếu file cũ thiếu cột v3.0
                try:
                    df = pd.read_csv(self.csv_path)
                    missing = [c for c in COLUMNS if c not in df.columns]
                    if missing:
                        for c in missing:
                            df[c] = ""
                        df.to_csv(self.csv_path, index=False, encoding="utf-8")
                except Exception:
                    pass

    def log_trade(self, data: dict):
        """Ghi 1 lệnh mới vào database — APPEND, không ghi đè"""
        with self._lock:
            self._init_db_unlocked()
            try:
                df = pd.read_csv(self.csv_path)
            except Exception:
                df = pd.DataFrame(columns=COLUMNS)

            # Đảm bảo có trade_id
            if "trade_id" not in data or pd.isna(data.get("trade_id")) or not data.get("trade_id"):
                data["trade_id"] = self._get_next_id_unlocked(df)

            # Chuẩn hoá các trường
            row = {}
            for col in COLUMNS:
                row[col] = data.get(col, "")

            new_row = pd.DataFrame([row])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(self.csv_path, index=False, encoding="utf-8")
            return data["trade_id"]

    def log_trades_batch(self, trades: list) -> int:
        """Ghi hàng loạt lệnh (dùng cho Backtest) an toàn, nhanh chóng"""
        if not trades:
            return 0
        with self._lock:
            self._init_db_unlocked()
            try:
                df = pd.read_csv(self.csv_path)
            except Exception:
                df = pd.DataFrame(columns=COLUMNS)

            existing_ids = set(df["trade_id"].astype(str)) if not df.empty and "trade_id" in df.columns else set()
            new_rows = []
            for t in trades:
                tid = str(t.get("trade_id", ""))
                if tid and tid in existing_ids:
                    continue  # Tránh trùng lặp
                row = {}
                for col in COLUMNS:
                    row[col] = t.get(col, "")
                new_rows.append(row)
                if tid:
                    existing_ids.add(tid)

            if new_rows:
                new_df = pd.DataFrame(new_rows)
                df = pd.concat([df, new_df], ignore_index=True)
                df.to_csv(self.csv_path, index=False, encoding="utf-8")
                return len(new_rows)
            return 0

    def get_all_trades(self) -> pd.DataFrame:
        with self._lock:
            self._init_db_unlocked()
            try:
                return pd.read_csv(self.csv_path)
            except Exception:
                return pd.DataFrame(columns=COLUMNS)

    def get_trade_count(self) -> int:
        return len(self.get_all_trades())

    def _get_next_id_unlocked(self, df: pd.DataFrame) -> int:
        if df.empty or "trade_id" not in df.columns:
            return 1001
        numeric_ids = []
        for x in df["trade_id"]:
            try:
                numeric_ids.append(int(x))
            except (ValueError, TypeError):
                pass
        return max(numeric_ids) + 1 if numeric_ids else 1001

    def get_next_id(self) -> int:
        with self._lock:
            df = self.get_all_trades()
            return self._get_next_id_unlocked(df)

    def update_outcome(self, trade_id=None, outcome="WIN", rr=None):
        """Cập nhật kết quả lệnh: WIN, LOSS, PARTIAL. Nếu trade_id=None thì update lệnh pending gần nhất."""
        with self._lock:
            self._init_db_unlocked()
            try:
                df = pd.read_csv(self.csv_path)
            except Exception:
                return False

            if df.empty:
                return False

            if trade_id is None:
                # Tìm lệnh PENDING gần nhất
                pending_mask = df["outcome"].astype(str).str.upper() == "PENDING"
                if pending_mask.any():
                    idx = df[pending_mask].index[-1]
                    df.loc[idx, "outcome"] = outcome
                    if rr is not None:
                        df.loc[idx, "rr_achieved"] = rr
                    df.to_csv(self.csv_path, index=False, encoding="utf-8")
                    return True
                # Nếu không có pending, update dòng cuối cùng
                idx = df.index[-1]
                df.loc[idx, "outcome"] = outcome
                if rr is not None:
                    df.loc[idx, "rr_achieved"] = rr
                df.to_csv(self.csv_path, index=False, encoding="utf-8")
                return True

            # Tìm theo trade_id
            mask = df["trade_id"].astype(str) == str(trade_id)
            if not mask.any():
                return False
            df.loc[mask, "outcome"] = outcome
            if rr is not None:
                df.loc[mask, "rr_achieved"] = rr
            df.to_csv(self.csv_path, index=False, encoding="utf-8")
            return True

    # Alias tương thích với các module khác
    log_outcome = update_outcome

    def get_recent_trades(self, n=20) -> pd.DataFrame:
        df = self.get_all_trades()
        return df.tail(n)

    def get_stats_summary(self) -> dict:
        """Tính toán thống kê tổng quan với cả WIN và PARTIAL"""
        df = self.get_all_trades()
        if df.empty:
            return {"total": 0, "wins": 0, "losses": 0, "winrate": 0,
                    "avg_rr": 0, "total_rr": 0, "best_session": "N/A"}

        total = len(df)
        wins = len(df[df["outcome"].isin(["WIN", "PARTIAL"])])
        losses = len(df[df["outcome"] == "LOSS"])
        winrate = (wins / max(1, wins + losses) * 100) if (wins + losses) > 0 else 0
        
        # RR trung bình của các lệnh thắng
        win_df = df[df["outcome"].isin(["WIN", "PARTIAL"])]
        avg_rr = pd.to_numeric(win_df["rr_achieved"], errors="coerce").mean() if not win_df.empty else 0
        total_rr = pd.to_numeric(df["rr_achieved"], errors="coerce").fillna(0).sum()

        best_session = "London"
        if "session" in df.columns and not df["session"].isna().all():
            session_wr = df.groupby("session")["outcome"].apply(
                lambda x: (x.isin(["WIN", "PARTIAL"])).mean() * 100
            )
            if not session_wr.empty:
                best_session = session_wr.idxmax()

        return {
            "total": total, "wins": wins, "losses": losses,
            "winrate": round(winrate, 1),
            "avg_rr": round(float(avg_rr) if not pd.isna(avg_rr) else 0.0, 1),
            "total_rr": round(float(total_rr), 1),
            "best_session": best_session,
        }

    def backup(self) -> str:
        """Backup database trước khi thao tác nguy hiểm"""
        if os.path.exists(self.csv_path):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.csv_path.replace(".csv", f"_backup_{ts}.csv")
            shutil.copy2(self.csv_path, backup_path)
            return backup_path
        return ""

    def generate_sample_data(self, count=30):
        """Tạo dữ liệu mẫu đa dạng cho demo"""
        self.backup()
        start_id = self.get_next_id()
        sessions = ["London", "New York", "Asian"]
        symbols = ["XAUUSD", "EURUSD", "GBPUSD"]
        now = datetime.now()

        samples = []
        for i in range(count):
            sess = random.choices(sessions, weights=[0.45, 0.40, 0.15])[0]
            wick = random.randint(45, 85)
            is_fvg = random.choice([True, False])
            is_ob = random.choice([True, False])

            win_prob = 0.40
            if wick >= 60:
                win_prob += 0.25
            if sess in ["London", "New York"]:
                win_prob += 0.15
            if is_fvg or is_ob:
                win_prob += 0.10

            is_win = random.random() < win_prob
            outcome = random.choice(["WIN", "PARTIAL"]) if is_win else "LOSS"
            rr = round(random.uniform(2.0, 4.5), 1) if outcome == "WIN" else (
                round(random.uniform(1.0, 1.8), 1) if outcome == "PARTIAL" else -1.0
            )
            symbol = random.choice(symbols)
            dir_choice = random.choice(["BUY", "SELL"])
            base_price = 2650.0 if symbol == "XAUUSD" else (1.0850 if symbol == "EURUSD" else 1.2950)
            entry = round(base_price + random.uniform(-10, 10), 4 if "XAU" not in symbol else 2)
            sl_dist = 4.0 if "XAU" in symbol else 0.0025
            sl = entry - sl_dist if dir_choice == "BUY" else entry + sl_dist
            tp1 = entry + sl_dist * 1.5 if dir_choice == "BUY" else entry - sl_dist * 1.5
            tp2 = entry + sl_dist * 3.0 if dir_choice == "BUY" else entry - sl_dist * 3.0
            tp3 = entry + sl_dist * 4.5 if dir_choice == "BUY" else entry - sl_dist * 4.5

            t_date = now - timedelta(days=random.randint(1, 55), hours=random.randint(1, 23))

            samples.append({
                "trade_id": start_id + i,
                "timestamp": t_date.strftime("%Y-%m-%d %H:%M"),
                "symbol": symbol,
                "timeframe": "M5",
                "session": sess,
                "wick_percent": wick,
                "sweep_pips": round(random.uniform(5, 25), 1),
                "volume_ratio": round(random.uniform(1.2, 3.0), 2),
                "has_fvg": is_fvg,
                "has_ob": is_ob,
                "market_structure": random.choice(["Uptrend", "Downtrend", "Range"]),
                "direction": dir_choice,
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp2,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "outcome": outcome,
                "rr_achieved": rr,
                "tp_hit": "TP2" if outcome == "WIN" else ("TP1+Trail" if outcome == "PARTIAL" else "SL"),
                "ai_score": round(random.uniform(6.5, 9.5), 1),
                "ai_analysis": f"Setup {sess} với râu nến {wick}%. Cấu trúc thuận xu hướng.",
                "notes": "Dữ liệu mẫu",
            })

        return self.log_trades_batch(samples)

    def _init_db_unlocked(self):
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=COLUMNS)
            df.to_csv(self.csv_path, index=False, encoding="utf-8")
