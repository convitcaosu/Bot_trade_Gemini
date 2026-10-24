"""
=============================================================================
STATS VIEW — Biểu đồ phân tích hiệu suất
Hiển thị 4 biểu đồ + thống kê chi tiết
=============================================================================
"""
import os
import sys
import customtkinter as ctk
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, REPORT_IMG_PATH


class StatsView(ctk.CTkFrame):
    """Tab thống kê — biểu đồ hiệu suất + phân tích chi tiết"""

    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # ─── Header ───
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", padx=20, pady=(15, 5))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="📈  Performance Statistics",
            font=("Segoe UI", 22, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkButton(
            header, text="📊 Generate Report", font=("Segoe UI", 12),
            width=150, height=32, corner_radius=8,
            fg_color=COLORS["accent_blue"],
            hover_color="#1a47b8",
            text_color="#ffffff",
            command=self._generate,
        ).pack(side="right")

        # ─── Stats Summary Cards ───
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent", height=80)
        self.summary_frame.pack(fill="x", padx=20, pady=(5, 10))
        self.summary_frame.pack_propagate(False)

        self.stat_labels = {}
        stat_items = [
            ("total", "Total", "0"),
            ("wins", "Wins", "0"),
            ("losses", "Losses", "0"),
            ("winrate", "Winrate", "0%"),
            ("avg_rr", "Avg R:R", "0"),
            ("total_rr", "Profit", "+0R"),
        ]

        for key, label, val in stat_items:
            card = ctk.CTkFrame(self.summary_frame, fg_color=COLORS["bg_card"],
                                 corner_radius=10)
            card.pack(side="left", fill="both", expand=True, padx=3)

            val_lbl = ctk.CTkLabel(card, text=val, font=("Segoe UI", 18, "bold"),
                                    text_color=COLORS["text_primary"])
            val_lbl.pack(pady=(8, 0))
            ctk.CTkLabel(card, text=label, font=("Segoe UI", 10),
                          text_color=COLORS["text_secondary"]).pack(pady=(0, 8))
            self.stat_labels[key] = val_lbl

        # ─── Chart Image Display ───
        self.chart_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.chart_label = ctk.CTkLabel(
            self.chart_frame,
            text="Bấm 'Generate Report' để tạo biểu đồ phân tích.\n\n"
                 "Cần ít nhất 3 lệnh trong database.",
            font=("Segoe UI", 14),
            text_color=COLORS["text_muted"],
            justify="center",
        )
        self.chart_label.pack(fill="both", expand=True, padx=20, pady=20)

        # ─── AI Insight ───
        self.insight_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"],
                                           corner_radius=12, height=120)
        self.insight_frame.pack(fill="x", padx=20, pady=(0, 15))
        self.insight_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.insight_frame, text="🧠  AI Insight",
            font=("Segoe UI", 13, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=15, pady=(10, 3))

        self.insight_text = ctk.CTkLabel(
            self.insight_frame,
            text="Tạo báo cáo để nhận nhận định tổng quan từ AI.",
            font=("Segoe UI", 11),
            text_color=COLORS["text_secondary"],
            anchor="w",
            justify="left",
            wraplength=1000,
        )
        self.insight_text.pack(fill="x", padx=15, pady=(0, 10))

    def refresh(self):
        """Refresh stats + reload chart nếu có"""
        self._update_stats()
        self._load_chart_image()

    def _update_stats(self):
        if not self.app or not self.app.trade_logger:
            return
        stats = self.app.trade_logger.get_stats_summary()
        mapping = {
            "total": str(stats.get("total", 0)),
            "wins": str(stats.get("wins", 0)),
            "losses": str(stats.get("losses", 0)),
            "winrate": f"{stats.get('winrate', 0)}%",
            "avg_rr": f"1:{stats.get('avg_rr', 0)}",
            "total_rr": f"+{stats.get('total_rr', 0)}R",
        }
        for key, val in mapping.items():
            if key in self.stat_labels:
                self.stat_labels[key].configure(text=val)

    def _load_chart_image(self):
        """Load ảnh biểu đồ nếu đã tạo"""
        if os.path.exists(REPORT_IMG_PATH):
            try:
                img = Image.open(REPORT_IMG_PATH)
                # Get available size
                max_w = max(800, self.chart_frame.winfo_width() - 40)
                max_h = max(400, self.chart_frame.winfo_height() - 40)
                img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                                       size=img.size)
                self.chart_label.configure(image=ctk_img, text="")
                self.chart_label._ctk_img = ctk_img
            except Exception as e:
                self.chart_label.configure(text=f"Lỗi load ảnh: {e}")

    def _generate(self):
        if not self.app or not self.app.quant_engine:
            return

        self.app.set_status("📊 Đang tạo biểu đồ phân tích...")
        import threading

        def do_generate():
            path = self.app.quant_engine.generate_report_chart()
            if path:
                self.after(0, self._on_report_done, path)
            else:
                self.after(0, lambda: self.app.set_status("⚠️ Không đủ dữ liệu."))

        threading.Thread(target=do_generate, daemon=True).start()

    def _on_report_done(self, path):
        self._update_stats()
        self._load_chart_image()
        self.app.set_status("📊 Báo cáo đã sẵn sàng!")

        # Get AI insight
        if self.app.gemini and self.app.gemini.ready and self.app.quant_engine:
            import threading

            def get_insight():
                stats_text = self.app.quant_engine.get_stats_text()
                insight = self.app.gemini.get_report_insight(stats_text)
                self.after(0, lambda: self.insight_text.configure(text=insight[:500]))

            threading.Thread(target=get_insight, daemon=True).start()
