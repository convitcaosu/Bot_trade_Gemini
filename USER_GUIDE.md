# ⚡ GEMINI TRADE BOT PRO v3.0 — HƯỚNG DẪN VẬN HÀNH TOÀN DIỆN

Hệ thống bot trading SMC ứng dụng thị giác máy tính **Google Gemini AI Vision**, kết nối trực tiếp **MetaTrader 5 (MT5)**, sở hữu **Giao diện Desktop Dashboard Pro (Dark Mode)**, cơ chế **Bắn tín hiệu song song độc lập (Desktop UI + Telegram)**, **Dynamic SL/TP linh động** và tính năng **Backtest 2 Tháng Quá Khứ** trực quan phong độ.

---

## 🎯 CÁC TÍNH NĂNG ĐỈNH CAO v3.0

| Phân hệ | Tính năng chi tiết | Trạng thái |
|---|---|---|
| **Dynamic SL/TP** | • SL linh động theo râu nến sweep + buffer ATR (không cố định)<br>• **TP1 (40%)**: Bảo toàn vốn (swing level gần nhất), tự động dời SL lên Breakeven<br>• **TP2 (40%)**: Mục tiêu chính (Order Block / cản tiếp theo)<br>• **TP3 (20%)**: Runner tham vọng (cấu trúc lớn / trailing) | ✅ Đã hoàn thiện |
| **Backtest 2 Tháng** | • Quét 15.000 nến quá khứ (~2 tháng M5) cho bất kỳ symbol nào (XAUUSD, Cent, Forex...)<br>• Thống kê trực quan: Winrate, Total Setups, Thắng/Thua, R:R tích luỹ<br>• Bảng chi tiết từng setup: Entry, SL, TP1, TP2, TP3, Ngày giờ vào lệnh, Outcome, R:R đạt được<br>• **AI Gemini thẩm định phong độ**: Phân tích ưu/nhược điểm, phiên mạnh nhất, lý do setup thắng/thua | ✅ Đã hoàn thiện |
| **MT5 EA Bridge v3.0** | • File `EA_Bridge/GeminiBotBridge.mq5` gắn vào bất kỳ chart nào (nhận diện symbol tự động)<br>• Nút bấm trực tiếp trên chart: `⚡ QUÉT 2 THÁNG NẾN` xuất 15.000 nến ngay lập tức<br>• Tự vẽ các mốc Entry, SL, TP1, TP2, TP3 rõ ràng trên chart MT5<br>• Chụp ảnh nét và gửi signal file cho Desktop App | ✅ Đã hoàn thiện |
| **Signal Dispatcher** | • Bắn tín hiệu song song 2 nơi: **Desktop UI Feed** & **Telegram Channel/Chat**<br>• Format Telegram chuyên nghiệp với đầy đủ Entry, SL, TP1/TP2/TP3 và nhận định AI | ✅ Đã hoàn thiện |
| **Gemini AI Brain v3.0** | • Sử dụng SDK `google.genai` chuẩn mới nhất với model `gemini-2.5-flash`<br>• Thẩm định setup, chấm điểm (/10), đưa ra chiến lược chốt lời từng phần | ✅ Đã hoàn thiện |
| **Desktop UI (.exe)** | • Theme TradingView Dark Mode (CustomTkinter)<br>• 6 Tabs: **Dashboard**, **Backtest 2M**, **Signals Feed**, **Statistics**, **Experience Log**, **Settings** | ✅ Đã hoàn thiện |
| **Telegram Bot** | • Tự động nhận diện & bind chat: gõ `1111` hoặc `/bind` hoặc `/start`<br>• Lệnh: `/backtest`, `/stats`, `/report`, `/status`, `/scan`, `/win`, `/loss`<br>• Gửi trực tiếp ảnh chart từ điện thoại lên để Gemini soi SMC ngay | ✅ Đã hoàn thiện |

---

## 🚀 CÁCH KHỞI CHẠY APP

Bạn có thể mở app cực kỳ dễ dàng:

### Cách 1: Nhấp đúp vào `CHAY_APP.bat` (Khuyên dùng)
- Trong thư mục `bot_gemi_tele`, nhấp đúp file: **`CHAY_APP.bat`**
- App sẽ tự động mở giao diện Desktop TradingView Dark Mode.

