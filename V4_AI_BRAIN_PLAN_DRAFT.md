# V4 — AI-first, draft chưa push (chờ Đỉnh duyệt)

## Vấn đề gốc: vì sao đã có AI mà vẫn sai?
- Luồng hiện tại: điều kiện cứng sweep + pin bar quyết định trước, Gemini chỉ soi ảnh sau đó.
- Điểm AI bị gán cứng 8.0/8.5 khi offline; hướng lệnh được đoán bằng cách tìm chữ SELL/BUY trong văn bản.
- Gemini chỉ thấy 1 ảnh M5 render bằng matplotlib (60 nến), không thấy xu hướng khung lớn, spread lúc tín hiệu, volume thật, hay cấu trúc OB/FVG đã tính bằng số.
- Kết quả: AI là trang trí, không phải bộ não, và không có quyền phủ quyết tín hiệu.

## Kiến trúc mới: AI làm não, thuật toán chỉ làm ứng viên
1. **Tạo ứng viên mềm (không loại cứng):** quét tất cả symbol, mỗi phương pháp dưới đây chỉ đề xuất ứng viên + đặc trưng số, không tự bắn tín hiệu.
2. **Xếp hạng ứng viên:** theo confluence (HTF trend, BOS, OB, FVG, sweep/ATR, spread/ATR, session, volume).
3. **AI phán quyết:** Gemini nhận (a) ảnh M5 + H1/H4, (b) bảng đặc trưng số, (c) lịch sử hiệu quả của phương pháp đó. Trả về JSON có cấu trúc, không phải văn bản tự do: decision BUY/SELL/SKIP, score từng thành phần, entry/SL/TP + lý do, confidence.
4. **Cổng phát tín hiệu:** chỉ bắn khi AI decision trùng hướng ứng viên, confidence >= ngưỡng người dùng chọn, SL/TP hợp lệ (risk > spread, TP1 > spread + phí), và không trùng tín hiệu đang mở.
5. **Vòng học:** mọi tín hiệu + outcome (TP1/TP2/TP3/SL, có trừ spread) được log kèm method, AI score, đặc trưng. Báo cáo theo method/symbol/session/score để tự điều chỉnh trọng số, không cần đoán.

## Các phương pháp để AI đánh giá (không phải tất cả đều bắn)
- A. Sweep + BOS/CHoCH + hồi về OB chưa bị phá (phương pháp chính, ít tín hiệu nhất).
- B. Sweep + displacement + FVG entry (vào nhanh sau cú đẩy mạnh).
- C. OB + FVG thuận xu hướng HTF (continuation, không cần sweep).
- D. Breaker block / mitigation sau khi OB cũ bị phá.
- E. Liquidity grab ở đỉnh/đáy phiên Asia + đảo chiều phiên London/New York.
- F. Range Asia breakout có xác nhận BOS, chỉ khi HTF không ngược hướng.
- Mỗi phương pháp có preset Conservative / Balanced / Aggressive khác nhau về ngưỡng confidence và RR tối thiểu.

## Train AI riêng (không thay Gemini ngay, mà bổ sung)
- **Bước 1 — thu thập nhãn thật:** chạy collector trên MT5 Windows đã kết nối Exness Standard, ghi tick/M1 + spread tại thời điểm tín hiệu, không dùng spread cố định vì spread Standard thay đổi theo phiên và tin tức.
- **Bước 2 — tạo dataset:** mỗi ứng viên là 1 mẫu, đặc trưng gồm sweep/ATR, wick%, BOS, khoảng cách tới OB, kích thước FVG, HTF trend, session, spread/ATR, volume ratio. Nhãn: chạm TP1 trước SL hay không, và RR thực tế sau khi trừ spread/phí.
- **Bước 3 — train model nhỏ, giải thích được:** logistic regression / gradient boosting, chia train/test theo thời gian (walk-forward), không chia ngẫu nhiên để tránh rò rỉ tương lai.
- **Bước 4 — dùng song song:** model này cho xác suất, Gemini cho lý do và phán quyết cuối. Chỉ khi cả hai đồng thuận ở preset Conservative mới bắn.
- **Giới hạn trung thực:** không có model nào đảm bảo winrate. Cần forward-test trên demo trước khi dùng tiền thật, và model chỉ tốt bằng dữ liệu Exness mà người dùng cung cấp.

