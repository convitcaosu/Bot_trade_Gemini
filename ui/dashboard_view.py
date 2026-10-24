"""
=============================================================================
DASHBOARD VIEW — Trang chính với stats cards, chart preview, AI analysis
=============================================================================
"""
import os
import sys
import customtkinter as ctk
from PIL import Image, ImageTk
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS


class DashboardView(ctk.CTkFrame):
    """Dashboard chính — stats cards + chart preview + AI analysis"""

    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.app = app
        self._last_signal = None

        self._build_ui()

    def _build_ui(self):
        # ─── Header ───
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", padx=20, pady=(15, 5))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="📊  Dashboard",
            font=("Segoe UI", 22, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # Refresh button
        ctk.CTkButton(
            header, text="🔄 Refresh", font=("Segoe UI", 12),
            width=100, height=32, corner_radius=8,
            fg_color=COLORS["bg_card"], hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self.refresh,
        ).pack(side="right")

        # ─── Stats Cards Row ───
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent", height=100)
        self.cards_frame.pack(fill="x", padx=20, pady=(5, 10))
        self.cards_frame.pack_propagate(False)

        self.card_widgets = {}
        cards_data = [
            ("total",   "Total Trades", "0",    COLORS["accent_blue"]),
            ("winrate", "Winrate",      "0%",   COLORS["accent_cyan"]),
            ("total_rr","Total R:R",    "+0R",  COLORS["accent_green"]),
            ("avg_rr",  "Avg R:R",      "0",    COLORS["accent_yellow"]),
            ("streak",  "Streak",       "-",    COLORS["text_secondary"]),
        ]

        for i, (key, label, default_val, color) in enumerate(cards_data):
            card = self._create_stat_card(self.cards_frame, label, default_val, color)
            card.pack(side="left", fill="both", expand=True, padx=(0 if i == 0 else 5, 0))
            self.card_widgets[key] = card

        # ─── Main Content (Chart + AI Analysis) ───
        main_content = ctk.CTkFrame(self, fg_color="transparent")
        main_content.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Left: Chart Preview
        chart_frame = ctk.CTkFrame(main_content, fg_color=COLORS["bg_card"], corner_radius=12)
        chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ctk.CTkLabel(
            chart_frame, text="📈  Latest Signal Chart",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=15, pady=(12, 5))

        self.chart_label = ctk.CTkLabel(
            chart_frame,
            text="Chưa có tín hiệu.\n\nKết nối MT5 và bật Auto Scan\nhoặc gửi ảnh chart qua Telegram.",
            font=("Segoe UI", 13),
            text_color=COLORS["text_muted"],
            justify="center",
        )
        self.chart_label.pack(fill="both", expand=True, padx=15, pady=10)

        # Right: AI Analysis + Quick Actions
        right_panel = ctk.CTkFrame(main_content, fg_color="transparent", width=380)
        right_panel.pack(side="right", fill="y", padx=(5, 0))
        right_panel.pack_propagate(False)

        # AI Analysis Box
        ai_frame = ctk.CTkFrame(right_panel, fg_color=COLORS["bg_card"], corner_radius=12)
        ai_frame.pack(fill="both", expand=True, pady=(0, 5))

        ctk.CTkLabel(
            ai_frame, text="🧠  AI Analysis",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=15, pady=(12, 5))

        self.ai_textbox = ctk.CTkTextbox(
            ai_frame, font=("Consolas", 11),
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_secondary"],
            corner_radius=8,
            wrap="word",
            border_width=1,
            border_color=COLORS["border"],
        )
        self.ai_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 12))
        self.ai_textbox.insert("1.0", "Đang chờ tín hiệu từ MT5...\n\nBot sẽ tự động phân tích khi phát hiện setup SMC.")
        self.ai_textbox.configure(state="disabled")

        # Quick Actions
        actions_frame = ctk.CTkFrame(right_panel, fg_color=COLORS["bg_card"],
                                      corner_radius=12, height=130)
        actions_frame.pack(fill="x", pady=(5, 0))
        actions_frame.pack_propagate(False)

        ctk.CTkLabel(
            actions_frame, text="⚡  Quick Actions",
            font=("Segoe UI", 13, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=15, pady=(10, 5))

        btn_row = ctk.CTkFrame(actions_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="✅ Log Win", font=("Segoe UI", 11, "bold"),
            height=36, corner_radius=8,
            fg_color=COLORS["accent_green"],
            hover_color="#1b8a7a",
            text_color="#ffffff",
            command=self._log_win,
        ).pack(side="left", fill="x", expand=True, padx=(0, 3))

        ctk.CTkButton(
            btn_row, text="❌ Log Loss", font=("Segoe UI", 11, "bold"),
            height=36, corner_radius=8,
            fg_color=COLORS["accent_red"],
            hover_color="#c62828",
            text_color="#ffffff",
            command=self._log_loss,
        ).pack(side="left", fill="x", expand=True, padx=(3, 3))

        ctk.CTkButton(
            btn_row, text="🔍 Scan Now", font=("Segoe UI", 11, "bold"),
            height=36, corner_radius=8,
            fg_color=COLORS["accent_blue"],
            hover_color="#1a47b8",
            text_color="#ffffff",
            command=self._manual_scan,
        ).pack(side="left", fill="x", expand=True, padx=(3, 0))

        btn_row2 = ctk.CTkFrame(actions_frame, fg_color="transparent")
        btn_row2.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkButton(
            btn_row2, text="⚡ Backtest 2 Tháng MT5", font=("Segoe UI", 11, "bold"),
            height=32, corner_radius=8,
            fg_color=COLORS["accent_blue"],
            hover_color="#1a47b8",
            text_color="#ffffff",
            command=self._backtest_2_months,
        ).pack(side="left", fill="x", expand=True, padx=(0, 3))

        ctk.CTkButton(
            btn_row2, text="📊 Báo Cáo Pro", font=("Segoe UI", 11),
            height=32, corner_radius=8,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self._generate_report,
        ).pack(side="left", fill="x", expand=True, padx=(3, 0))

    def _create_stat_card(self, parent, label, value, accent_color):
        """Tạo 1 stat card đẹp"""
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12)

        # Accent bar on top
        accent = ctk.CTkFrame(card, height=3, fg_color=accent_color, corner_radius=2)
        accent.pack(fill="x", padx=15, pady=(10, 0))

        # Value
        val_label = ctk.CTkLabel(
            card, text=value,
            font=("Segoe UI", 24, "bold"),
            text_color=COLORS["text_primary"],
        )
        val_label.pack(pady=(8, 0))
        card._val_label = val_label

        # Label
        ctk.CTkLabel(
            card, text=label,
            font=("Segoe UI", 11),
            text_color=COLORS["text_secondary"],
        ).pack(pady=(0, 10))

        return card

    # ─────────────────────────────────────────────────────────
    # REFRESH / UPDATE
    # ─────────────────────────────────────────────────────────
    def refresh(self):
        """Refresh tất cả stats"""
        if not self.app or not self.app.trade_logger:
            return

        stats = self.app.trade_logger.get_stats_summary()
        self._update_card("total", str(stats.get("total", 0)))
        self._update_card("winrate", f"{stats.get('winrate', 0)}%")
        self._update_card("total_rr", f"+{stats.get('total_rr', 0)}R")
        self._update_card("avg_rr", f"1:{stats.get('avg_rr', 0)}")

    def _update_card(self, key, value):
        card = self.card_widgets.get(key)
        if card and hasattr(card, "_val_label"):
            card._val_label.configure(text=value)

    def on_new_signal(self, signal):
        """Khi có signal mới — update chart + AI analysis"""
        self._last_signal = signal

        # Update chart image
        if signal.chart_image_path and os.path.exists(signal.chart_image_path):
            try:
                img = Image.open(signal.chart_image_path)
                # Resize to fit
                img.thumbnail((700, 400), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                                       size=img.size)
                self.chart_label.configure(image=ctk_img, text="")
                self.chart_label._ctk_img = ctk_img  # Prevent GC
            except Exception:
                self.chart_label.configure(
                    text=f"📊 {signal.direction} {signal.symbol}\n"
                         f"Entry: {signal.entry_price} | SL: {signal.stop_loss} | TP: {signal.take_profit}"
                )

        # Update AI analysis
        if signal.ai_analysis:
            self.ai_textbox.configure(state="normal")
            self.ai_textbox.delete("1.0", "end")
            self.ai_textbox.insert("1.0", signal.ai_analysis)
            self.ai_textbox.configure(state="disabled")

        # Refresh stats
        self.refresh()

    # ─────────────────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────────────────
    def _log_win(self):
        if self._last_signal and self.app and self.app.trade_logger:
            self.app.trade_logger.log_trade({
                "trade_id": self.app.trade_logger.get_next_id(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "symbol": self._last_signal.symbol,
                "timeframe": self._last_signal.timeframe,
                "session": self._last_signal.session,
                "wick_percent": self._last_signal.wick_percent,
                "sweep_pips": self._last_signal.sweep_pips,
                "direction": self._last_signal.direction,
                "entry_price": self._last_signal.entry_price,
                "stop_loss": self._last_signal.stop_loss,
                "take_profit": self._last_signal.take_profit,
                "outcome": "WIN",
                "rr_achieved": self._last_signal.risk_reward_ratio(),
                "ai_score": self._last_signal.ai_score,
                "ai_analysis": self._last_signal.ai_analysis[:200],
                "image_path": self._last_signal.chart_image_path,
                "notes": "Logged from Dashboard",
            })
            self.app.set_status("✅ Đã ghi WIN vào database kinh nghiệm!")
            self.refresh()

    def _log_loss(self):
        if self._last_signal and self.app and self.app.trade_logger:
            self.app.trade_logger.log_trade({
                "trade_id": self.app.trade_logger.get_next_id(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "symbol": self._last_signal.symbol,
                "timeframe": self._last_signal.timeframe,
                "session": self._last_signal.session,
                "wick_percent": self._last_signal.wick_percent,
                "sweep_pips": self._last_signal.sweep_pips,
                "direction": self._last_signal.direction,
                "entry_price": self._last_signal.entry_price,
                "stop_loss": self._last_signal.stop_loss,
                "take_profit": self._last_signal.take_profit,
                "outcome": "LOSS",
                "rr_achieved": -1.0,
                "ai_score": self._last_signal.ai_score,
                "ai_analysis": self._last_signal.ai_analysis[:200],
                "image_path": self._last_signal.chart_image_path,
                "notes": "Logged from Dashboard",
            })
            self.app.set_status("❌ Đã ghi LOSS vào database kinh nghiệm.")
            self.refresh()

    def _manual_scan(self):
        """Trigger quét setup thủ công"""
        if self.app:
            self.app.set_status("🔍 Đang quét tất cả cặp tiền...")
            import threading
            threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        if not self.app or not self.app.mt5 or not self.app.mt5.connected:
            self.after(0, lambda: self.app.set_status("⚠️ MT5 chưa kết nối!"))
            return

        from core.mt5_data import SMCSetup
        from core.signal_dispatcher import Signal

        found = False
        for symbol in self.app.mt5.symbols:
            setup = self.app.mt5.detect_smc_setup(symbol)
            if setup:
                # Render chart
                chart_path = self.app.mt5.render_chart(setup)

                # AI analysis
                ai_text = ""
                if self.app.gemini and self.app.gemini.ready:
                    stats_text = ""
                    if self.app.quant_engine:
                        stats_text = self.app.quant_engine.get_stats_text()
                    if chart_path:
                        ai_text = self.app.gemini.analyze_chart(chart_path, stats_text)
                    else:
                        ai_text = self.app.gemini.analyze_setup_data(
                            {"symbol": setup.symbol, "timeframe": setup.timeframe,
                             "session": setup.session, "wick_percent": setup.wick_percent,
                             "sweep_pips": setup.sweep_pips, "has_fvg": setup.has_fvg,
                             "entry_price": setup.entry_price, "stop_loss": setup.stop_loss,
                             "take_profit": setup.take_profit},
                            stats_text)

                # Create signal
                signal = Signal(
                    signal_id=setup.signal_id,
                    timestamp=setup.timestamp.strftime("%Y-%m-%d %H:%M") if setup.timestamp else "",
                    symbol=setup.symbol,
                    timeframe=setup.timeframe,
                    direction=setup.direction,
                    entry_price=setup.entry_price,
                    stop_loss=setup.stop_loss,
                    take_profit=setup.take_profit,
                    wick_percent=setup.wick_percent,
                    sweep_pips=setup.sweep_pips,
                    session=setup.session,
                    has_fvg=setup.has_fvg,
                    ai_analysis=ai_text,
                    chart_image_path=chart_path or "",
                )

                # Dispatch
                if self.app.dispatcher:
                    self.app.dispatcher.dispatch(signal)
                found = True

        if not found:
            self.after(0, lambda: self.app.set_status("🔍 Scan hoàn tất — không phát hiện setup mới."))
        else:
            self.after(0, lambda: self.app.set_status("🚨 Phát hiện setup mới! Xem tab Signals."))

    def _generate_report(self):
        if self.app and self.app.quant_engine:
            self.app.set_status("📊 Đang tạo báo cáo phân tích...")
            import threading
            threading.Thread(target=self._do_report, daemon=True).start()

    def _do_report(self):
        path = self.app.quant_engine.generate_report_chart()
        if path and os.path.exists(path):
            self.after(0, lambda: self.app.set_status(f"📊 Báo cáo đã tạo! Xem tab Statistics."))
            # Switch to stats view
            self.after(100, lambda: self.app.switch_view("stats"))
        else:
            self.after(0, lambda: self.app.set_status("⚠️ Không đủ dữ liệu để tạo báo cáo."))

    def _backtest_2_months(self):
        if not self.app or not self.app.mt5:
            return
        if not self.app.mt5.connected:
            self.app.set_status("⚠️ MT5 chưa kết nối. Đang kết nối lại...")
            self.app.mt5.connect()
            if not self.app.mt5.connected:
                self.app.set_status("❌ Không kết nối được MT5!")
                return

        self.app.set_status("⏳ Đang quét 15.000 nến M5 (2 tháng) từ MT5...")
        import threading

        def worker():
            try:
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
                self.after(0, lambda: self.app.set_status(f"❌ Lỗi Backtest: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_backtest_done(self, msg):
        if self.app:
            self.app.set_status(msg)
        self.refresh()

    def _load_demo_data(self):
        if self.app and self.app.trade_logger:
            count = self.app.trade_logger.generate_sample_data()
            self.app.set_status(f"🎲 Đã tạo {count} lệnh mẫu! Database đã được backup.")
            self.refresh()
