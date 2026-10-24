"""
=============================================================================
GEMINI TRADE BOT PRO v2.0 — ENTRY POINT
- Khởi chạy Desktop Trading Dashboard UI (CustomTkinter)
- Bắn tín hiệu song song: Telegram Channel/Group + Desktop UI Feed
- Tự động quét nến MT5 & Thư mục EA mt5_signals/
- Tích hợp bộ não Gemini AI Vision & Quant Performance Engine
=============================================================================
"""
import os
import sys
import time
import glob
import logging
import threading
from datetime import datetime

# Đảm bảo in tiếng Việt trên console Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup root path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import (
    SettingsManager, CSV_FILE, MT5_SIGNALS_DIR, CHARTS_DIR, REPORT_IMG_PATH
)
from core import (
    TradeLogger, QuantEngine, GeminiBrain, SignalDispatcher, Signal,
    MT5Connector, SMCSetup
)
from telegram_bot import TelegramBotHandler
from ui import (
    AppWindow, DashboardView, BacktestView, SignalsView, StatsView, LogView, SettingsView
)


class BotController:
    """Điều phối toàn bộ luồng hoạt động giữa MT5, AI Brain, UI và Telegram"""

    def __init__(self):
        print("⚡ Khởi động Gemini Trade Bot Pro v2.0...")
        # 1. Cấu hình
        self.settings = SettingsManager()

        # 2. Database & Quant
        self.trade_logger = TradeLogger(CSV_FILE)
        self.quant_engine = QuantEngine(self.trade_logger)

        # 3. AI Brain
        gemini_key = self.settings.get_api_key("gemini_api_key")
        self.gemini_brain = GeminiBrain(api_key=gemini_key)

        # 4. Dispatcher
        self.dispatcher = SignalDispatcher()

        # 5. MT5 Data Connector
        symbols = self.settings.get("mt5_symbols", ["XAUUSD", "EURUSD", "GBPUSD"])
        tf = self.settings.get("mt5_timeframe", "M5")
        lookback = self.settings.get("lookback_bars", 500)
        self.mt5 = MT5Connector(symbols=symbols, timeframe_str=tf, lookback=lookback)

        # 6. Telegram Bot Handler
        tg_token = self.settings.get_api_key("telegram_bot_token")
        tg_chat_id = self.settings.get_api_key("telegram_chat_id")
        self.tele_bot = TelegramBotHandler(
            token=tg_token,
            chat_id=tg_chat_id,
            dispatcher=self.dispatcher,
            gemini_brain=self.gemini_brain,
            quant_engine=self.quant_engine,
            trade_logger=self.trade_logger,
            mt5_connector=self.mt5,
            settings_mgr=self.settings,
            on_status_change=self._on_tg_status_change,
        )

        # 7. UI Desktop Window
        self.app = AppWindow(
            dispatcher=self.dispatcher,
            trade_logger=self.trade_logger,
            quant_engine=self.quant_engine,
            mt5_connector=self.mt5,
            gemini_brain=self.gemini_brain,
            settings_mgr=self.settings,
        )

        # Đăng ký các tab vào AppWindow
        self.app.register_view("dashboard", DashboardView)
        self.app.register_view("backtest", BacktestView)
        self.app.register_view("signals", SignalsView)
        self.app.register_view("stats", StatsView)
        self.app.register_view("log", LogView)
        self.app.register_view("settings", SettingsView)

        # 8. Trạng thái chạy ngầm
        self.is_running = True
        self.processed_ea_files = set()

    def _on_tg_status_change(self, online: bool):
        if hasattr(self, "app") and self.app:
            try:
                self.app.after(0, lambda: self.app.set_telegram_status(online))
            except Exception:
                pass

    def start_background_services(self):
        """Khởi động luồng quét tự động MT5 và folder watcher"""
        # Telegram Polling
        if self.tele_bot.token:
            self.tele_bot.start()

        # MT5 Auto Connect nếu có thể
        threading.Thread(target=self._auto_connect_mt5, daemon=True).start()

        # Scanner & Watcher Thread
        self.scanner_thread = threading.Thread(target=self._scanner_worker, daemon=True, name="ScannerThread")
        self.scanner_thread.start()

    def _auto_connect_mt5(self):
        """Thử kết nối MT5 tự động khi khởi động"""
        if self.mt5.is_available:
            ok, msg = self.mt5.connect()
            print(f"[MT5] {msg}")
            if ok and hasattr(self, "app"):
                self.app.set_status("✅ MT5 đã kết nối thành công")

    def _scanner_worker(self):
        """
        Luồng background:
        1. Theo dõi file ảnh/signal mới do EA MT5 chụp vào mt5_signals/
        2. Quét thêm thư mục MQL5/Files/mt5_signals của MT5 terminal
        3. Tự động quét nến trực tiếp qua MT5 API nếu bật auto_scan
        """
        # Tìm thêm thư mục MT5 Files để sync file từ EA
        mt5_files_dirs = self._discover_mt5_signal_dirs()

        while self.is_running:
            try:
                # ─── A. KIỂM TRA ẢNH TỪ EA BRIDGE (mt5_signals/*.png) ───
                all_signal_dirs = [MT5_SIGNALS_DIR] + mt5_files_dirs
                for sig_dir in all_signal_dirs:
                    if not os.path.exists(sig_dir):
                        continue
                    # Quét file ảnh PNG
                    png_files = glob.glob(os.path.join(sig_dir, "*.png"))
                    for img_file in png_files:
                        if img_file not in self.processed_ea_files:
                            self.processed_ea_files.add(img_file)
                            self._process_ea_screenshot(img_file)

                    # Quét file .signal từ EA Bridge
                    signal_files = glob.glob(os.path.join(sig_dir, "*.signal"))
                    for sig_file in signal_files:
                        if sig_file not in self.processed_ea_files:
                            self.processed_ea_files.add(sig_file)
                            self._process_ea_signal_file(sig_file)

                # ─── B. TỰ ĐỘNG QUÉT NẾN QUA MT5 API ───
                if self.settings.get("auto_scan", True) and self.mt5.connected:
                    symbols = self.settings.get("mt5_symbols", ["XAUUSD", "EURUSD"])
                    tf = self.settings.get("mt5_timeframe", "M5")
                    lookback_swing = self.settings.get("swing_lookback", 20)
                    min_wick = self.settings.get("min_wick_percent", 55.0)

                    self.mt5.timeframe_str = tf
                    for sym in symbols:
                        setup = self.mt5.detect_smc_setup(sym, swing_lookback=lookback_swing, min_wick_pct=min_wick)
                        if setup:
                            self._process_smc_setup(setup)

            except Exception as e:
                print(f"[ScannerWorker] Lỗi: {e}")

            interval = max(2, self.settings.get("scan_interval_sec", 3))
            time.sleep(interval)

    def _discover_mt5_signal_dirs(self) -> list:
        """Tự tìm thư mục MQL5/Files/mt5_signals của MT5 terminal"""
        dirs = []
        try:
            # Quét các ổ đĩa phổ biến
            for drive in ["C", "D", "E"]:
                base = f"{drive}:\\Program Files"
                if not os.path.exists(base):
                    continue
                for folder in os.listdir(base):
                    if "metatrader" in folder.lower() or "mt5" in folder.lower():
                        mt5_files = os.path.join(base, folder, "MQL5", "Files", "mt5_signals")
                        if os.path.exists(mt5_files):
                            dirs.append(mt5_files)
                            print(f"[EA Bridge] Tìm thấy thư mục MT5: {mt5_files}")

            # Thử thêm AppData
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                mt_roaming = os.path.join(appdata, "MetaQuotes", "Terminal")
                if os.path.exists(mt_roaming):
                    for terminal_id in os.listdir(mt_roaming):
                        sig_path = os.path.join(mt_roaming, terminal_id, "MQL5", "Files", "mt5_signals")
                        if os.path.exists(sig_path):
                            dirs.append(sig_path)
                            print(f"[EA Bridge] Tìm thấy thư mục MT5 AppData: {sig_path}")
        except Exception as e:
            print(f"[EA Bridge] Lỗi quét thư mục MT5: {e}")
        return dirs

    def _process_ea_signal_file(self, signal_path: str):
        """Đọc file .signal do EA Bridge ghi ra, tạo Signal và dispatch"""
        print(f"[!] Phát hiện signal file từ EA: {signal_path}")
        try:
            data = {}
            with open(signal_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, val = line.split("=", 1)
                        data[key.strip()] = val.strip()

            symbol = data.get("symbol", "UNKNOWN")
            direction = data.get("direction", "BUY")
            entry = float(data.get("entry", 0))
            sl = float(data.get("sl", 0))
            tp = float(data.get("tp", 0))
            wick_pct = float(data.get("wick_pct", 0))
            sweep_pips = float(data.get("sweep_pips", 0))
            session = data.get("session", "")
            timeframe = data.get("timeframe", self.settings.get("mt5_timeframe", "M5"))

            # Tìm ảnh chart tương ứng (cùng tên nhưng .png)
            chart_path = signal_path.replace(".signal", ".png")
            if not os.path.exists(chart_path):
                chart_path = ""

            # Gọi AI nếu có ảnh
            ai_verdict = ""
            score = 8.0
            if chart_path and self.gemini_brain.ready:
                stats = self.quant_engine.get_summary()
                stats_summary = f"Database {stats.get('total_trades', 0)} lệnh, Winrate {stats.get('winrate', 0)}%"
                ai_verdict = self.gemini_brain.analyze_chart(chart_path, stats_summary=stats_summary)
            else:
                ai_verdict = f"EA Bridge: {direction} {symbol} | Sweep {sweep_pips}p | Wick {wick_pct}% | {session}"

            from core import Signal
            sig = Signal(
                signal_id=f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                ai_score=score,
                ai_analysis=ai_verdict,
                chart_image_path=chart_path,
                session=session,
                wick_percent=wick_pct,
                sweep_pips=sweep_pips,
                outcome="PENDING",
            )

            self.trade_logger.log_trade(sig.to_dict())
            self.dispatcher.dispatch(sig)
            self.app.set_status(f"📡 EA Bridge: {direction} {symbol} | Wick {wick_pct}%")

        except Exception as e:
            print(f"[EA Bridge] Lỗi đọc signal file: {e}")


    def _process_ea_screenshot(self, img_path: str):
        """Xử lý khi phát hiện file ảnh mới từ EA MT5"""
        print(f"[!] Phát hiện tín hiệu chart mới từ EA: {img_path}")
        self.app.set_status("📸 Nhận chart từ MT5! Gemini AI đang soi nến...")

        # Parse thông tin cơ bản từ filename (VD: XAUUSD_M5_20261024_193000.png)
        filename = os.path.basename(img_path)
        parts = filename.replace(".png", "").split("_")
        symbol = parts[0] if len(parts) > 0 else "UNKNOWN"
        timeframe = parts[1] if len(parts) > 1 else self.settings.get("mt5_timeframe", "M5")

        # Lấy tóm tắt quant data để bổ trợ cho prompt
        stats = self.quant_engine.get_summary()
        stats_summary = (
            f"Database {stats.get('total_trades', 0)} lệnh, Winrate {stats.get('winrate', 0)}%, "
            f"Phiên London đạt winrate cao nhất ({stats.get('best_session', 'London')})."
        )

        # Gọi Gemini phân tích
        ai_verdict = ""
        score = 8.0
        direction = "BUY"
        if self.gemini_brain.ready:
            ai_verdict = self.gemini_brain.analyze_chart(img_path, stats_summary=stats_summary)
            # Parse điểm số & hướng lệnh từ văn bản nếu có
            if "SELL" in ai_verdict.upper() and "BUY" not in ai_verdict.upper():
                direction = "SELL"
            elif "SKIP" in ai_verdict.upper():
                direction = "SKIP"
        else:
            ai_verdict = "Setup SMC hợp lệ được ghi nhận từ EA Bridge. (Gemini AI Offline)"

        # Tạo đối tượng Signal
        sig = Signal(
            signal_id=f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            ai_score=score,
            ai_analysis=ai_verdict,
            chart_image_path=img_path,
            session=datetime.now().strftime("%H:%M"),
            outcome="PENDING",
        )

        # Ghi log ban đầu
        self.trade_logger.log_trade(sig.to_dict())

        # Bắn đồng thời 2 nơi qua Dispatcher!
        self.dispatcher.dispatch(sig)

    def _process_smc_setup(self, setup: SMCSetup):
        """Xử lý khi phát hiện setup SMC từ thuật toán quét nến trực tiếp"""
        print(f"🎯 Phát hiện setup SMC: {setup.direction} {setup.symbol} {setup.timeframe}")
        self.app.set_status(f"🎯 Phát hiện {setup.direction} {setup.symbol}! Đang tạo chart & thẩm định AI...")

        # 1. Render ảnh chart với Entry / SL / TP overlay
        chart_path = self.mt5.render_chart(setup, save_dir=CHARTS_DIR)
        setup.chart_image_path = chart_path

        # 2. Lấy bối cảnh kinh nghiệm từ quant engine
        stats = self.quant_engine.get_summary()
        stats_summary = (
            f"Database {stats.get('total_trades', 0)} trades, Winrate: {stats.get('winrate', 0)}%, "
            f"Phiên hiệu quả nhất: {stats.get('best_session', 'London')}."
        )

        # 3. Gemini Vision phân tích
        ai_verdict = ""
        score = 8.5
        if self.gemini_brain.ready and chart_path and os.path.exists(chart_path):
            ai_verdict = self.gemini_brain.analyze_chart(chart_path, stats_summary=stats_summary)
            # Thử trích xuất score
            try:
                import re
                match = re.search(r"(\d+(\.\d+)?)\s*/\s*10", ai_verdict)
                if match:
                    score = float(match.group(1))
            except Exception:
                pass
        else:
            ai_verdict = (
                f"SMC Setup: Quét thanh khoản đáy cũ {setup.sweep_pips} pips, "
                f"Bullish Pin Bar râu nến {setup.wick_percent}%, phiên {setup.session}."
            )

        setup.ai_score = score
        setup.ai_analysis = ai_verdict

        # 4. Tạo Signal object với Dynamic TP
        sig = Signal(
            signal_id=setup.signal_id or f"{setup.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            symbol=setup.symbol,
            timeframe=setup.timeframe,
            direction=setup.direction,
            entry_price=setup.entry_price,
            stop_loss=setup.stop_loss,
            take_profit=setup.take_profit,
            tp1=setup.tp1,
            tp2=setup.tp2,
            tp3=setup.tp3,
            ai_score=score,
            ai_analysis=ai_verdict,
            chart_image_path=chart_path,
            session=setup.session,
            wick_percent=setup.wick_percent,
            sweep_pips=setup.sweep_pips,
            has_fvg=setup.has_fvg,
            has_ob=setup.has_ob,
            market_structure=setup.market_structure,
            atr=setup.atr,
            outcome="PENDING",
            rr_achieved=0.0,
        )

        # 5. Lưu vào Database kinh nghiệm (trạng thái PENDING)
        self.trade_logger.log_trade(sig.to_dict())

        # 6. Bắn tín hiệu SONG SONG: Desktop UI + Telegram Bot!
        self.dispatcher.dispatch(sig)

    def run(self):
        """Khởi động ứng dụng và vòng lặp GUI"""
        self.start_background_services()

        def on_close():
            print("[*] Đang đóng ứng dụng...")
            self.is_running = False
            self.tele_bot.stop()
            self.mt5.disconnect()
            self.app.destroy()
            sys.exit(0)

        self.app.protocol("WM_DELETE_WINDOW", on_close)
        self.app.mainloop()


if __name__ == "__main__":
    controller = BotController()
    controller.run()