### Cách 2: Đóng gói hoặc chạy file EXE
- Để đóng gói lại file EXE mới nhất, chỉ cần chạy file: **`build_exe.bat`**
- File EXE độc lập sẽ được tạo tại: **`dist\GeminiTradeBotPro\GeminiTradeBotPro.exe`**

---

## 🧪 CÁCH SỬ DỤNG TÍNH NĂNG BACKTEST 2 THÁNG

1. Mở Desktop App lên, nhấp vào tab **`🧪 Backtest 2M`** ở menu bên trái.
2. Nhập Symbol muốn test (ví dụ: `XAUUSD`, hoặc tài khoản Cent thì gõ tên đuôi của sàn như `XAUUSDc`, `XAUUSDm`, etc.).
3. Chọn khung thời gian (mặc định: `M5` hoặc `M15`).
4. Bấm nút **`⚡ QUÉT 2 THÁNG`**:
   - Hệ thống quét 15.000 nến quá khứ.
   - Thống kê tỷ lệ thắng (Winrate), tổng số lệnh, lãi lỗ bao nhiêu R.
   - Bảng bên dưới hiển thị chi tiết từng setup: Ngày giờ vào, Entry, SL, TP1, TP2, TP3, Kết quả và Điểm chốt.
5. Bấm nút **`🧠 AI ĐÁNH GIÁ PHONG ĐỘ`**:
   - Não bộ Gemini sẽ đọc toàn bộ kết quả 2 tháng và xuất bản báo cáo nhận định phong độ, phân tích ưu nhược điểm, streak thua dài nhất và giải thích vì sao thắng/thua.

---

## 🔌 CÁCH CÀI ĐẶT EA BRIDGE TRÊN METATRADER 5

1. Mở phần mềm **MetaTrader 5**.
2. Chọn menu **File** -> **Open Data Folder** -> mở thư mục `MQL5\Experts\`.
3. Copy file [GeminiBotBridge.mq5](file:///c:/Users/MSI/Downloads/bot_gemi_tele/EA_Bridge/GeminiBotBridge.mq5) vào thư mục đó.
4. Mở **MetaEditor** (`F4`), mở file `GeminiBotBridge.mq5` và nhấn **Compile** (`F7`).
5. Kéo EA vào bất kỳ chart nào (ví dụ Gold `XAUUSD`, `EURUSD`, cent, v.v.).
6. Trên chart MT5 sẽ xuất hiện:
   - Dòng trạng thái `⚡ GEMINI BOT BRIDGE v3.0 — RUNNING`
   - Nút bấm `⚡ QUÉT 2 THÁNG NẾN` (bấm nút này để xuất nến lịch sử cho Python phân tích).

---

## 📱 KẾT NỐI TELEGRAM (MÃ BIND 1111)

- **Token Bot**: Đã được lưu sẵn trong cấu hình (`8838582550:AAGrpBmITZNdSMYMaQ7b3o_8tfg28OkeWog`).
- **Liên kết Chat ID**: 
  1. Mở Telegram, tìm bot và gửi tin nhắn: **`1111`** hoặc **`/bind`** hoặc **`/start`**.
  2. Bot sẽ tự động nhận diện Chat ID của bạn, lưu vào hệ thống và xác nhận thành công!
  3. Từ thời điểm này, mỗi khi có tín hiệu SMC mới, bot sẽ bắn ảnh chart + mốc Entry, SL, TP1, TP2, TP3 linh động trực tiếp vào máy bạn.

### Các lệnh hữu ích trên Telegram:
- `/backtest` — Kích hoạt quét nến 2 tháng MT5 & Gemini thẩm định phong độ ngay trên điện thoại!
- `/stats` — Xem tóm tắt Winrate, tổng R, phân bổ theo phiên.
- `/report` — Xuất 4 biểu đồ phân tích hình ảnh Dark Theme gửi về Telegram.
- `/status` — Kiểm tra kết nối MT5, Gemini AI, số lượng lệnh trong database.
- `/scan` — Yêu cầu bot quét nến ngay lập tức.
- **Gửi ảnh Chart trực tiếp**: Chụp ảnh màn hình nến bất kỳ gửi vào bot, Gemini Vision sẽ soi SMC ngay lập tức!
