"""
=============================================================================
CẤU HÌNH HỆ THỐNG GEMINI TRADE BOT PRO v2.0
=============================================================================
"""
import os
import sys
import json

# === Fix encoding Windows ===
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# === Paths ===
if getattr(sys, 'frozen', False):
    # Đang chạy từ file EXE đóng gói
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
else:
    # Đang chạy từ mã nguồn Python
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

DATA_DIR = os.path.join(BASE_DIR, "bot_data")
CSV_FILE = os.path.join(DATA_DIR, "trade_history.csv")
MT5_SIGNALS_DIR = os.path.join(DATA_DIR, "mt5_signals")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
REPORT_IMG_PATH = os.path.join(DATA_DIR, "performance_report.png")
ASSETS_DIR = os.path.join(BUNDLE_DIR, "assets")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# === Create directories ===
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MT5_SIGNALS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# === UI Color Palette (TradingView Dark Mode) ===
COLORS = {
    "bg_darkest":     "#0f1117",
    "bg_dark":        "#131722",
    "bg_card":        "#1e222d",
    "bg_sidebar":     "#161a25",
    "bg_input":       "#2a2e39",
    "border":         "#2a2e39",
    "border_light":   "#363a45",
    "text_primary":   "#d1d4dc",
    "text_secondary": "#787b86",
    "text_muted":     "#4a4e59",
    "accent_green":   "#26a69a",
    "accent_red":     "#ef5350",
    "accent_blue":    "#2962ff",
    "accent_yellow":  "#f7931a",
    "accent_cyan":    "#00e5ff",
    "win":            "#26a69a",
    "loss":           "#ef5350",
    "buy":            "#26a69a",
    "sell":           "#ef5350",
    "skip":           "#787b86",
}


# =============================================================================
# SETTINGS MANAGER — Load/Save từ JSON, UI Settings có thể thay đổi runtime
# =============================================================================
class SettingsManager:
    """Quản lý cấu hình persistent — lưu/đọc từ file JSON"""

    _DEFAULTS = {
        "gemini_api_key": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "mt5_symbols": ["XAUUSD", "EURUSD", "GBPUSD"],
        "mt5_timeframe": "M5",
        "min_wick_percent": 55.0,
        "swing_lookback": 20,
        "scan_interval_sec": 3,
        "auto_telegram": True,
        "auto_scan": True,
        "rr_target": 3.0,
        "lookback_bars": 500,
        # V4 — AI-first. v4_enabled=True routes the live scanner through
        # V4Engine; False keeps the legacy sweep+pinbar scanner.
        "v4_enabled": True,
        "v4_preset": "balanced",  # conservative | balanced | aggressive
        "v4_max_ai_per_minute": 10,
        "v4_top_n_per_scan": 5,
    }

    def __init__(self, path=None):
        self.path = path or SETTINGS_FILE
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                return {**self._DEFAULTS, **saved}
            except Exception:
                pass
        return dict(self._DEFAULTS)

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get(self, key, fallback=None):
        return self.data.get(key, fallback if fallback is not None else self._DEFAULTS.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def get_api_key(self, key):
        """Ưu tiên env var, nếu không có thì lấy từ settings"""
        env_map = {
            "gemini_api_key": "GEMINI_API_KEY",
            "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
            "telegram_chat_id": "TELEGRAM_CHAT_ID",
        }
        env_val = os.environ.get(env_map.get(key, ""), "")
        return env_val if env_val else self.data.get(key, "")
