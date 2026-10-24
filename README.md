# ⚡ Gemini Trade Bot Pro v3.0

Hệ thống bot trading SMC ứng dụng thị giác máy tính **Google Gemini AI Vision**, kết nối trực tiếp **MetaTrader 5 (MT5)**, sở hữu **Giao diện Desktop Dashboard Pro (Dark Mode)**, cơ chế **Bắn tín hiệu song song độc lập (Desktop UI + Telegram)**, **Dynamic SL/TP linh động** và tính năng **Backtest 2 Tháng Quá Khứ** trực quan phong độ.

---

## 🚀 Các Tính Năng Chính v3.0

- **Dynamic SL/TP & Bảo Toàn Vốn:**
  - SL neo theo cấu trúc râu nến sweep + ATR buffer.
  - **TP1 (40% lot):** Chốt lời bảo toàn tại swing level gần nhất (≈ 1.5R) và **tự động trailing SL lên Breakeven (hòa vốn)**.
  - **TP2 (40% lot):** Chốt lời mục tiêu tại Order Block / cản tiếp theo (≈ 2.5R - 3.0R).
  - **TP3 (20% lot):** Runner tham vọng chạy theo cấu trúc lớn (trailing).
- **Tab Backtest 2 Tháng (Desktop UI + Telegram):**
  - Quét 15.000 nến quá khứ cho mọi symbol (XAUUSD, Cent, Forex).
  - Thống kê tỷ lệ thắng (Winrate), tổng số lệnh, lãi lỗ bao nhiêu R.
  - Bảng chi tiết từng setup: Ngày giờ vào, Entry, SL, TP1, TP2, TP3, Kết quả và Điểm chốt.
  - AI Gemini đọc dữ liệu và đưa ra nhận xét phong độ chuyên sâu.
- **EA Bridge v3.0 (`EA_Bridge/GeminiBotBridge.mq5`):**
  - Gắn vào bất kỳ chart nào trên MT5 (tự động nhận diện symbol).
  - Có nút bấm **`⚡ QUÉT 2 THÁNG NẾN`** trực tiếp trên chart để xuất nến lịch sử cho Python.
  - Vẽ trực quan các đường Entry, SL, TP1, TP2, TP3 sắc nét trên MT5.
- **Bắn Tín Hiệu Kép Song Song:**
  - Bắn realtime lên **Desktop Dashboard Feed**.
  - Bắn qua **Telegram Bot** kèm phân tích AI và ảnh chụp chart.
  - Liên kết chat nhanh bằng cách gửi mã `1111` hoặc `/bind`.

---

## 📁 Cấu Trúc Dự Án

```
bot_gemi_tele/
├── assets/                 # Icon, hình ảnh UI
├── bot_data/               # Database lệnh (trade_history.csv), cấu hình (settings.json)
├── core/
│   ├── gemini_brain.py     # Bộ não AI Gemini 2.5 Flash
│   ├── mt5_data.py         # Kết nối nến MT5, SMC detection, Backtest engine
│   ├── quant_engine.py     # Phân tích định lượng, biểu đồ hiệu suất
│   ├── signal_dispatcher.py # Điều phối bắn tín hiệu song song
│   └── trade_logger.py     # Database lưu trữ lịch sử và kinh nghiệm
├── EA_Bridge/
│   └── GeminiBotBridge.mq5 # EA cầu nối MT5 v3.0
├── telegram_bot/
│   └── tele_bot.py         # Bot Telegram tương tác 2 chiều
├── ui/
│   ├── app_window.py       # Cửa sổ chính Desktop Dashboard
│   ├── backtest_view.py    # Giao diện Backtest 2 tháng trực quan
│   ├── dashboard_view.py   # Trang chủ Dashboard
│   ├── signals_view.py     # Feed tín hiệu realtime
│   ├── stats_view.py       # Biểu đồ phân tích định lượng
│   ├── log_view.py         # Nhật ký lệnh thực tế
│   └── settings_view.py    # Cài đặt API keys & thông số
├── build_exe.bat           # Script đóng gói EXE (PyInstaller)
├── CHAY_APP.bat            # Script khởi chạy app nhanh
├── config.py               # Cấu hình chung
├── main.py                 # File chạy chính
├── requirements.txt        # Thư viện phụ thuộc
└── USER_GUIDE.md           # Hướng dẫn sử dụng chi tiết
```

---

## 🛠️ Cài Đặt & Khởi Chạy

### 1. Cài đặt môi trường
```bash
pip install -r requirements.txt
```

### 2. Khởi chạy ứng dụng
- Nhấp đúp vào file **`CHAY_APP.bat`**
- Hoặc chạy lệnh:
```bash
python main.py
```

### 3. Đóng gói file EXE
```bash
build_exe.bat
```
File EXE sẽ được lưu tại: `dist/GeminiTradeBotPro/GeminiTradeBotPro.exe`.
