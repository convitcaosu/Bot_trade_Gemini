"""
=============================================================================
APP WINDOW — Cửa sổ chính Desktop Dashboard
- Sidebar navigation với icon
- Content area chuyển giữa các view
- Status bar realtime
=============================================================================
"""
import os
import sys
import threading
import queue

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, ASSETS_DIR

# ─── CustomTkinter Theme ───
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class AppWindow(ctk.CTk):
    """Cửa sổ chính — Trading Dashboard Pro Dark Mode"""

    def __init__(self, dispatcher=None, trade_logger=None, quant_engine=None,
                 mt5_connector=None, gemini_brain=None, settings_mgr=None):
        super().__init__()

        # Store references
        self.dispatcher = dispatcher
        self.trade_logger = trade_logger
        self.quant_engine = quant_engine
        self.mt5 = mt5_connector
        self.gemini = gemini_brain
        self.settings = settings_mgr

        # ─── Window Config ───
        self.title("⚡ Gemini Trade Bot Pro v2.0")
        self.geometry("1440x850")
        self.minsize(1100, 650)
        self.configure(fg_color=COLORS["bg_darkest"])

        # ─── Views registry ───
        self.views = {}
        self.current_view_name = None

        # ─── Layout ───
        self._create_sidebar()
        self._create_content_area()
        self._create_status_bar()

        # ─── Default view ───
        self.after(100, lambda: self.switch_view("dashboard"))

        # ─── Signal polling (check queue every 200ms) ───
        if self.dispatcher:
            self._poll_signals()

        # ─── Status update timer ───
        self._update_status()

    # ─────────────────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────────────────
    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0,
            fg_color=COLORS["bg_sidebar"],
            border_width=0,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # ─── Logo / Title ───
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=80)
        logo_frame.pack(fill="x", pady=(20, 10), padx=15)
        logo_frame.pack_propagate(False)

        ctk.CTkLabel(
            logo_frame, text="⚡", font=("Segoe UI Emoji", 28),
            text_color=COLORS["accent_cyan"]
        ).pack(side="left", padx=(5, 8))

        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="y", expand=True)
        ctk.CTkLabel(
            title_frame, text="GEMINI", font=("Segoe UI", 18, "bold"),
            text_color=COLORS["accent_cyan"], anchor="sw"
        ).pack(fill="x")
        ctk.CTkLabel(
            title_frame, text="TRADE BOT PRO", font=("Segoe UI", 10),
            text_color=COLORS["text_secondary"], anchor="nw"
        ).pack(fill="x")

        # ─── Divider ───
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=COLORS["border"]
        ).pack(fill="x", padx=15, pady=(5, 15))

        # ─── Navigation Buttons ───
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "📊", "Dashboard"),
            ("v4", "⚡", "V4 Pro"),
            ("backtest",  "🧪", "Backtest 2M"),
            ("signals",   "📡", "Signals"),
            ("stats",     "📈", "Statistics"),
            ("log",       "📋", "Experience Log"),
            ("settings",  "⚙️", "Settings"),
        ]

        for key, icon, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {icon}   {label}",
                font=("Segoe UI", 13),
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=COLORS["text_secondary"],
                hover_color=COLORS["bg_card"],
                anchor="w",
                command=lambda k=key: self.switch_view(k),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

        # ─── Spacer ───
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(fill="both", expand=True)

        # ─── MT5 Status Indicator ───
        self.mt5_status_label = ctk.CTkLabel(
            self.sidebar, text="● MT5: Offline",
            font=("Segoe UI", 11),
            text_color=COLORS["accent_red"],
            anchor="w",
        )
        self.mt5_status_label.pack(fill="x", padx=20, pady=2)

        self.ai_status_label = ctk.CTkLabel(
            self.sidebar, text="● AI: Offline",
            font=("Segoe UI", 11),
            text_color=COLORS["accent_red"],
            anchor="w",
        )
        self.ai_status_label.pack(fill="x", padx=20, pady=2)

        self.tg_status_label = ctk.CTkLabel(
            self.sidebar, text="● Telegram: Offline",
            font=("Segoe UI", 11),
            text_color=COLORS["accent_red"],
            anchor="w",
        )
        self.tg_status_label.pack(fill="x", padx=20, pady=(2, 15))

    # ─────────────────────────────────────────────────────────
    # CONTENT AREA
    # ─────────────────────────────────────────────────────────
    def _create_content_area(self):
        self.content_area = ctk.CTkFrame(
            self, corner_radius=0,
            fg_color=COLORS["bg_dark"],
        )
        self.content_area.pack(side="left", fill="both", expand=True)

    # ─────────────────────────────────────────────────────────
    # STATUS BAR
    # ─────────────────────────────────────────────────────────
    def _create_status_bar(self):
        self.status_bar = ctk.CTkFrame(
            self.content_area, height=32, corner_radius=0,
            fg_color=COLORS["bg_card"],
            border_width=0,
        )
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)

        self.status_text = ctk.CTkLabel(
            self.status_bar,
            text="  ⏳ Đang khởi động hệ thống...",
            font=("Segoe UI", 11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.status_text.pack(side="left", padx=10)

        self.status_right = ctk.CTkLabel(
            self.status_bar,
            text="v2.0  ",
            font=("Segoe UI", 10),
            text_color=COLORS["text_muted"],
            anchor="e",
        )
        self.status_right.pack(side="right", padx=10)

    # ─────────────────────────────────────────────────────────
    # VIEW MANAGEMENT
    # ─────────────────────────────────────────────────────────
    def register_view(self, name: str, view_class, **kwargs):
        """Đăng ký view (gọi từ main.py sau khi init)"""
        self.views[name] = {
            "class": view_class,
            "instance": None,
            "kwargs": kwargs,
        }

    def switch_view(self, name: str):
        """Chuyển sang view khác — highlight nav button"""
        if name not in self.views:
            return

        # Deactivate current
        if self.current_view_name and self.current_view_name in self.views:
            old = self.views[self.current_view_name].get("instance")
            if old:
                old.pack_forget()

        # Update nav button colors
        for key, btn in self.nav_buttons.items():
            if key == name:
                btn.configure(
                    fg_color=COLORS["accent_blue"],
                    text_color="#ffffff",
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS["text_secondary"],
                )

        # Create or show view
        view_info = self.views[name]
        if view_info["instance"] is None:
            view_info["instance"] = view_info["class"](
                self.content_area,
                app=self,
                **view_info["kwargs"]
            )

        view_info["instance"].pack(fill="both", expand=True, before=self.status_bar)
        self.current_view_name = name

        # Refresh view
        if hasattr(view_info["instance"], "refresh"):
            view_info["instance"].refresh()

    def get_current_view(self):
        if self.current_view_name and self.current_view_name in self.views:
            return self.views[self.current_view_name].get("instance")
        return None

    # ─────────────────────────────────────────────────────────
    # SIGNAL POLLING (Thread-safe UI update)
    # ─────────────────────────────────────────────────────────
    def _poll_signals(self):
        """Check signal queue và cập nhật UI — gọi từ main thread"""
        try:
            signal = self.dispatcher.get_ui_signal(timeout=0.01)
            if signal:
                self._on_new_signal(signal)
        except Exception:
            pass
        self.after(200, self._poll_signals)

    def _on_new_signal(self, signal):
        """Xử lý signal mới — update UI views"""
        # Update signals view
        sig_view = self.views.get("signals", {}).get("instance")
        if sig_view and hasattr(sig_view, "add_signal"):
            sig_view.add_signal(signal)

        # Update dashboard + V4 dashboard
        dash_view = self.views.get("dashboard", {}).get("instance")
        if dash_view and hasattr(dash_view, "on_new_signal"):
            dash_view.on_new_signal(signal)
        v4_view = self.views.get("v4", {}).get("instance")
        if v4_view and hasattr(v4_view, "on_new_signal"):
            v4_view.on_new_signal(signal)

        # Flash status
        self.set_status(f"🚨 Tín hiệu mới: {signal.direction} {signal.symbol} | Score: {signal.ai_score}/10")

    # ─────────────────────────────────────────────────────────
    # STATUS UPDATES
    # ─────────────────────────────────────────────────────────
    def _update_status(self):
        """Cập nhật trạng thái kết nối mỗi 5 giây"""
        # MT5
        if self.mt5 and self.mt5.connected:
            self.mt5_status_label.configure(
                text="● MT5: Online", text_color=COLORS["accent_green"])
        else:
            self.mt5_status_label.configure(
                text="● MT5: Offline", text_color=COLORS["accent_red"])

        # Gemini
        if self.gemini and self.gemini.ready:
            self.ai_status_label.configure(
                text="● AI: Ready", text_color=COLORS["accent_green"])
        else:
            self.ai_status_label.configure(
                text="● AI: Offline", text_color=COLORS["accent_red"])

        # Trade count
        if self.trade_logger:
            count = self.trade_logger.get_trade_count()
            self.status_right.configure(text=f"DB: {count} trades  |  v2.0  ")

        self.after(5000, self._update_status)

    def set_status(self, text: str):
        """Set status bar text"""
        self.status_text.configure(text=f"  {text}")

    def set_telegram_status(self, online: bool):
        if online:
            self.tg_status_label.configure(
                text="● Telegram: Online", text_color=COLORS["accent_green"])
        else:
            self.tg_status_label.configure(
                text="● Telegram: Offline", text_color=COLORS["accent_red"])
