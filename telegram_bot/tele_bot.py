"""
=============================================================================
TELEGRAM BOT HANDLER — Bắn tín hiệu và tương tác qua Telegram
- Bắn signal song song (ảnh chart + entry/SL/TP + AI analysis)
- Tương tác 2 chiều: /stats, /report, /win, /loss, /scan, /status
- Nhận ảnh chart gửi trực tiếp từ điện thoại -> Gemini soi nến ngay
- Quản lý luồng polling thread-safe, tự động reconnect
=============================================================================
"""
import os
import sys
import time
import glob
import logging
import threading
from datetime import datetime
from typing import Optional, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, REPORT_IMG_PATH

try:
    import telebot
    from telebot import types
    TELEBOT_AVAILABLE = True
except ImportError:
    TELEBOT_AVAILABLE = False


class TelegramBotHandler:
    """
    Quản lý kết nối và gửi nhận tin nhắn Telegram
    Chạy background thread, thread-safe dispatch và auto-reconnect
    """

    def __init__(self, token: str = "", chat_id: str = "", dispatcher=None,
                 gemini_brain=None, quant_engine=None, trade_logger=None,
                 mt5_connector=None, settings_mgr=None, on_status_change: Optional[Callable[[bool], None]] = None):
        self.token = token.strip()
        self.chat_id = chat_id.strip()
        self.dispatcher = dispatcher
        self.gemini = gemini_brain
        self.quant = quant_engine
        self.logger = trade_logger
        self.mt5 = mt5_connector
        self.settings = settings_mgr
        self.on_status_change = on_status_change

        self.bot: Optional[telebot.TeleBot] = None
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Đăng ký nhận signal từ dispatcher nếu có
        if self.dispatcher:
            self.dispatcher.register_callback(self.send_signal)

        # Khởi tạo bot nếu có token hợp lệ
        if self.token and TELEBOT_AVAILABLE:
            self._init_bot()

    def _init_bot(self):
        """Khởi tạo instance bot và đăng ký các command handlers"""
        try:
            self.bot = telebot.TeleBot(self.token, parse_mode=None)
            self._register_handlers()
            return True
        except Exception as e:
            print(f"[TelegramBot] Lỗi khởi tạo TeleBot: {e}")
            self.bot = None
            return False

    def update_credentials(self, token: str, chat_id: str):
        """Cập nhật token/chat_id runtime và restart bot"""
        was_running = self.is_running
        self.stop()
        self.token = token.strip()
        self.chat_id = chat_id.strip()
        if self.token and TELEBOT_AVAILABLE:
            self._init_bot()
            if was_running:
                self.start()

    def start(self):
        """Bắt đầu chạy bot polling trên thread riêng"""
        if not TELEBOT_AVAILABLE:
            print("[TelegramBot] pyTelegramBotAPI chưa được cài đặt")
            return False

        if not self.bot or not self.token:
            print("[TelegramBot] Chưa có token Telegram hợp lệ")
            return False

        if self.is_running:
            return True

        self.is_running = True
        self._thread = threading.Thread(target=self._polling_worker, daemon=True, name="TelegramPollThread")
        self._thread.start()
        return True

    def stop(self):
        """Dừng bot polling"""
        self.is_running = False
        if self.bot:
            try:
                self.bot.stop_polling()
            except Exception:
                pass
        if self.on_status_change:
            try:
                self.on_status_change(False)
            except Exception:
                pass

    def _notify_status(self, online: bool):
        if self.on_status_change:
            try:
                self.on_status_change(online)
            except Exception:
                pass

    def _polling_worker(self):
        """Vòng lặp polling bảo vệ tự phục hồi khi mất kết nối"""
        print("[TelegramBot] Bắt đầu lắng nghe tin nhắn...")
        self._notify_status(True)

        while self.is_running:
            try:
                if self.bot:
                    self.bot.infinity_polling(timeout=20, long_polling_timeout=20)
                else:
                    break
            except Exception as e:
                print(f"[TelegramBot] Lỗi polling: {e}. Thử lại sau 5s...")
                self._notify_status(False)
                time.sleep(5)
                if self.is_running:
                    self._notify_status(True)

        self._notify_status(False)
        print("[TelegramBot] Đã dừng polling.")

    # ─────────────────────────────────────────────────────────
    # SIGNAL BROADCASTING
    # ─────────────────────────────────────────────────────────
    def send_signal(self, signal):
        """
        Bắn signal tới Telegram channel/group/chat:
        - Nếu có ảnh chart -> gửi Photo + Caption
        - Nếu không có ảnh -> gửi Text Markdown
        """
        if not self.bot or not self.chat_id:
            return False

        # Kiểm tra setting auto_telegram
        if self.settings and not self.settings.get("auto_telegram", True):
            return False

        text = signal.format_telegram()
        img_path = getattr(signal, "chart_image_path", "")

        try:
            if img_path and os.path.exists(img_path):
                with open(img_path, "rb") as photo:
                    self.bot.send_photo(
                        self.chat_id,
                        photo,
                        caption=text,
                        parse_mode="Markdown"
                    )
            else:
                self.bot.send_message(
                    self.chat_id,
                    text,
                    parse_mode="Markdown"
                )
            print(f"[TelegramBot] ✅ Đã gửi signal {signal.direction} {signal.symbol} tới Telegram")
            return True
        except Exception as e:
            # Nếu lỗi Markdown parse, thử gửi plain text
            try:
                plain_text = text.replace("*", "").replace("`", "")
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as photo:
                        self.bot.send_photo(self.chat_id, photo, caption=plain_text)
                else:
                    self.bot.send_message(self.chat_id, plain_text)
                return True
            except Exception as e2:
                print(f"[TelegramBot] Lỗi gửi signal: {e2}")
                return False

    def send_notification(self, message: str, parse_mode: Optional[str] = "Markdown"):
        """Gửi thông báo nhanh đến admin/channel"""
        if not self.bot or not self.chat_id:
            return False
        try:
            self.bot.send_message(self.chat_id, message, parse_mode=parse_mode)
            return True
        except Exception as e:
            print(f"[TelegramBot] Lỗi send_notification: {e}")
            return False

    # ─────────────────────────────────────────────────────────
    # COMMAND HANDLERS
    # ─────────────────────────────────────────────────────────
    def _register_handlers(self):
        bot = self.bot
        if not bot:
            return

        @bot.message_handler(commands=['bind'])
        def handle_bind(message):
            cid = str(message.chat.id)
            self.chat_id = cid
            if self.settings:
                self.settings.set("telegram_chat_id", cid)
            bot.reply_to(
                message,
                f"🎉 *BẮN TÍN HIỆU ĐÃ KẾT NỐI!*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Đã bind thành công Chat ID: `{cid}`\n"
                f"📡 Tín hiệu giao dịch và phân tích AI sẽ được gửi trực tiếp đến đây!",
                parse_mode="Markdown"
            )

        @bot.message_handler(commands=['start', 'help'])
        def handle_start(message):
            # Tự động gán chat_id nếu chưa có
            if not self.chat_id:
                self.chat_id = str(message.chat.id)
                if self.settings:
                    self.settings.set("telegram_chat_id", self.chat_id)

            text = (
                "⚡ *GEMINI TRADE BOT PRO v3.0*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Hệ thống phân tích SMC & Bắn tín hiệu giao dịch kép (Desktop UI + Telegram).\n\n"
                f"🆔 *Chat ID của bạn:* `{message.chat.id}` (Đã kết nối)\n\n"
                "📋 *DANH SÁCH LỆNH:*\n"
                "• /bind — Khóa/Liên kết chat ID nhận tín hiệu\n"
                "• /stats — Xem tóm tắt hiệu suất & Winrate hiện tại\n"
                "• /backtest — Kích hoạt quét nến 2 tháng MT5 & phân tích phong độ\n"
                "• /report — Xuất biểu đồ phân tích 4 khung hình ảnh\n"
                "• /status — Kiểm tra trạng thái MT5, AI, DB\n"
                "• /scan — Kích hoạt quét thị trường ngay lập tức\n"
                "• /win `[trade_id]` `[rr]` — Xác nhận lệnh Thắng (mặc định R:R=3)\n"
                "• /loss `[trade_id]` — Xác nhận lệnh Thua\n"
                "• /demo — Tạo 30 lệnh mẫu để test đồ thị ngay\n\n"
                "📸 *Tính năng đặc biệt:* Gửi trực tiếp ảnh chart vào chat này, bộ não Gemini Vision sẽ soi SMC ngay lập tức!"
            )
            bot.reply_to(message, text, parse_mode="Markdown")

        @bot.message_handler(commands=['status'])
        def handle_status(message):
            mt5_stat = "🟢 Online" if (self.mt5 and getattr(self.mt5, "connected", False)) else "🔴 Offline"
            ai_stat = "🟢 Ready" if (self.gemini and getattr(self.gemini, "ready", False)) else "🔴 Offline"
            trade_count = self.logger.get_trade_count() if self.logger else 0

            text = (
                "📊 *TRẠNG THÁI HỆ THỐNG:*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"• MT5 Connector: {mt5_stat}\n"
                f"• Gemini AI Brain: {ai_stat}\n"
                f"• Database Lịch sử: {trade_count} trades\n"
                f"• Chat ID hiện tại: `{message.chat.id}`\n"
                f"• Thời gian server: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            bot.reply_to(message, text, parse_mode="Markdown")

        @bot.message_handler(commands=['stats'])
        def handle_stats(message):
            if not self.quant:
                bot.reply_to(message, "⚠️ Quantitative Engine chưa khởi tạo.")
                return

            summary = self.quant.get_summary()
            winrate = summary.get("winrate", 0.0)
            total = summary.get("total_trades", 0)
            total_r = summary.get("total_r", 0.0)
            avg_rr = summary.get("avg_rr", 0.0)
            wins = summary.get("wins", 0)
            losses = summary.get("losses", 0)

            sign = "+" if total_r > 0 else ""
            text = (
                "📈 *THỐNG KÊ HIỆU SUẤT HIỆN TẠI*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"• Tổng số lệnh: *{total}* ({wins} Thắng / {losses} Thua)\n"
                f"• Tỷ lệ thắng (Winrate): *{winrate}%*\n"
                f"• Tổng lợi nhuận R: *{sign}{total_r:.1f}R*\n"
                f"• R:R trung bình: *1:{avg_rr:.2f}*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💡 Gõ /report để nhận biểu đồ phân tích 4 khung trực quan!"
            )
            bot.reply_to(message, text, parse_mode="Markdown")

        @bot.message_handler(commands=['report'])
        def handle_report(message):
            if not self.quant:
                bot.reply_to(message, "⚠️ Quant Engine chưa sẵn sàng.")
                return

            bot.send_message(message.chat.id, "⏳ Đang tổng hợp dữ liệu & vẽ biểu đồ hiệu suất...")

            img_path = self.quant.generate_report_image(REPORT_IMG_PATH)
            if img_path and os.path.exists(img_path):
                summary = self.quant.get_summary()
                caption = (
                    f"📊 *BÁO CÁO PHÂN TÍCH ĐỊNH LƯỢNG*\n"
                    f"Winrate: {summary.get('winrate', 0)}% | Total: {summary.get('total_r', 0)}R | Trades: {summary.get('total_trades', 0)}\n"
                    f"🧠 Dữ liệu cập nhật realtime từ các lệnh thực chiến."
                )
                with open(img_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=caption, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "⚠️ Chưa đủ dữ liệu lệnh để vẽ biểu đồ. Hãy thử gõ /demo để tạo dữ liệu mẫu!")

        @bot.message_handler(commands=['win'])
        def handle_win(message):
            if not self.logger:
                bot.reply_to(message, "⚠️ Trade Logger chưa sẵn sàng.")
                return

            parts = message.text.split()
            # /win [trade_id] [rr]
            rr = 3.0
            trade_id = None
            if len(parts) >= 2:
                try:
                    rr = float(parts[1])
                except ValueError:
                    trade_id = parts[1]
            if len(parts) >= 3:
                try:
                    rr = float(parts[2])
                except ValueError:
                    pass

            success = self.logger.log_outcome(trade_id=trade_id, outcome="WIN", rr_achieved=rr)
            if success:
                bot.reply_to(message, f"✅ Đã ghi nhận lệnh **WIN** (+{rr}R) vào kho kinh nghiệm!", parse_mode="Markdown")
            else:
                bot.reply_to(message, f"❌ Không tìm thấy lệnh phù hợp để cập nhật.")

        @bot.message_handler(commands=['loss'])
        def handle_loss(message):
            if not self.logger:
                bot.reply_to(message, "⚠️ Trade Logger chưa sẵn sàng.")
                return

            parts = message.text.split()
            trade_id = parts[1] if len(parts) >= 2 else None
            success = self.logger.log_outcome(trade_id=trade_id, outcome="LOSS", rr_achieved=-1.0)
            if success:
                bot.reply_to(message, "🛑 Đã ghi nhận lệnh **LOSS** (-1R) vào kho kinh nghiệm!", parse_mode="Markdown")
            else:
                bot.reply_to(message, "❌ Không tìm thấy lệnh phù hợp để cập nhật.")

        @bot.message_handler(commands=['demo', 'demo_data'])
        def handle_demo(message):
            if not self.logger:
                bot.reply_to(message, "⚠️ Trade Logger chưa sẵn sàng.")
                return

            count = self.logger.generate_sample_data(n=30)
            bot.reply_to(message, f"🎉 Đã nạp thành công {count} lệnh mẫu thực tế vào database!\nGõ /stats hoặc /report để xem kết quả phân tích.")

        @bot.message_handler(commands=['scan'])
        def handle_scan(message):
            if not self.mt5:
                bot.reply_to(message, "⚠️ MT5 Connector chưa sẵn sàng.")
                return

            bot.reply_to(message, "🔍 Đang kích hoạt quét quét SMC trên MT5...")
            symbols = self.settings.get("mt5_symbols", ["XAUUSD", "EURUSD"]) if self.settings else ["XAUUSD"]
            tf = self.settings.get("mt5_timeframe", "M5") if self.settings else "M5"

            found = 0
            for sym in symbols:
                setup = self.mt5.detect_smc_setup(sym, tf)
                if setup:
                    found += 1
                    # Dispatch setup
                    if hasattr(self.mt5, "dispatch_setup"):
                        self.mt5.dispatch_setup(setup)

            if found == 0:
                bot.send_message(message.chat.id, f"ℹ️ Không có setup SMC mới nào đạt tiêu chí trên các cặp {symbols}.")
            else:
                bot.send_message(message.chat.id, f"🎯 Đã phát hiện và phát đi {found} setup mới!")

        @bot.message_handler(commands=['backtest'])
        def handle_backtest(message):
            if not self.mt5 or not getattr(self.mt5, "connected", False):
                bot.reply_to(message, "⚠️ MT5 chưa kết nối. Đang thử kết nối...")
                if self.mt5:
                    self.mt5.connect()
                if not self.mt5 or not getattr(self.mt5, "connected", False):
                    bot.reply_to(message, "❌ Không kết nối được MT5. Vui lòng mở phần mềm MT5 trên máy tính!")
                    return

            bot.reply_to(message, "⏳ Đang quét 15.000 nến (2 tháng gần nhất) trên MT5 & phân tích setup SMC...")

            def run_bt():
                try:
                    symbols = self.settings.get("mt5_symbols", ["XAUUSD", "EURUSD"]) if self.settings else ["XAUUSD"]
                    setups = self.mt5.backtest_historical_range(symbols=symbols, lookback_bars=15000)
                    if setups and self.logger:
                        self.logger.log_trades_batch(setups)

                    total = len(setups)
                    wins = len([s for s in setups if s.get("outcome") in ["WIN", "PARTIAL"]])
                    losses = len([s for s in setups if s.get("outcome") == "LOSS"])
                    wr = round(wins / max(1, wins + losses) * 100, 1) if (wins + losses) > 0 else 0
                    total_r = sum(float(s.get("rr_achieved", 0)) for s in setups)

                    summary_text = (
                        f"📊 *KẾT QUẢ BACKTEST 2 THÁNG QUA*\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"• Tổng số setup: *{total}*\n"
                        f"• Thắng (Win/Partial): *{wins}* | Thua: *{losses}*\n"
                        f"• Tỷ lệ thắng (Winrate): *{wr}%*\n"
                        f"• Tổng lợi nhuận: *+{total_r:.1f}R*\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                    )

                    # Gửi trước bảng kết quả
                    bot.send_message(message.chat.id, summary_text, parse_mode="Markdown")

                    # Gọi Gemini đánh giá phong độ
                    if self.gemini and self.gemini.ready:
                        bot.send_message(message.chat.id, "🧠 Não bộ Gemini đang thẩm định phong độ chiến lược 2 tháng qua...")
                        ai_assessment = self.gemini.analyze_backtest_results(summary_text)
                        bot.send_message(message.chat.id, f"🧠 *NHẬN ĐỊNH TỪ GEMINI AI:*\n\n{ai_assessment}", parse_mode="Markdown")

                except Exception as e:
                    bot.send_message(message.chat.id, f"❌ Lỗi khi chạy backtest: {e}")

            threading.Thread(target=run_bt, daemon=True).start()

        @bot.message_handler(func=lambda msg: msg.text and "1111" in msg.text)
        def handle_passcode_bind(message):
            cid = str(message.chat.id)
            self.chat_id = cid
            if self.settings:
                self.settings.set("telegram_chat_id", cid)
            bot.reply_to(
                message,
                f"🎉 *XÁC NHẬN MÃ PIN 1111 THÀNH CÔNG!*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Đã kết nối Chat ID: `{cid}`\n"
                f"Bot sẽ tự động bắn tín hiệu và nhận lệnh trực tiếp qua chat này!",
                parse_mode="Markdown"
            )

        @bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            """Nhận ảnh chart từ điện thoại gửi lên Telegram -> Gemini phân tích tức thì"""
            bot.reply_to(message, "🧠 Đã nhận ảnh! Não bộ Gemini đang soi nến và đối chiếu với database kinh nghiệm...")

            try:
                # Tải file ảnh
                file_info = bot.get_file(message.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                saved_path = os.path.join(DATA_DIR, f"tg_chart_{timestamp}.png")
                with open(saved_path, 'wb') as f:
                    f.write(downloaded_file)

                # Lấy tóm tắt kinh nghiệm từ quant engine
                stats_summary = ""
                if self.quant:
                    s = self.quant.get_summary()
                    stats_summary = (
                        f"Database có {s.get('total_trades', 0)} lệnh, Winrate trung bình: {s.get('winrate', 0)}%, "
                        f"Phiên hiệu quả nhất: {s.get('best_session', 'London')}."
                    )

                # Gọi Gemini thẩm định
                if self.gemini and self.gemini.ready:
                    ai_verdict = self.gemini.analyze_chart(saved_path, stats_summary=stats_summary)
                    bot.reply_to(message, ai_verdict)
                else:
                    bot.reply_to(message, "⚠️ Gemini AI chưa được kích hoạt hoặc API key chưa thiết lập trong tab Cài đặt.")
            except Exception as e:
                bot.reply_to(message, f"❌ Lỗi khi xử lý ảnh chart: {e}")

