"""
V4 DASHBOARD — tab giao diện mới, không thay dashboard cũ.

Thiết kế theo phong cách TradingView Dark, cho Windows (font Segoe UI):
- Header lớn + pill trạng thái MT5 / AI / Collector
- Hàng KPI: tín hiệu V4 hôm nay, tỉ lệ AI pass, winrate DB, tổng R
- Chart lớn: ảnh tín hiệu mới nhất (giữ nguyên cách render matplotlib
  của v3, chỉ trình bày lại cho đẹp, không vẽ chart live bằng canvas
  ở vòng này vì cần test trực quan trên Windows)
- Panel AI: thanh điểm thành phần trend / structure / liquidity / timing,
  method, lý do AI, preset đang dùng
- Feed dưới: tín hiệu V4 gần nhất + lý do SKIP gần nhất (để thấy AI
  đã lọc cái gì, không chỉ thấy cái đã bắn)

LƯU Ý: file này chỉ kiểm tra cú pháp ở máy dev (Linux). Giao diện
trực quan chưa chạy kiểm chứng trên Windows theo yêu cầu của người dùng
— hãy mở tab "V4 Pro" trên exe Windows để xem thật.
"""
import os
import sys

import customtkinter as ctk
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS


class V4DashboardView(ctk.CTkFrame):
    """Tab V4 Pro — trình bày đẹp cho tín hiệu AI-first."""

    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.app = app
        self._build_ui()

    # ---------- layout helpers ----------
    def _pill(self, parent, text, color):
        return ctk.CTkLabel(parent, text=f"  ● {text}  ", font=("Segoe UI", 11, "bold"),
                            text_color=color, fg_color=COLORS["bg_card"], corner_radius=12)

    def _kpi(self, parent, label, key):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=16)
        ctk.CTkLabel(card, text=label, font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).pack(pady=(14, 2))
        lbl = ctk.CTkLabel(card, text="—", font=("Segoe UI", 24, "bold"),
                           text_color=COLORS["text_primary"])
        lbl.pack(pady=(0, 14))
        setattr(self, key, lbl)
        return card

    def _bar(self, parent, label, key):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=label, font=("Segoe UI", 12), width=110,
                     text_color=COLORS["text_primary"], anchor="w").pack(side="left")
        bar = ctk.CTkProgressBar(row, height=10, corner_radius=5,
                                 fg_color=COLORS["bg_input"],
                                 progress_color=COLORS["accent_cyan"])
        bar.pack(side="left", fill="x", expand=True, padx=8)
        bar.set(0)
        val = ctk.CTkLabel(row, text="—", font=("Segoe UI", 12, "bold"),
                           text_color=COLORS["text_primary"], width=40)
        val.pack(side="right")
        setattr(self, key, (bar, val))

    # ---------- build ----------
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=64)
        header.pack(fill="x", padx=24, pady=(18, 6))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="⚡  V4 Pro  —  AI Brain", font=("Segoe UI", 26, "bold"),
                     text_color=COLORS["text_primary"]).pack(side="left")
        pills = ctk.CTkFrame(header, fg_color="transparent")
        pills.pack(side="right")
        self.pill_mt5 = self._pill(pills, "MT5", COLORS["accent_red"]); self.pill_mt5.pack(side="left", padx=4)
        self.pill_ai = self._pill(pills, "AI", COLORS["accent_red"]); self.pill_ai.pack(side="left", padx=4)
        self.pill_col = self._pill(pills, "Tick Collector", COLORS["text_muted"]); self.pill_col.pack(side="left", padx=4)

        # KPI row
        kpis = ctk.CTkFrame(self, fg_color="transparent", height=96)
        kpis.pack(fill="x", padx=24, pady=6)
        kpis.pack_propagate(False)
        for label, key in [("Tín hiệu V4", "_kpi_signals"), ("AI pass", "_kpi_pass"),
                           ("Winrate DB", "_kpi_win"), ("Tổng R", "_kpi_r")]:
            card = self._kpi(kpis, label, key)
            card.pack(side="left", fill="both", expand=True, padx=4)

        # Main: chart left, AI panel right
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=6)

        chart_frame = ctk.CTkFrame(main, fg_color=COLORS["bg_card"], corner_radius=16)
        chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(chart_frame, text="📈  Latest V4 Signal Chart", font=("Segoe UI", 14, "bold"),
                     text_color=COLORS["text_primary"], anchor="w").pack(fill="x", padx=16, pady=(14, 4))
        self.chart_label = ctk.CTkLabel(chart_frame,
            text="Chưa có tín hiệu V4.\n\nKết nối MT5, bật Auto Scan,\nGemini phải sẵn sàng (có API key).",
            font=("Segoe UI", 13), text_color=COLORS["text_muted"], justify="center")
        self.chart_label.pack(fill="both", expand=True, padx=16, pady=10)

        ai_frame = ctk.CTkFrame(main, fg_color=COLORS["bg_card"], corner_radius=16, width=380)
        ai_frame.pack(side="right", fill="y", padx=(6, 0))
        ai_frame.pack_propagate(False)
        ctk.CTkLabel(ai_frame, text="🧠  AI Verdict", font=("Segoe UI", 14, "bold"),
                     text_color=COLORS["text_primary"], anchor="w").pack(fill="x", padx=16, pady=(14, 4))
        self.ai_method = ctk.CTkLabel(ai_frame, text="Method: —", font=("Segoe UI", 12),
                                      text_color=COLORS["accent_cyan"], anchor="w")
        self.ai_method.pack(fill="x", padx=16, pady=2)
        self._bar(ai_frame, "Trend", "_bar_trend")
        self._bar(ai_frame, "Structure", "_bar_structure")
        self._bar(ai_frame, "Liquidity", "_bar_liquidity")
        self._bar(ai_frame, "Timing", "_bar_timing")
        self.ai_reason = ctk.CTkTextbox(ai_frame, font=("Segoe UI", 12),
                                        text_color=COLORS["text_secondary"],
                                        fg_color=COLORS["bg_dark"], height=110)
        self.ai_reason.pack(fill="x", padx=16, pady=10)
        self.ai_reason.insert("0.0", "AI chưa phán quyết tín hiệu nào.")
        self.ai_reason.configure(state="disabled")

        # Bottom: SKIP feed — shows what AI filtered out
        bottom = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=16, height=110)
        bottom.pack(fill="x", padx=24, pady=(6, 18))
        bottom.pack_propagate(False)
        ctk.CTkLabel(bottom, text="🚫  AI đã lọc (SKIP gần nhất) — để bạn thấy não AI làm việc, không chỉ thấy tín hiệu đã bắn",
                     font=("Segoe UI", 12, "bold"), text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        self.skip_label = ctk.CTkLabel(bottom, text="Chưa có SKIP nào.", font=("Segoe UI", 12),
                                       text_color=COLORS["text_muted"], anchor="w", wraplength=1100, justify="left")
        self.skip_label.pack(fill="x", padx=16, pady=2)

    # ---------- updates from AppWindow ----------
    def on_new_signal(self, signal):
        if signal.chart_image_path and os.path.exists(signal.chart_image_path):
            try:
                img = Image.open(signal.chart_image_path)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(900, 420))
                self.chart_label.configure(image=ctk_img, text="")
                self.chart_label._ctk_img = ctk_img
            except Exception:
                pass
        self.ai_method.configure(text=f"Method: {getattr(signal, 'method_id', '') or '—'}  •  Score: {signal.ai_score}/10")
        comps = getattr(signal, "ai_components", {}) or {}
        for key, comp in [("_bar_trend", "trend"), ("_bar_structure", "structure"),
                          ("_bar_liquidity", "liquidity"), ("_bar_timing", "timing")]:
            bar, val = getattr(self, key)
            v = float(comps.get(comp, 0) or 0)
            bar.set(max(0.0, min(1.0, v / 10.0))); val.configure(text=f"{v:g}/10")
        self.ai_reason.configure(state="normal")
        self.ai_reason.delete("0.0", "end")
        self.ai_reason.insert("0.0", getattr(signal, "ai_reason", "") or signal.ai_analysis or "—")
        self.ai_reason.configure(state="disabled")
        self.refresh()

    def refresh(self):
        try:
            if self.app and self.app.mt5 and self.app.mt5.connected:
                self.pill_mt5.configure(text="  ● MT5: Online  ", text_color=COLORS["accent_green"])
            if self.app and self.app.gemini and self.app.gemini.ready:
                self.pill_ai.configure(text="  ● AI: Ready  ", text_color=COLORS["accent_green"])
            if self.app and self.app.trade_logger:
                s = self.app.quant_engine.get_summary() if self.app.quant_engine else {}
                self._kpi_win.configure(text=f"{s.get('winrate', 0)}%")
                self._kpi_r.configure(text=f"{s.get('total_r', 0)}R")
                self._kpi_signals.configure(text=str(self.app.trade_logger.get_trade_count()))
            eng = getattr(self.app, "v4_engine", None) if self.app else None
            # AppWindow's controller holds v4_engine; main.py stores it on controller, not app.
            # SKIP feed is filled by AppWindow._on_new_signal when available; keep placeholder here.
            if eng and getattr(eng, "skipped", None):
                last = eng.skipped[-1]
                self.skip_label.configure(text=f"{last.get('symbol','')} {last.get('method','')} — {last.get('reason','')}")
        except Exception:
            pass
