"""
=============================================================================
SIGNALS VIEW — Feed tín hiệu realtime
Mỗi signal hiển thị: direction, symbol, Entry/SL/TP, AI score, analysis
=============================================================================
"""
import os
import sys
import customtkinter as ctk
from PIL import Image
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS


class SignalsView(ctk.CTkFrame):
    """Feed tín hiệu giao dịch — realtime display"""

    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.app = app
        self.signal_cards = []
        self._build_ui()

    def _build_ui(self):
        # ─── Header ───
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", padx=20, pady=(15, 5))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="📡  Signal Feed",
            font=("Segoe UI", 22, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # Live indicator
        self.live_dot = ctk.CTkLabel(
            header, text="● LIVE",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["accent_green"],
        )
        self.live_dot.pack(side="right", padx=10)

        # Signal count
        self.count_label = ctk.CTkLabel(
            header, text="0 signals",
            font=("Segoe UI", 12),
            text_color=COLORS["text_muted"],
        )
        self.count_label.pack(side="right", padx=10)

        # Clear button
        ctk.CTkButton(
            header, text="🗑️ Clear", font=("Segoe UI", 11),
            width=80, height=30, corner_radius=6,
            fg_color=COLORS["bg_card"], hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self._clear_signals,
        ).pack(side="right", padx=5)

        # ─── Scrollable Signal Feed ───
        self.feed = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["border_light"],
        )
        self.feed.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        # Empty state
        self.empty_label = ctk.CTkLabel(
            self.feed,
            text="Chưa có tín hiệu.\n\n"
                 "📡 Kết nối MT5 và bật Auto Scan để nhận signal tự động\n"
                 "📸 Hoặc gửi ảnh chart qua Telegram",
            font=("Segoe UI", 14),
            text_color=COLORS["text_muted"],
            justify="center",
        )
        self.empty_label.pack(pady=80)

    def add_signal(self, signal):
        """Thêm 1 signal card mới vào feed (mới nhất ở trên)"""
        # Hide empty state
        if self.empty_label.winfo_exists():
            self.empty_label.pack_forget()

        card = self._create_signal_card(signal)
        card.pack(fill="x", pady=(0, 8), before=self.signal_cards[0] if self.signal_cards else None)
        self.signal_cards.insert(0, card)

        # Update count
        self.count_label.configure(text=f"{len(self.signal_cards)} signals")

    def _create_signal_card(self, signal):
        """Tạo 1 signal card đẹp"""
        is_buy = signal.direction == "BUY"
        accent = COLORS["accent_green"] if is_buy else COLORS["accent_red"]

        card = ctk.CTkFrame(
            self.feed, fg_color=COLORS["bg_card"],
            corner_radius=12, border_width=1,
            border_color=accent,
        )

        # ─── Top Row: Direction + Symbol + Time + Score ───
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(12, 5))

        # Direction badge
        badge_color = COLORS["accent_green"] if is_buy else COLORS["accent_red"]
        badge = ctk.CTkLabel(
            top, text=f" {signal.direction} ",
            font=("Segoe UI", 12, "bold"),
            text_color="#ffffff",
            fg_color=badge_color,
            corner_radius=6,
            width=60, height=28,
        )
        badge.pack(side="left")

        # Symbol + Timeframe
        ctk.CTkLabel(
            top, text=f"  {signal.symbol}  {signal.timeframe}",
            font=("Segoe UI", 15, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left", padx=(8, 0))

        # Session tag
        ctk.CTkLabel(
            top, text=f"  {signal.session}  ",
            font=("Segoe UI", 10),
            text_color=COLORS["text_muted"],
            fg_color=COLORS["bg_input"],
            corner_radius=4,
        ).pack(side="left", padx=8)

        # Score
        score_color = COLORS["accent_green"] if signal.ai_score >= 7 else (
            COLORS["accent_yellow"] if signal.ai_score >= 5 else COLORS["accent_red"])
        ctk.CTkLabel(
            top, text=f"⭐ {signal.ai_score}/10",
            font=("Segoe UI", 13, "bold"),
            text_color=score_color,
        ).pack(side="right")

        # Timestamp
        ctk.CTkLabel(
            top, text=f"🕐 {signal.timestamp}",
            font=("Segoe UI", 11),
            text_color=COLORS["text_muted"],
        ).pack(side="right", padx=10)

        # ─── Price Row: Entry / SL / TP ───
        price_row = ctk.CTkFrame(card, fg_color=COLORS["bg_dark"],
                                  corner_radius=8, height=45)
        price_row.pack(fill="x", padx=15, pady=5)
        price_row.pack_propagate(False)

        prices = [
            ("🎯 Entry", signal.entry_price, COLORS["accent_blue"]),
            ("🛑 SL", signal.stop_loss, COLORS["accent_red"]),
        ]
        if signal.tp1 > 0:
            prices.append(("🥇 TP1 (40%)", signal.tp1, COLORS["accent_yellow"]))
        if signal.tp2 > 0:
            prices.append(("🥈 TP2 (40%)", signal.tp2, COLORS["accent_green"]))
        if signal.tp3 > 0:
            prices.append(("🥉 TP3 (Trail)", signal.tp3, COLORS["accent_cyan"]))
        if not signal.tp1 and signal.take_profit > 0:
            prices.append(("✅ TP", signal.take_profit, COLORS["accent_green"]))

        rr = signal.risk_reward_ratio()
        prices.append(("📊 R:R", f"1:{rr}", COLORS["accent_cyan"]))

        for label, value, color in prices:
            item = ctk.CTkFrame(price_row, fg_color="transparent")
            item.pack(side="left", fill="both", expand=True)
            ctk.CTkLabel(
                item, text=label, font=("Segoe UI", 9, "bold"),
                text_color=COLORS["text_muted"],
            ).pack()
            ctk.CTkLabel(
                item, text=str(value), font=("Consolas", 11, "bold"),
                text_color=color,
            ).pack()

        # ─── Wick + Sweep info + V4 method / AI components ───
        info_row = ctk.CTkFrame(card, fg_color="transparent")
        info_row.pack(fill="x", padx=15, pady=2)

        v4_info = ""
        if getattr(signal, "method_id", ""):
            v4_info += f"Method: {signal.method_id}  |  "
        comps = getattr(signal, "ai_components", {}) or {}
        if comps:
            v4_info += "AI: " + "  ".join(f"{k} {v}/10" for k, v in comps.items()) + "  |  "
        if getattr(signal, "ai_reason", ""):
            v4_info += f"{signal.ai_reason}  |  "
        ctk.CTkLabel(
            info_row, text=f"{v4_info}Wick: {signal.wick_percent}%  |  Sweep: {signal.sweep_pips} pips  |  FVG: {'✅' if signal.has_fvg else '❌'}",
            font=("Segoe UI", 11),
            text_color=COLORS["text_muted"],
            wraplength=900, justify="left",
        ).pack(side="left", fill="x", expand=True)

        # ─── AI Analysis Preview ───
        if signal.ai_analysis:
            analysis_preview = signal.ai_analysis[:300].replace("\n", " ")
            ai_frame = ctk.CTkFrame(card, fg_color=COLORS["bg_dark"],
                                     corner_radius=8)
            ai_frame.pack(fill="x", padx=15, pady=5)

            ctk.CTkLabel(
                ai_frame, text=f"🧠 {analysis_preview}...",
                font=("Segoe UI", 11),
                text_color=COLORS["text_secondary"],
                wraplength=800,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=10, pady=8)

        # ─── Action Buttons ───
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(5, 12))

        ctk.CTkButton(
            btn_row, text="✅ Win", font=("Segoe UI", 11),
            width=70, height=28, corner_radius=6,
            fg_color=COLORS["accent_green"],
            hover_color="#1b8a7a",
            text_color="#ffffff",
            command=lambda s=signal: self._log_outcome(s, "WIN"),
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btn_row, text="❌ Loss", font=("Segoe UI", 11),
            width=70, height=28, corner_radius=6,
            fg_color=COLORS["accent_red"],
            hover_color="#c62828",
            text_color="#ffffff",
            command=lambda s=signal: self._log_outcome(s, "LOSS"),
        ).pack(side="left", padx=(0, 5))

        if signal.chart_image_path and os.path.exists(signal.chart_image_path):
            ctk.CTkButton(
                btn_row, text="👁️ View Chart", font=("Segoe UI", 11),
                width=100, height=28, corner_radius=6,
                fg_color=COLORS["bg_input"],
                hover_color=COLORS["border_light"],
                text_color=COLORS["text_secondary"],
                command=lambda s=signal: self._view_chart(s),
            ).pack(side="left", padx=(0, 5))

        return card

    def _log_outcome(self, signal, outcome):
        if not self.app or not self.app.trade_logger:
            return
        rr = signal.risk_reward_ratio() if outcome == "WIN" else -1.0
        self.app.trade_logger.log_trade({
            "trade_id": self.app.trade_logger.get_next_id(),
            "timestamp": signal.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "symbol": signal.symbol,
            "timeframe": signal.timeframe,
            "session": signal.session,
            "wick_percent": signal.wick_percent,
            "sweep_pips": signal.sweep_pips,
            "direction": signal.direction,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "outcome": outcome,
            "rr_achieved": rr,
            "ai_score": signal.ai_score,
            "ai_analysis": signal.ai_analysis[:200] if signal.ai_analysis else "",
            "image_path": signal.chart_image_path,
            "notes": "Logged from Signal Feed",
        })
        emoji = "✅" if outcome == "WIN" else "❌"
        self.app.set_status(f"{emoji} Đã ghi {outcome} cho {signal.symbol} vào kinh nghiệm!")

    def _view_chart(self, signal):
        """Mở chart lớn trong Dashboard"""
        if self.app:
            dash = self.app.views.get("dashboard", {}).get("instance")
            if dash:
                dash.on_new_signal(signal)
                self.app.switch_view("dashboard")

    def _clear_signals(self):
        for card in self.signal_cards:
            card.destroy()
        self.signal_cards.clear()
        self.count_label.configure(text="0 signals")
        self.empty_label.pack(pady=80)

    def refresh(self):
        """Load signals from dispatcher history"""
        if self.app and self.app.dispatcher:
            history = self.app.dispatcher.get_history()
            # Only add new ones
            existing_count = len(self.signal_cards)
            for signal in history[existing_count:]:
                self.add_signal(signal)