## Không giới hạn symbols — nhưng phải quét theo tầng
- Tầng 1 (rẻ, chạy local): quét tất cả symbol visible trên Market Watch, tính đặc trưng, loại ứng viên yếu.
- Tầng 2 (đắt, gọi AI): chỉ top ứng viên theo confluence, có cooldown mỗi symbol, giới hạn số lần gọi AI mỗi phút.
- Bảng thông số theo symbol (digits, point, contract size, spread trung bình, giờ giao dịch) thay cho công thức point_mult cứng hiện tại.
- Nếu quét thật sự mọi symbol mỗi 3 giây + gọi Gemini cho mọi ứng viên thì sẽ chậm, tốn API và spam tín hiệu — nên mặc định là "không giới hạn danh sách", nhưng AI chỉ xử lý ứng viên mạnh nhất.

## Giao diện exe mới (giữ CustomTkinter để đóng gói Windows dễ)
- Dashboard: chart live vẽ lại khi có nến mới, vùng OB/FVG, đường Entry/SL/TP1/TP2/TP3, đồng hồ đóng nến.
- Thẻ tín hiệu: điểm thành phần của AI (trend, cấu trúc, thanh khoản, timing), lý do SKIP cũng hiển thị để người dùng thấy AI đã lọc cái gì.
- Bộ lọc: method, symbol, session, ngưỡng confidence, preset.
- Hiệu suất live: win/loss và R theo method, theo AI score, theo symbol/session; cảnh báo khi 1 method tụt hiệu quả.
- Trạng thái: MT5, Gemini, model local, spread hiện tại, số ứng viên đang chờ AI.

## EXE và giới hạn build
- Code sửa được trên máy Linux này và kiểm tra cú pháp được, nhưng file exe Windows + thư viện MetaTrader5 chỉ build và test live được trên máy Windows có MT5/Exness.
- Quy trình: sửa code ở đây -> push lên GitHub khi Đỉnh duyệt -> chạy build_exe.bat trên Windows -> test demo trước.
- Chưa sửa code chính trong bản draft này; file này chỉ là bản thiết kế để duyệt.

## Đã code V4 ngày 2026-10-24 (local, chưa push)
- core/v4_candidates.py: đặc trưng mềm, BOS/CHoCH thật, OB chưa bị phá, FVG 3 nến, HTF trend.
- core/v4_methods.py: 6 phương pháp A-F, chỉ tạo ứng viên.
- core/v4_ai_judge.py: JSON bắt buộc, SKIP khi offline/parse sai/lệch hướng, không điểm cứng.
- core/v4_gate.py: preset conservative/balanced/aggressive, kiểm tra risk > spread, thứ tự SL/Entry/TP, RR tối thiểu.
- core/v4_symbols.py: quét tầng 1 local cho mọi symbol, tầng 2 AI top-N + cooldown + giới hạn gọi/phút.
- core/v4_engine.py: candidate -> AI -> gate -> Signal, SKIP được ghi lại.
- core/v4_training.py: dataset + nhãn trừ spread + walk-forward + train HistGradientBoosting nếu có sklearn.
- main.py: scanner mặc định qua V4 khi v4_enabled=True, bỏ điểm 8.0/8.5, bỏ tín hiệu screenshot giá 0.
- ui/signals_view.py: thẻ tín hiệu hiện method, điểm thành phần AI, lý do AI. ui/settings_view.py: thêm v4_preset, v4_max_ai_per_minute, v4_top_n_per_scan.
- tests/test_v4.py: 5 test pass, không cần MT5/Gemini/mạng.
- Chưa làm: chart live hoàn toàn mới, train model thật (cần dữ liệu Exness), build exe Windows, push GitHub.
