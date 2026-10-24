"""
=============================================================================
SETTINGS VIEW — Cấu hình API keys, thông số giao dịch
=============================================================================
"""
import os
import sys
import threading
import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS


class SettingsView(ctk.CTkFrame):
    """Tab cài đặt — API keys, MT5 config, trading parameters"""

    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.app = app
        self._entries = {}
        self._build_ui()

    def _build_ui(self):
        # ─── Header ───
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", padx=20, pady=(15, 5))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⚙️  Settings",
            font=("Segoe UI", 22, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkButton(
            header, text="💾 Save All", font=("Segoe UI", 12, "bold"),
            width=120, height=34, corner_radius=8,
            fg_color=COLORS["accent_green"],
            hover_color="#1b8a7a",
            text_color="#ffffff",
            command=self._save_all,
        ).pack(side="right")

        # ─── Scrollable Content ───
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                         scrollbar_button_color=COLORS["border"])
        scroll.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        # ═══════════════════════════════
        # SECTION 1: API KEYS
        # ═══════════════════════════════
        self._section_header(scroll, "🔑  API Keys")

        self._add_input(scroll, "gemini_api_key", "Gemini API Key",
                         "Lấy từ: ai.google.dev/gemini-api", show="•")
        self._add_input(scroll, "telegram_bot_token", "Telegram Bot Token",
                         "Lấy từ: @BotFather trên Telegram", show="•")
        self._add_input(scroll, "telegram_chat_id", "Telegram Chat ID",
                         "Lấy từ: @userinfobot trên Telegram")

        # Test connections
        test_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        test_frame.pack(fill="x", pady=(5, 15))

        ctk.CTkButton(
            test_frame, text="🧪 Test Gemini", font=("Segoe UI", 11),
            width=130, height=30, corner_radius=6,
            fg_color=COLORS["accent_blue"],
            hover_color="#1a47b8",
            text_color="#ffffff",
            command=self._test_gemini,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            test_frame, text="🧪 Test Telegram", font=("Segoe UI", 11),
            width=130, height=30, corner_radius=6,
            fg_color=COLORS["accent_blue"],
            hover_color="#1a47b8",
            text_color="#ffffff",
            command=self._test_telegram,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            test_frame, text="🧪 Connect MT5", font=("Segoe UI", 11),
            width=130, height=30, corner_radius=6,
            fg_color=COLORS["accent_blue"],
            hover_color="#1a47b8",
            text_color="#ffffff",
            command=self._connect_mt5,
        ).pack(side="left")

        self.test_status = ctk.CTkLabel(
            scroll, text="",
            font=("Segoe UI", 11),
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self.test_status.pack(fill="x", pady=(0, 10))

        # ═══════════════════════════════
        # SECTION 2: TRADING PARAMETERS
        # ═══════════════════════════════
        self._section_header(scroll, "📊  Trading Parameters")

        self._add_input(scroll, "mt5_symbols", "Symbols (comma separated)",
                         "VD: XAUUSD,EURUSD,GBPUSD")
        self._add_input(scroll, "mt5_timeframe", "Timeframe",
                         "VD: M1, M5, M15, H1, H4, D1")
        self._add_input(scroll, "min_wick_percent", "Min Wick % (Pin Bar)",
                         "Tối thiểu % râu nến để được coi là Pin Bar")
        self._add_input(scroll, "swing_lookback", "Swing Lookback",
                         "Số nến tìm đáy/đỉnh cũ để quét thanh khoản")
        self._add_input(scroll, "rr_target", "R:R Target",
                         "Mục tiêu Risk:Reward ratio (VD: 3.0 = 1:3)")
        self._add_input(scroll, "scan_interval_sec", "Scan Interval (sec)",
                         "Khoảng thời gian giữa mỗi lần quét (giây)")
        self._add_input(scroll, "lookback_bars", "Historical Lookback",
                         "Số nến lịch sử để quét xây dựng kinh nghiệm")
        self._add_input(scroll, "v4_preset", "V4 Preset",
                         "conservative | balanced | aggressive (AI-first, cần restart app để áp dụng)")
        self._add_input(scroll, "v4_max_ai_per_minute", "V4 Max AI / phút",
                         "Giới hạn gọi Gemini mỗi phút cho mọi symbol")
        self._add_input(scroll, "v4_top_n_per_scan", "V4 Top ứng viên / lần quét",
                         "Số ứng viên mạnh nhất được đưa cho AI mỗi lần quét")

        # ═══════════════════════════════
        # SECTION 3: AUTO SETTINGS
        # ═══════════════════════════════
        self._section_header(scroll, "🤖  Automation")

        self.auto_scan_var = ctk.BooleanVar(value=True)
        self.auto_tg_var = ctk.BooleanVar(value=True)

        auto_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        auto_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkSwitch(
            auto_frame, text="  Auto Scan MT5 (Realtime)",
            font=("Segoe UI", 12),
            text_color=COLORS["text_primary"],
            variable=self.auto_scan_var,
            progress_color=COLORS["accent_green"],
            button_color=COLORS["text_secondary"],
        ).pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkSwitch(
            auto_frame, text="  Auto Send to Telegram",
            font=("Segoe UI", 12),
            text_color=COLORS["text_primary"],
            variable=self.auto_tg_var,
            progress_color=COLORS["accent_green"],
            button_color=COLORS["text_secondary"],
        ).pack(fill="x", padx=15, pady=(5, 10))

        # ═══════════════════════════════
        # SECTION 4: DATABASE
        # ═══════════════════════════════
        self._section_header(scroll, "💾  Database")

        db_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        db_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            db_frame, text="📂 Open Data Folder", font=("Segoe UI", 11),
            width=150, height=30, corner_radius=6,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self._open_data_folder,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            db_frame, text="💿 Backup Database", font=("Segoe UI", 11),
            width=150, height=30, corner_radius=6,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border_light"],
            text_color=COLORS["text_secondary"],
            command=self._backup_db,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            db_frame, text="🔍 Build Experience", font=("Segoe UI", 11),
            width=150, height=30, corner_radius=6,
            fg_color=COLORS["accent_yellow"],
            hover_color="#d4790f",
            text_color="#000000",
            command=self._build_experience,
        ).pack(side="left")

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────
    def _section_header(self, parent, text):
        ctk.CTkFrame(parent, height=1, fg_color=COLORS["border"]).pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 15, "bold"),
                      text_color=COLORS["text_primary"], anchor="w").pack(fill="x", pady=(5, 10))

    def _add_input(self, parent, key, label, hint="", show=None):
        """Add an input field with label and hint"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(frame, text=label, font=("Segoe UI", 12),
                      text_color=COLORS["text_primary"], anchor="w").pack(fill="x")

        # Get current value
        current_val = ""
        if self.app and self.app.settings:
            val = self.app.settings.get(key, "")
            if isinstance(val, list):
                current_val = ",".join(val)
            else:
                current_val = str(val) if val else ""

        entry = ctk.CTkEntry(
            frame, font=("Consolas", 12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text=hint,
            placeholder_text_color=COLORS["text_muted"],
            height=36, corner_radius=8,
            show=show,
        )
        entry.pack(fill="x", pady=(3, 0))
        if current_val:
            entry.insert(0, current_val)

        self._entries[key] = entry

    # ─────────────────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────────────────
    def _save_all(self):
        if not self.app or not self.app.settings:
            return

        for key, entry in self._entries.items():
            val = entry.get().strip()
            if key == "mt5_symbols":
                val = [s.strip() for s in val.split(",") if s.strip()]
            elif key in ["min_wick_percent", "rr_target"]:
                try:
                    val = float(val)
                except ValueError:
                    continue
            elif key in ["swing_lookback", "scan_interval_sec", "lookback_bars", "v4_max_ai_per_minute", "v4_top_n_per_scan"]:
                try:
                    val = int(val)
                except ValueError:
                    continue
            self.app.settings.set(key, val)

        # Save auto settings
        self.app.settings.set("auto_scan", self.auto_scan_var.get())
        self.app.settings.set("auto_telegram", self.auto_tg_var.get())

        self.app.settings.save()
        self.app.set_status("💾 Settings đã được lưu!")

        # Update Gemini key if changed
        gemini_key = self.app.settings.get_api_key("gemini_api_key")
        if gemini_key and self.app.gemini:
            self.app.gemini.update_key(gemini_key)

    def _test_gemini(self):
        self._save_all()
        key = self._entries.get("gemini_api_key")
        if not key or not key.get().strip():
            self.test_status.configure(text="⚠️ Vui lòng nhập Gemini API Key trước!",
                                        text_color=COLORS["accent_red"])
            return

        self.test_status.configure(text="⏳ Đang test Gemini API...",
                                    text_color=COLORS["text_secondary"])

        def do_test():
            if self.app and self.app.gemini:
                success = self.app.gemini.update_key(key.get().strip())
                if success:
                    self.after(0, lambda: self.test_status.configure(
                        text="✅ Gemini API hoạt động!",
                        text_color=COLORS["accent_green"]))
                else:
                    self.after(0, lambda: self.test_status.configure(
                        text="❌ Gemini API Key không hợp lệ!",
                        text_color=COLORS["accent_red"]))

        threading.Thread(target=do_test, daemon=True).start()

    def _test_telegram(self):
        self._save_all()
        token = self._entries.get("telegram_bot_token")
        if not token or not token.get().strip():
            self.test_status.configure(text="⚠️ Vui lòng nhập Telegram Bot Token!",
                                        text_color=COLORS["accent_red"])
            return

        self.test_status.configure(text="⏳ Đang test Telegram Bot...",
                                    text_color=COLORS["text_secondary"])

        def do_test():
            try:
                import telebot
                test_bot = telebot.TeleBot(token.get().strip())
                info = test_bot.get_me()
                self.after(0, lambda: self.test_status.configure(
                    text=f"✅ Bot: @{info.username} hoạt động!",
                    text_color=COLORS["accent_green"]))
            except Exception as e:
                self.after(0, lambda: self.test_status.configure(
                    text=f"❌ Lỗi Telegram: {str(e)[:80]}",
                    text_color=COLORS["accent_red"]))

        threading.Thread(target=do_test, daemon=True).start()

    def _connect_mt5(self):
        self.test_status.configure(text="⏳ Đang kết nối MT5...",
                                    text_color=COLORS["text_secondary"])

        def do_connect():
            if self.app and self.app.mt5:
                ok, msg = self.app.mt5.connect()
                color = COLORS["accent_green"] if ok else COLORS["accent_red"]
                self.after(0, lambda: self.test_status.configure(
                    text=msg, text_color=color))

        threading.Thread(target=do_connect, daemon=True).start()

    def _open_data_folder(self):
        from config import DATA_DIR
        try:
            os.startfile(DATA_DIR)
        except Exception:
            self.app.set_status(f"📂 Data folder: {DATA_DIR}")

    def _backup_db(self):
        if self.app and self.app.trade_logger:
            path = self.app.trade_logger.backup()
            if path:
                self.app.set_status(f"💿 Backup saved: {os.path.basename(path)}")
            else:
                self.app.set_status("⚠️ Không có database để backup.")

    def _build_experience(self):
        """Quét nến cũ trên MT5 để xây dựng database kinh nghiệm"""
        if not self.app or not self.app.mt5 or not self.app.mt5.connected:
            self.test_status.configure(
                text="⚠️ Kết nối MT5 trước khi build experience!",
                text_color=COLORS["accent_red"])
            return

        self.test_status.configure(
            text="⏳ Đang quét nến lịch sử để xây dựng kinh nghiệm...",
            text_color=COLORS["accent_yellow"])
        self.app.set_status("🔍 Building experience database from MT5 history...")

        def do_build():
            total_found = 0
            for symbol in self.app.mt5.symbols:
                setups = self.app.mt5.scan_historical_setups(symbol)
                for s in setups:
                    s["trade_id"] = self.app.trade_logger.get_next_id()
                    self.app.trade_logger.log_trade(s)
                total_found += len(setups)

            self.after(0, lambda: self.test_status.configure(
                text=f"✅ Đã tìm thấy {total_found} setup lịch sử và ghi vào database!",
                text_color=COLORS["accent_green"]))
            self.after(0, lambda: self.app.set_status(
                f"✅ Experience built: {total_found} historical setups logged!"))

        threading.Thread(target=do_build, daemon=True).start()

    def refresh(self):
        """Reload current settings into fields"""
        if not self.app or not self.app.settings:
            return

        for key, entry in self._entries.items():
            val = self.app.settings.get(key, "")
            if isinstance(val, list):
                val = ",".join(val)
            else:
                val = str(val) if val else ""

            entry.delete(0, "end")
            if val:
                entry.insert(0, val)

        self.auto_scan_var.set(self.app.settings.get("auto_scan", True))
        self.auto_tg_var.set(self.app.settings.get("auto_telegram", True))
