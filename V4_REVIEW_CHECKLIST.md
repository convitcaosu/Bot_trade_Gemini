# V4 — Bản xem trước, CHƯA PUSH (giữ local theo yêu cầu của Đỉnh)

## Trạng thái
- Code chỉ ở local clone, chưa push lên GitHub.
- Test: `python tests/test_v4.py` — 5/5 pass, không cần MT5/Gemini/mạng.
- `py_compile` toàn bộ code Python pass. Giao diện chưa chạy kiểm chứng trực quan trên Windows (theo yêu cầu của Đỉnh).

## File mới (nên xem trước)
- `core/v4_candidates.py` (234 dòng) — đặc trưng mềm, BOS/CHoCH, OB chưa bị phá, FVG, HTF.
- `core/v4_methods.py` (92 dòng) — 6 phương pháp A-F, chỉ tạo ứng viên.
- `core/v4_ai_judge.py` (115 dòng) — JSON bắt buộc, SKIP khi offline/sai JSON/lệch hướng.
- `core/v4_gate.py` (62 dòng) — preset conservative/balanced/aggressive.
- `core/v4_symbols.py` (63 dòng) — quét tầng, top-N AI, cooldown.
- `core/v4_engine.py` (84 dòng) — candidate -> AI -> gate -> Signal.
- `core/v4_training.py` (118 dòng) — dataset, nhãn trừ spread, walk-forward.
- `core/v4_ticks.py` (46 dòng) — đọc file tick của EA, tính spread quanh tín hiệu.
- `EA_Bridge/GeminiTickCollector.mq5` (238 dòng) — host chart XAUUSD, quét tick cũ-mới theo ngày + realtime bằng OnTimer, xuất nến M5/M15/H1/H4.
- `ui/v4_dashboard_view.py` (173 dòng) — tab V4 Pro mới, dashboard cũ giữ nguyên.
- `tests/test_v4.py` (95 dòng) — 5 test.

## File sửa
- `main.py` — scanner mặc định qua V4, bỏ điểm 8.0/8.5, bỏ tín hiệu screenshot giá 0, scanner dùng symbol MT5 phát hiện.
- `core/mt5_data.py` — bỏ danh sách symbol cứng, nhận mọi symbol visible trên Market Watch.
- `core/signal_dispatcher.py`, `core/trade_logger.py` — thêm method_id, ai_reason, ai_components.
- `core/gemini_brain.py` — thêm analyze_text() cho V4 judge.
- `config.py` — thêm v4_enabled, v4_preset, v4_max_ai_per_minute, v4_top_n_per_scan.
- `ui/app_window.py`, `ui/__init__.py` — thêm tab V4 Pro.
- `ui/signals_view.py`, `ui/settings_view.py` — hiện method/AI breakdown, thêm cài đặt V4.

## Checklist xem trước (Đỉnh cần chốt)
1. EA tick collector: InpMaxDays mặc định 7 ngày có ok không, hay muốn tăng?
2. V4 preset mặc định Balanced có ok không?
3. Tab V4 Pro: giữ dashboard cũ song song có ok không?
4. Token trong các file: giữ nguyên theo yêu cầu (Đỉnh nói đã thu hồi).
5. Sau khi xem xong: push lên GitHub, hay sửa thêm rồi mới push?
