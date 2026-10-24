"""
=============================================================================
BACKTEST VIEW v3.0 — Phân tích lịch sử 2 tháng & Thẩm định phong độ AI
- Quét 15.000 nến MT5 (2 tháng) cho bất kỳ symbol nào (XAUUSD, Cent, Forex, etc.)
- Trực quan hoá: Winrate, số lệnh Win / Loss, R:R tích luỹ
- Chi tiết từng setup: Entry, SL linh động, TP1/TP2/TP3, ngày giờ vào lệnh, kết quả
- Bộ não AI Gemini thẩm định phong độ, phân tích đúng sai từng setup
=============================================================================
"""
import os
import sys
import threading
import customtkinter as ctk
from datetime import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS


class BacktestView(ctk.CTkFrame):
    """Giao diện Backtest 2 tháng chuyên nghiệp & Trực quan hoá phong độ"""

    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.app = app
        self.backtest_results = []
        self.filtered_results = []
        self._row_widgets = []
        self._build_ui()

    def _build_ui(self):
        # ─── 1. Header ───
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", padx=20, pady=(15, 5))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🧪  Backtest 2 Tháng & Phân Tích Phong Độ AI",
            font=("Segoe UI", 20, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # ─── 2. Controls & Configuration Row ───
        ctrl_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10, height=65)
        ctrl_frame.pack(fill="x", padx=20, pady=5)
        ctrl_frame.pack_propagate(False)

        # Symbol selector
        ctk.CTkLabel(ctrl_frame, text="Symbol:", font=("Segoe UI", 12, "bold"),
                      text_color=COLORS["text_secondary"]).pack(side="left", padx=(15, 5))
        
        default_symbol = "XAUUSD"
        if self.app and self.app.settings:
            syms = self.app.settings.get("mt5_symbols", ["XAUUSD"])
            if syms:
                default_symbol = syms[0]

        self.symbol_entry = ctk.CTkEntry(
            ctrl_frame, width=110, height=32, font=("Segoe UI", 12, "bold"),
            fg_color=COLORS["bg_input"], text_color=COLORS["accent_cyan"],
            border_color=COLORS["border"], corner_radius=6,
        )
        self.symbol_entry.insert(0, default_symbol)
        self.symbol_entry.pack(side="left", padx=(0, 10))

        # Timeframe
        ctk.CTkLabel(ctrl_frame, text="Khung:", font=("Segoe UI", 12),
                      text_color=COLORS["text_secondary"]).pack(side="left", padx=(5, 5))
        self.tf_menu = ctk.CTkOptionMenu(
            ctrl_frame, values=["M5", "M15", "M30", "H1"],
            width=80, height=32, font=("Segoe UI", 11),
            fg_color=COLORS["bg_input"], button_color=COLORS["border_light"],
            corner_radius=6,
        )
        self.tf_menu.set("M5")
        self.tf_menu.pack(side="left", padx=(0, 15))

        # Action Buttons
        self.btn_run = ctk.CTkButton(
            ctrl_frame, text="⚡ QUÉT 2 THÁNG", font=("Segoe UI", 12, "bold"),
            width=150, height=34, corner_radius=8,
            fg_color=COLORS["accent_blue"], hover_color="#1a47b8",
            text_color="#ffffff", command=self._start_backtest,
        )
        self.btn_run.pack(side="left", padx=5)

        self.btn_ai_eval = ctk.CTkButton(
            ctrl_frame, text="🧠 AI ĐÁNH GIÁ PHONG ĐỘ", font=("Segoe UI", 12, "bold"),
            width=190, height=34, corner_radius=8,
            fg_color=COLORS["accent_yellow"], hover_color="#c87411",
            text_color="#000000", command=self._start_ai_evaluation,
        )
        self.btn_ai_eval.pack(side="left", padx=5)

        self.btn_save_db = ctk.CTkButton(
            ctrl_frame, text="💾 Lưu Lịch Sử", font=("Segoe UI", 11),
            width=110, height=34, corner_radius=8,
            fg_color=COLORS["bg_input"], hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"], command=self._save_to_database,
        )
        self.btn_save_db.pack(side="left", padx=5)

        # Status text
        self.status_lbl = ctk.CTkLabel(
            ctrl_frame, text="Sẵn sàng quét dữ liệu 2 tháng quá khứ",
            font=("Segoe UI", 11), text_color=COLORS["text_muted"],
        )
        self.status_lbl.pack(side="right", padx=15)

        # ─── 3. Visual KPI Cards Row ───
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent", height=85)
        self.cards_frame.pack(fill="x", padx=20, pady=5)
        self.cards_frame.pack_propagate(False)

        self.kpi_widgets = {}
        kpi_data = [
            ("total",    "TỔNG SETUP",     "0",    COLORS["accent_blue"]),
            ("winrate",  "WINRATE",        "0.0%", COLORS["accent_cyan"]),
            ("wins",     "THẮNG (TP/Trail)","0",    COLORS["accent_green"]),
            ("losses",   "THUA (SL)",      "0",    COLORS["accent_red"]),
            ("total_r",  "LỢI NHUẬN R",   "+0.0R", COLORS["accent_green"]),
            ("avg_rr",   "R:R TRUNG BÌNH", "1:0.0",COLORS["accent_yellow"]),
        ]
        for i, (key, label, default_val, color) in enumerate(kpi_data):
            card = self._create_kpi_card(self.cards_frame, label, default_val, color)
            card.pack(side="left", fill="both", expand=True, padx=(0 if i == 0 else 6, 0))
            self.kpi_widgets[key] = card

        # ─── 4. AI Insights Box (Collapsible / expandable) ───
        self.ai_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10, height=120)
        self.ai_frame.pack(fill="x", padx=20, pady=5)
        self.ai_frame.pack_propagate(False)

        ai_header = ctk.CTkFrame(self.ai_frame, fg_color="transparent", height=28)
        ai_header.pack(fill="x", padx=15, pady=(8, 2))
        ai_header.pack_propagate(False)

        ctk.CTkLabel(
            ai_header, text="🧠  NHẬN XÉT CỦA BỘ NÃO AI GEMINI VỀ PHONG ĐỘ:",
            font=("Segoe UI", 12, "bold"), text_color=COLORS["accent_cyan"],
        ).pack(side="left")

        self.ai_textbox = ctk.CTkTextbox(
            self.ai_frame, font=("Segoe UI", 11), fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_secondary"], corner_radius=6, wrap="word",
        )
        self.ai_textbox.pack(fill="both", expand=True, padx=15, pady=(2, 8))
        self.ai_textbox.insert("1.0", "Nhấn nút '🧠 AI ĐÁNH GIÁ PHONG ĐỘ' để Gemini phân tích chi tiết ưu/nhược điểm các setup 2 tháng qua...")
        self.ai_textbox.configure(state="disabled")

        # ─── 5. Filter Row & Detailed Table ───
        filter_bar = ctk.CTkFrame(self, fg_color="transparent", height=35)
        filter_bar.pack(fill="x", padx=20, pady=(5, 0))
        filter_bar.pack_propagate(False)

        ctk.CTkLabel(
            filter_bar, text="📋 Danh Sách Chi Tiết Từng Lệnh:",
            font=("Segoe UI", 13, "bold"), text_color=COLORS["text_primary"],
        ).pack(side="left")

        self.filter_btn = ctk.CTkSegmentedButton(
            filter_bar, values=["Tất cả", "Chỉ Thắng (WIN)", "Bảo toàn (PARTIAL)", "Thua (LOSS)"],
            font=("Segoe UI", 11), selected_color=COLORS["accent_blue"],
            unselected_color=COLORS["bg_card"], text_color=COLORS["text_secondary"],
            command=self._apply_filter,
        )
        self.filter_btn.pack(side="right")
        self.filter_btn.set("Tất cả")

        # Table Header
        table_hdr = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=6, height=32)
        table_hdr.pack(fill="x", padx=20, pady=(4, 0))
        table_hdr.pack_propagate(False)

        cols = [
            ("Mã Setup", 90),
            ("Ngày Giờ Vào", 125),
            ("Symbol", 75),
            ("Phiên", 75),
            ("Hướng", 55),
            ("Entry", 85),
            ("SL", 85),
            ("TP1 (Bảo toàn)", 95),
            ("TP2 (Mục tiêu)", 95),
            ("Kết Quả", 80),
            ("R:R Đạt", 65),
            ("Điểm Chốt", 85),
            ("Cấu Trúc / Ghi Chú", 150),
        ]
        for name, width in cols:
            ctk.CTkLabel(
                table_hdr, text=name, font=("Segoe UI", 10, "bold"),
                text_color=COLORS["text_muted"], width=width, anchor="center",
            ).pack(side="left", padx=2)

        # Table Body
        self.table_scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["border_light"],
        )
        self.table_scroll.pack(fill="both", expand=True, padx=20, pady=(2, 10))

    def _create_kpi_card(self, parent, label, val, color):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=10)
        ctk.CTkLabel(
            card, text=label, font=("Segoe UI", 9, "bold"),
            text_color=COLORS["text_muted"],
        ).pack(pady=(8, 2))
        lbl = ctk.CTkLabel(
            card, text=val, font=("Consolas", 18, "bold"),
            text_color=color,
        )
        lbl.pack(pady=(0, 8))
        card.value_label = lbl
        return card

    # ─────────────────────────────────────────────────────────
    # BACKTEST EXECUTION
    # ─────────────────────────────────────────────────────────
    def _start_backtest(self):
        """Khởi chạy quét 15.000 nến 2 tháng MT5 trên background thread"""
        if not self.app or not self.app.mt5:
            self.status_lbl.configure(text="❌ MT5 Connector chưa sẵn sàng")
            return

        if not self.app.mt5.connected:
            self.status_lbl.configure(text="⏳ Đang kết nối MT5...")
            self.app.mt5.connect()
            if not self.app.mt5.connected:
                self.status_lbl.configure(text="❌ Không thể kết nối MT5. Hãy mở MT5!")
                return

        symbol = self.symbol_entry.get().strip().upper()
        if not symbol:
            symbol = "XAUUSD"

        tf = self.tf_menu.get()
        self.app.mt5.timeframe_str = tf

        self.btn_run.configure(state="disabled", text="⏳ ĐANG QUÉT...")
        self.status_lbl.configure(text=f"⏳ Đang tải 15.000 nến {tf} cho {symbol}...")

        def worker():
            try:
                # Quét 15.000 nến (~2 tháng M5)
                resolved_sym = self.app.mt5.resolve_symbol(symbol)
                setups = self.app.mt5.scan_historical_setups(
                    resolved_sym,
                    swing_lookback=20,
                    min_wick_pct=55.0,
                    max_candles=15000,
                )
                self.after(0, lambda: self._on_backtest_completed(setups, resolved_sym))
            except Exception as e:
                self.after(0, lambda: self._on_backtest_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_backtest_completed(self, setups, symbol):
        self.btn_run.configure(state="normal", text="⚡ QUÉT 2 THÁNG")
        self.backtest_results = setups
        self.status_lbl.configure(text=f"✅ Hoàn tất! Phát hiện {len(setups)} setup trên {symbol}")

        # Cập nhật KPI
        total = len(setups)
        wins = len([s for s in setups if s.get("outcome") in ["WIN", "PARTIAL"]])
        losses = len([s for s in setups if s.get("outcome") == "LOSS"])
        wr = round((wins / max(1, wins + losses)) * 100, 1) if (wins + losses) > 0 else 0
        total_r = sum(float(s.get("rr_achieved", 0)) for s in setups)
        
        win_rrs = [float(s.get("rr_achieved", 0)) for s in setups if s.get("outcome") in ["WIN", "PARTIAL"]]
        avg_rr = round(sum(win_rrs) / max(1, len(win_rrs)), 1) if win_rrs else 0.0

        self.kpi_widgets["total"].value_label.configure(text=str(total))
        self.kpi_widgets["winrate"].value_label.configure(text=f"{wr}%")
        self.kpi_widgets["wins"].value_label.configure(text=f"{wins}")
        self.kpi_widgets["losses"].value_label.configure(text=f"{losses}")
        self.kpi_widgets["total_r"].value_label.configure(text=f"+{total_r:.1f}R" if total_r >= 0 else f"{total_r:.1f}R")
        self.kpi_widgets["avg_rr"].value_label.configure(text=f"1:{avg_rr}")

        # Render bảng chi tiết
        self._apply_filter(self.filter_btn.get())

        # Gợi ý bấm nút AI
        self.ai_textbox.configure(state="normal")
        self.ai_textbox.delete("1.0", "end")
        self.ai_textbox.insert("1.0", f"✅ Đã quét xong {total} setup cho {symbol}!\nNhấn nút '🧠 AI ĐÁNH GIÁ PHONG ĐỘ' phía trên để Gemini phân tích sâu từng khía cạnh của chiến lược.")
        self.ai_textbox.configure(state="disabled")

    def _on_backtest_error(self, err):
        self.btn_run.configure(state="normal", text="⚡ QUÉT 2 THÁNG")
        self.status_lbl.configure(text=f"❌ Lỗi: {err}")

    # ─────────────────────────────────────────────────────────
    # AI EVALUATION
    # ─────────────────────────────────────────────────────────
    def _start_ai_evaluation(self):
        """Gọi Gemini AI thẩm định toàn diện kết quả backtest 2 tháng"""
        if not self.backtest_results:
            self.status_lbl.configure(text="⚠️ Vui lòng bấm 'Quét 2 Tháng' trước khi AI đánh giá!")
            return

        if not self.app or not self.app.gemini or not self.app.gemini.ready:
            self.status_lbl.configure(text="⚠️ Gemini AI chưa sẵn sàng. Hãy kiểm tra API Key!")
            return

        self.btn_ai_eval.configure(state="disabled", text="🧠 ĐANG PHÂN TÍCH...")
        self.status_lbl.configure(text="🧠 Gemini AI đang đối chiếu dữ liệu và đánh giá phong độ...")

        total = len(self.backtest_results)
        wins = len([s for s in self.backtest_results if s.get("outcome") in ["WIN", "PARTIAL"]])
        losses = len([s for s in self.backtest_results if s.get("outcome") == "LOSS"])
        wr = round((wins / max(1, wins + losses)) * 100, 1) if (wins + losses) > 0 else 0
        total_r = sum(float(s.get("rr_achieved", 0)) for s in self.backtest_results)
        sym = self.symbol_entry.get()

        summary_text = (
            f"Symbol: {sym} | Tổng setup: {total}\n"
            f"Thắng: {wins} ({wr}%) | Thua: {losses}\n"
            f"Tổng lợi nhuận: +{total_r:.1f}R\n"
            f"Chiến lược: Dynamic SL/TP (TP1 chốt 40% + break-even, TP2 mục tiêu 40%, TP3 trailing 20%)\n"
            f"Setup gồm: Liquidity Sweep đáy/đỉnh cũ + Pin Bar râu dài (>55%) + FVG + Order Block."
        )

        def worker():
            try:
                assessment = self.app.gemini.analyze_backtest_results(summary_text)
                self.after(0, lambda: self._on_ai_eval_completed(assessment))
            except Exception as e:
                self.after(0, lambda: self._on_ai_eval_completed(f"❌ Lỗi AI: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ai_eval_completed(self, text):
        self.btn_ai_eval.configure(state="normal", text="🧠 AI ĐÁNH GIÁ PHONG ĐỘ")
        self.status_lbl.configure(text="✅ AI đã hoàn tất thẩm định phong độ!")
        self.ai_textbox.configure(state="normal")
        self.ai_textbox.delete("1.0", "end")
        self.ai_textbox.insert("1.0", text)
        self.ai_textbox.configure(state="disabled")

    # ─────────────────────────────────────────────────────────
    # SAVE TO DATABASE
    # ─────────────────────────────────────────────────────────
    def _save_to_database(self):
        if not self.backtest_results:
            self.status_lbl.configure(text="⚠️ Chưa có dữ liệu để lưu!")
            return
        if self.app and self.app.trade_logger:
            count = self.app.trade_logger.log_trades_batch(self.backtest_results)
            self.status_lbl.configure(text=f"💾 Đã nạp thành công {count} lệnh vào nhật ký kinh nghiệm!")

    # ─────────────────────────────────────────────────────────
    # TABLE RENDERING & FILTERING
    # ─────────────────────────────────────────────────────────
    def _apply_filter(self, choice=None):
        choice = choice or self.filter_btn.get()
        if choice == "Chỉ Thắng (WIN)":
            self.filtered_results = [s for s in self.backtest_results if s.get("outcome") == "WIN"]
        elif choice == "Bảo toàn (PARTIAL)":
            self.filtered_results = [s for s in self.backtest_results if s.get("outcome") == "PARTIAL"]
        elif choice == "Thua (LOSS)":
            self.filtered_results = [s for s in self.backtest_results if s.get("outcome") == "LOSS"]
        else:
            self.filtered_results = list(self.backtest_results)

        # Clear existing rows
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()

        # Render rows
        for i, setup in enumerate(self.filtered_results):
            self._render_table_row(setup, i)

    def _render_table_row(self, s: dict, index: int):
        outcome = s.get("outcome", "").upper()
        row_bg = COLORS["bg_card"] if index % 2 == 0 else COLORS["bg_dark"]
        
        row_frame = ctk.CTkFrame(self.table_scroll, fg_color=row_bg, corner_radius=6, height=30)
        row_frame.pack(fill="x", pady=1)
        row_frame.pack_propagate(False)

        # Định dạng màu sắc kết quả
        if outcome == "WIN":
            outcome_color = COLORS["accent_green"]
        elif outcome == "PARTIAL":
            outcome_color = COLORS["accent_yellow"]
        elif outcome == "LOSS":
            outcome_color = COLORS["accent_red"]
        else:
            outcome_color = COLORS["text_muted"]

        rr_val = float(s.get("rr_achieved", 0))
        rr_color = COLORS["accent_green"] if rr_val > 0 else (COLORS["accent_red"] if rr_val < 0 else COLORS["text_muted"])

        cols_data = [
            (str(s.get("trade_id", ""))[:12], 90, COLORS["text_secondary"]),
            (str(s.get("timestamp", ""))[:16], 125, COLORS["text_muted"]),
            (str(s.get("symbol", "")), 75, COLORS["accent_cyan"]),
            (str(s.get("session", "")), 75, COLORS["text_secondary"]),
            (str(s.get("direction", "BUY")), 55, COLORS["accent_green"] if s.get("direction") == "BUY" else COLORS["accent_red"]),
            (str(s.get("entry_price", 0)), 85, COLORS["text_primary"]),
            (str(s.get("stop_loss", 0)), 85, COLORS["accent_red"]),
            (str(s.get("tp1", s.get("take_profit", 0))), 95, COLORS["accent_yellow"]),
            (str(s.get("tp2", s.get("take_profit", 0))), 95, COLORS["accent_green"]),
            (outcome, 80, outcome_color),
            (f"+{rr_val}R" if rr_val > 0 else f"{rr_val}R", 65, rr_color),
            (str(s.get("tp_hit", "-")), 85, COLORS["text_secondary"]),
            (f"{s.get('market_structure', '')} | {s.get('notes', '')}"[:25], 150, COLORS["text_muted"]),
        ]

        for val, width, color in cols_data:
            ctk.CTkLabel(
                row_frame, text=val, font=("Consolas", 10),
                text_color=color, width=width, anchor="center",
            ).pack(side="left", padx=2)

        self._row_widgets.append(row_frame)
