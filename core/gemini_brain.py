"""
=============================================================================
GEMINI AI BRAIN v3.0 — Bộ não phân tích thông minh
- Phân tích chart + gợi ý SL/TP linh động
- Đánh giá setup quality & chấm điểm
- Backtest insight — AI nhận xét kết quả test
- Hỗ trợ chốt lời từng phần, trailing, breakeven
=============================================================================
"""
import os
import sys
import re
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiBrain:
    """Bộ não AI — Gemini Vision + phân tích cấu trúc + gợi ý linh động"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.client = None
        self.model = "gemini-2.5-flash"
        self.ready = False

        if api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=api_key)
                self.ready = True
            except Exception as e:
                print(f"[GeminiBrain] Lỗi khởi tạo: {e}")

    @property
    def is_available(self):
        return GENAI_AVAILABLE

    def update_key(self, key: str):
        """Cập nhật API key runtime"""
        self.api_key = key
        if key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=key)
                self.ready = True
                return True
            except Exception:
                self.ready = False
        return False

    def analyze_chart(self, image_path: str, stats_summary: str = "",
                      extra_context: str = "") -> str:
        """
        Gửi ảnh chart + dữ liệu kinh nghiệm sang Gemini.
        Trả về phân tích chi tiết với SL/TP linh động.
        """
        if not self.ready or not self.client:
            return "⚠️ Gemini AI chưa sẵn sàng. Vui lòng kiểm tra API Key."

        if not os.path.exists(image_path):
            return f"⚠️ Không tìm thấy ảnh: {image_path}"

        prompt = self._build_analysis_prompt(stats_summary, extra_context)

        try:
            from PIL import Image
            img = Image.open(image_path)
            response = self.client.models.generate_content(
                model=self.model,
                contents=[img, prompt]
            )
            return response.text
        except Exception as e:
            return f"❌ Lỗi khi gọi Gemini: {str(e)}"

    def analyze_setup_data(self, setup_info: dict, stats_summary: str = "") -> str:
        """Phân tích setup từ dữ liệu số (không cần ảnh)"""
        if not self.ready or not self.client:
            return "⚠️ Gemini AI chưa sẵn sàng."

        prompt = f"""
Bạn là Chuyên gia phân tích SMC/ICT cấp cao.
Đánh giá chất lượng setup dưới đây:

[THÔNG TIN SETUP]:
- Symbol: {setup_info.get('symbol', 'N/A')}
- Timeframe: {setup_info.get('timeframe', 'N/A')}
- Direction: {setup_info.get('direction', 'N/A')}
- Phiên: {setup_info.get('session', 'N/A')}
- Râu nến: {setup_info.get('wick_percent', 0)}%
- Quét thanh khoản: {setup_info.get('sweep_pips', 0)} pips
- FVG: {'Có' if setup_info.get('has_fvg') else 'Không'}
- Order Block: {'Có' if setup_info.get('has_ob') else 'Không'}
- Market Structure: {setup_info.get('market_structure', 'N/A')}
- ATR: {setup_info.get('atr', 0)}
- Entry: {setup_info.get('entry_price', 0)}
- SL: {setup_info.get('stop_loss', 0)}
- TP1 (bảo toàn): {setup_info.get('tp1', 0)}
- TP2 (chính): {setup_info.get('tp2', setup_info.get('take_profit', 0))}
- TP3 (tham vọng): {setup_info.get('tp3', 0)}

[KINH NGHIỆM]:
{stats_summary if stats_summary else 'Chưa có dữ liệu lịch sử.'}

Trả lời NGẮN GỌN:
1. ĐIỂM: .../10
2. NHẬN ĐỊNH: 1-2 câu đánh giá setup
3. GỢI Ý SL/TP: Nên giữ nguyên hay điều chỉnh? Lý do?
4. CHIẾN LƯỢC: Chốt lời từng phần hay all-in? Trailing hay cố định?
5. QUYẾT ĐỊNH: VÀO LỆNH / BỎ QUA
"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt]
            )
            return response.text
        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    def analyze_backtest_results(self, backtest_summary: str) -> str:
        """AI đánh giá kết quả backtest — phong độ chiến lược"""
        if not self.ready or not self.client:
            return "⚠️ Gemini chưa sẵn sàng."

        prompt = f"""
Bạn là Chuyên gia Quant Trading phân tích kết quả backtest.
Dưới đây là kết quả quét 2 tháng lịch sử giao dịch:

{backtest_summary}

Hãy đưa ra:
1. ĐÁNH GIÁ PHONG ĐỘ: Chiến lược này mạnh hay yếu? (dựa trên winrate, RR, drawdown)
2. PHIÊN TỐT NHẤT: Phiên nào winrate cao nhất? Vì sao?
3. SETUP CHẤT LƯỢNG: Setup nào có edge rõ nhất? (wick cao, FVG, OB)
4. CẢNH BÁO: Có rủi ro gì cần lưu ý? Streak thua dài nhất?
5. GỢI Ý CẢI THIỆN: 2-3 điều cụ thể để tăng hiệu suất
6. KẾT LUẬN: Nên tiếp tục dùng chiến lược này không? Điều chỉnh gì?

Format ngắn gọn, rõ ràng, có số liệu cụ thể.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt]
            )
            return response.text
        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    def get_report_insight(self, stats_summary: str) -> str:
        """Gemini đọc thống kê và đưa ra nhận định tổng quan"""
        if not self.ready or not self.client:
            return "⚠️ Gemini chưa sẵn sàng."

        prompt = f"""
