"""
=============================================================================
LOG VIEW — Nhật ký kinh nghiệm giao dịch
Hiển thị toàn bộ trade history dạng bảng scrollable
=============================================================================
"""
import os
import sys
import customtkinter as ctk
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS


class LogView(ctk.CTkFrame):
    """Tab nhật ký kinh nghiệm — hiển thị trade history chi tiết"""

    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # ─── Header ───
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", padx=20, pady=(15, 5))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="📋  Experience Log",
            font=("Segoe UI", 22, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        self.count_label = ctk.CTkLabel(
            header, text="0 trades",
            font=("Segoe UI", 12),
            text_color=COLORS["text_muted"],
        )
        self.count_label.pack(side="left", padx=15)

        # Backtest 2 Tháng button
        self.btn_backtest = ctk.CTkButton(
            header, text="⚡ Backtest 2 Tháng MT5", font=("Segoe UI", 11, "bold"),
            width=165, height=30, corner_radius=6,
            fg_color=COLORS["accent_blue"],
            hover_color="#1a47b8",
            text_color="#ffffff",
            command=self._run_backtest,
        )
        self.btn_backtest.pack(side="right", padx=5)

        # Export button
        ctk.CTkButton(
            header, text="📤 Export CSV", font=("Segoe UI", 11),
            width=110, height=30, corner_radius=6,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self._export_csv,
        ).pack(side="right", padx=5)

        # Refresh
        ctk.CTkButton(
            header, text="🔄 Refresh", font=("Segoe UI", 11),
            width=90, height=30, corner_radius=6,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self.refresh,
        ).pack(side="right", padx=5)

        # ─── Filter Row ───
        filter_row = ctk.CTkFrame(self, fg_color="transparent", height=40)
        filter_row.pack(fill="x", padx=20, pady=(5, 5))
        filter_row.pack_propagate(False)

        ctk.CTkLabel(filter_row, text="Filter:", font=("Segoe UI", 11),
                      text_color=COLORS["text_secondary"]).pack(side="left")

        self.filter_outcome = ctk.CTkSegmentedButton(
            filter_row, values=["All", "WIN", "LOSS"],
            font=("Segoe UI", 11),
            selected_color=COLORS["accent_blue"],
            selected_hover_color="#1a47b8",
            unselected_color=COLORS["bg_card"],
            unselected_hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self._on_filter_change,
        )
        self.filter_outcome.pack(side="left", padx=10)
        self.filter_outcome.set("All")

        self.filter_symbol = ctk.CTkSegmentedButton(
            filter_row, values=["All", "XAUUSD", "EURUSD", "GBPUSD"],
            font=("Segoe UI", 11),
            selected_color=COLORS["accent_blue"],
            selected_hover_color="#1a47b8",
            unselected_color=COLORS["bg_card"],
            unselected_hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self._on_filter_change,
        )
        self.filter_symbol.pack(side="left", padx=10)
        self.filter_symbol.set("All")

        # ─── Table Header ───
        table_header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"],
                                     corner_radius=8, height=35)
        table_header.pack(fill="x", padx=20, pady=(5, 0))
        table_header.pack_propagate(False)

        columns = [
            ("ID", 60), ("Time", 130), ("Symbol", 80), ("Session", 80),
            ("Dir", 50), ("Entry", 90), ("SL", 90), ("TP", 90),
            ("Result", 60), ("R:R", 60), ("Wick%", 55), ("Score", 55),
        ]

        for col_name, width in columns:
            ctk.CTkLabel(
                table_header, text=col_name,
                font=("Segoe UI", 10, "bold"),
                text_color=COLORS["text_muted"],
                width=width,
                anchor="center",
            ).pack(side="left", padx=2)

        # ─── Scrollable Table Body ───
        self.table_body = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["border_light"],
        )
        self.table_body.pack(fill="both", expand=True, padx=20, pady=(2, 15))

        self.row_widgets = []

    def refresh(self):
        """Reload data từ database"""
        self._load_data()

    def _load_data(self, outcome_filter="All", symbol_filter="All"):
        # Clear existing rows
        for widget in self.row_widgets:
            widget.destroy()
        self.row_widgets.clear()

        if not self.app or not self.app.trade_logger:
            return

        df = self.app.trade_logger.get_all_trades()
        if df.empty:
            self.count_label.configure(text="0 trades")
            return

        # Apply filters
        if outcome_filter != "All":
            df = df[df["outcome"] == outcome_filter]
        if symbol_filter != "All":
            df = df[df["symbol"] == symbol_filter]

        self.count_label.configure(text=f"{len(df)} trades")

        # Show latest first
        df = df.iloc[::-1]

        for _, row in df.iterrows():
            self._add_table_row(row)

    def _add_table_row(self, row):
        """Thêm 1 row vào table"""
        outcome_str = str(row.get("outcome", "")).upper()
        row_color = COLORS["bg_card"] if len(self.row_widgets) % 2 == 0 else COLORS["bg_dark"]

        frame = ctk.CTkFrame(self.table_body, fg_color=row_color,
                              corner_radius=6, height=32)
        frame.pack(fill="x", pady=1)
        frame.pack_propagate(False)

        # Columns matching header
        tid = str(row.get("trade_id", ""))
        if tid.endswith(".0"):
            tid = tid[:-2]
        values = [
            (tid[:12], 60),
            (str(row.get("timestamp", ""))[:16], 130),
            (str(row.get("symbol", "")), 80),
            (str(row.get("session", "")), 80),
            (str(row.get("direction", "BUY")), 50),
            (str(row.get("entry_price", 0)), 90),
            (str(row.get("stop_loss", 0)), 90),
            (str(row.get("take_profit", 0)), 90),
            (outcome_str, 60),
            (str(row.get("rr_achieved", 0)), 60),
            (str(row.get("wick_percent", 0)), 55),
            (str(row.get("ai_score", 0)), 55),
        ]

        for i, (val, width) in enumerate(values):
            color = COLORS["text_secondary"]
            if i == 8:  # Outcome column
                if outcome_str == "WIN":
                    color = COLORS["accent_green"]
                elif outcome_str == "PARTIAL":
                    color = COLORS["accent_yellow"]
                elif outcome_str == "LOSS":
                    color = COLORS["accent_red"]
                else:
                    color = COLORS["text_muted"]
            elif i == 9:  # R:R column
                try:
                    rr_val = float(val)
                    color = COLORS["accent_green"] if rr_val > 0 else (COLORS["accent_red"] if rr_val < 0 else COLORS["text_muted"])
                except (ValueError, TypeError):
                    pass

            ctk.CTkLabel(
                frame, text=val,
                font=("Consolas", 10),
                text_color=color,
                width=width,
                anchor="center",
            ).pack(side="left", padx=2)

        self.row_widgets.append(frame)

    def _on_filter_change(self, _value=None):
        outcome = self.filter_outcome.get()
        symbol = self.filter_symbol.get()
        self._load_data(outcome, symbol)

    def _export_csv(self):
        """Mở thư mục chứa file CSV"""
        if self.app and self.app.trade_logger:
            csv_path = self.app.trade_logger.csv_path
            folder = os.path.dirname(csv_path)
            try:
                os.startfile(folder)
                self.app.set_status(f"📤 Đã mở thư mục: {folder}")
            except Exception:
                self.app.set_status(f"📤 File CSV: {csv_path}")

    def _run_backtest(self):
        if not self.app or not self.app.mt5:
            return
        if not self.app.mt5.connected:
            self.app.set_status("⚠️ MT5 chưa kết nối. Đang thử kết nối...")
            self.app.mt5.connect()
            if not self.app.mt5.connected:
                self.app.set_status("❌ Không kết nối được MT5 để quét lịch sử!")
                return

        self.btn_backtest.configure(state="disabled", text="⏳ Đang quét 2 tháng...")
        self.app.set_status("⏳ Đang quét 15.000 nến M5 (2 tháng) từ MT5...")

        def worker():
            try:
                import threading
                symbols = self.app.settings.get("mt5_symbols", ["XAUUSD", "EURUSD", "GBPUSD"]) if self.app.settings else ["XAUUSD"]
                setups = self.app.mt5.backtest_historical_range(symbols=symbols, lookback_bars=15000)
                if setups and self.app.trade_logger:
                    for s in setups:
                        self.app.trade_logger.log_trade(s)

                wins = len([s for s in setups if s.get("outcome") == "WIN"])
                losses = len([s for s in setups if s.get("outcome") == "LOSS"])
                total = len(setups)
                wr = round(wins / max(1, wins + losses) * 100, 1)

                msg = f"✅ Hoàn tất Backtest 2 tháng: {total} lệnh (Winrate: {wr}%, Thắng: {wins}, Thua: {losses})"
                self.after(0, lambda: self._on_backtest_done(msg))
            except Exception as e:
                self.after(0, lambda: self._on_backtest_done(f"❌ Lỗi Backtest: {e}"))

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _on_backtest_done(self, msg):
        self.btn_backtest.configure(state="normal", text="⚡ Backtest 2 Tháng MT5")
        if self.app:
            self.app.set_status(msg)
        self.refresh()