Bạn là Chuyên gia Quant Trading phân tích hiệu suất giao dịch.
Thống kê từ database kinh nghiệm thực tế:

{stats_summary}

Hãy đưa ra:
1. NHẬN ĐỊNH TỔNG QUAN (2-3 câu)
2. ĐIỂM MẠNH của chiến lược (dựa trên data)
3. ĐIỂM YẾU cần cải thiện
4. GỢI Ý HÀNH ĐỘNG cụ thể để tăng winrate
"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt]
            )
            return response.text
        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    def _build_analysis_prompt(self, stats_summary: str = "", extra_context: str = "") -> str:
        return f"""
Bạn là Tổng Tư Lệnh Phân Tích Định Lượng & Chuyên Gia SMC/ICT cấp cao.

NHIỆM VỤ: Thẩm định setup trong ảnh chart — có đủ tiêu chuẩn vào lệnh không?
GỢI Ý SL/TP LINH ĐỘNG dựa trên cấu trúc thị trường — KHÔNG dùng RR cố định.

[BỘ NHỚ KINH NGHIỆM TỪ DỮ LIỆU THỰC TẾ]:
{stats_summary if stats_summary else "Chưa có đủ lịch sử lệnh."}

{f"[CONTEXT BỔ SUNG]: {extra_context}" if extra_context else ""}

[QUY TẮC CHIẾN LƯỢC SMC BẮT BUỘC]:
1. Quét thanh khoản (Liquidity Sweep): Nến phải thò râu đâm thủng đáy/đỉnh cũ rồi rút chân.
2. Nến đảo chiều: Bullish/Bearish Pin Bar có râu dài (>60% tổng cây nến).
3. Cấu trúc & Cản: Có Order Block cản không? FVG mở đường không?
4. ĐỐI CHIẾU KINH NGHIỆM: Setup này thuộc nhóm winrate cao hay thấp?

[QUAN TRỌNG — SL/TP LINH ĐỘNG]:
- SL: Đặt dưới/trên râu nến sweep + buffer ATR (KHÔNG cố định pips)
- TP1: Swing level gần nhất (bảo toàn vốn, chốt 30-50% lot)
- TP2: Order Block hoặc cản tiếp theo (chốt thêm 30%)
- TP3: Cấu trúc lớn hơn (phần còn lại, trailing SL)
- GỢI Ý: Khi hit TP1 → trailing SL lên breakeven

[YÊU CẦU TRẢ LỜI]:
━━━━━━━━━━━━━━━━━━━━━━━━
📊 QUYẾT ĐỊNH: [ BUY / SELL / BỎ QUA ]
⭐ ĐIỂM ĐÁNH GIÁ: .../10

📋 PHÂN TÍCH:
• Quét thanh khoản: (Đạt/Không đạt, vì sao)
• Cây nến rút chân: (Đánh giá râu và thân)
• Bối cảnh cản & FVG: (Đường đi thoáng không)
• Market Structure: (CHoCH/BOS/Range)

📈 ĐỐI CHIẾU KINH NGHIỆM:
(Kèo này giống nhóm thắng hay nhóm thua)

🎯 GỢI Ý VÀO LỆNH (SL/TP LINH ĐỘNG):
• Entry: [giá cụ thể]
• SL: [giá — lý do]
• TP1: [giá — swing level — chốt 40% lot]
• TP2: [giá — OB/cản — chốt 40% lot]
• TP3: [giá — cấu trúc lớn — trailing 20% lot]
• Khi hit TP1 → trailing SL lên breakeven
━━━━━━━━━━━━━━━━━━━━━━━━
"""
