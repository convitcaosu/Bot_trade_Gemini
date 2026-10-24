"""
=============================================================================
QUANT ENGINE — Phân tích thống kê & trực quan hóa
- Tính toán winrate, R:R, equity curve
- Vẽ 4 biểu đồ pro dark theme
- Phân tích theo phiên, symbol, râu nến
=============================================================================
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REPORT_IMG_PATH, COLORS

# Font tiếng Việt — fallback nếu không có
try:
    plt.rcParams['font.family'] = ['Segoe UI', 'DejaVu Sans', 'sans-serif']
except Exception:
    pass


class QuantEngine:
    """Engine phân tích định lượng — tính thống kê & vẽ biểu đồ"""

    def __init__(self, trade_logger):
        self.logger = trade_logger

    def get_full_stats(self) -> dict:
        """Tính toán đầy đủ các chỉ số thống kê"""
        df = self.logger.get_all_trades()
        if df.empty:
            return {"error": "Chưa có dữ liệu"}

        total = len(df)
        wins = len(df[df["outcome"].isin(["WIN", "PARTIAL"])])
        losses = len(df[df["outcome"] == "LOSS"])
        pending = total - wins - losses
        winrate = (wins / max(1, wins + losses)) * 100
        
        # Convert rr_achieved safely
        rr_series = pd.to_numeric(df["rr_achieved"], errors="coerce").fillna(0.0)
        win_mask = df["outcome"].isin(["WIN", "PARTIAL"])
        avg_rr = rr_series[win_mask].mean() if wins > 0 else 0.0
        total_rr = rr_series.sum()

        # Streak
        outcomes = df["outcome"].tolist()
        current_streak = 0
        streak_type = ""
        for o in reversed(outcomes):
            if o in ["WIN", "LOSS"]:
                if not streak_type:
                    streak_type = o
                if o == streak_type:
                    current_streak += 1
                else:
                    break

        # By session
        session_stats = {}
        if "session" in df.columns:
            for sess in ["London", "New York", "Asian"]:
                sdf = df[df["session"] == sess]
                if len(sdf) > 0:
                    sw = len(sdf[sdf["outcome"] == "WIN"])
                    st = len(sdf[sdf["outcome"].isin(["WIN", "LOSS"])])
                    session_stats[sess] = {
                        "count": len(sdf),
                        "winrate": round(sw / max(1, st) * 100, 1),
                    }

        # By symbol
        symbol_stats = {}
        if "symbol" in df.columns:
            for sym in df["symbol"].unique():
                sdf = df[df["symbol"] == sym]
                sw = len(sdf[sdf["outcome"] == "WIN"])
                st = len(sdf[sdf["outcome"].isin(["WIN", "LOSS"])])
                symbol_stats[sym] = {
                    "count": len(sdf),
                    "winrate": round(sw / max(1, st) * 100, 1),
                    "total_rr": round(sdf["rr_achieved"].sum(), 1),
                }

        best_sess = "London"
        if session_stats:
            best_sess = max(session_stats.items(), key=lambda x: x[1].get("winrate", 0))[0]

        return {
            "total": total,
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "winrate": round(winrate, 1),
            "avg_rr": round(avg_rr, 1),
            "total_rr": round(total_rr, 1),
            "total_r": round(total_rr, 1),
            "streak": f"{current_streak}{streak_type[0] if streak_type else ''}",
            "best_session": best_sess,
            "session_stats": session_stats,
            "symbol_stats": symbol_stats,
        }

    def get_summary(self) -> dict:
        """Alias tương thích cho get_full_stats"""
        return self.get_full_stats()

    def get_stats_text(self) -> str:
        """Tóm tắt thống kê dạng text — dùng cho Gemini và Telegram"""
        stats = self.get_full_stats()
        if "error" in stats:
            return stats["error"]

        lines = [
            f"Tổng lệnh: {stats['total']} | Thắng: {stats['wins']} | Thua: {stats['losses']}",
            f"Winrate: {stats['winrate']}% | R:R TB: 1:{stats['avg_rr']} | Tổng R: +{stats['total_rr']}R",
            f"Streak hiện tại: {stats['streak']}",
            "",
            "Theo phiên:"
        ]
        for sess, data in stats.get("session_stats", {}).items():
            lines.append(f"  {sess}: {data['winrate']}% ({data['count']} lệnh)")

        lines.append("")
        lines.append("Theo symbol:")
        for sym, data in stats.get("symbol_stats", {}).items():
            lines.append(f"  {sym}: {data['winrate']}% | {data['total_rr']}R ({data['count']} lệnh)")

        return "\n".join(lines)

    def generate_report_image(self, save_path: str = None) -> str:
        """Alias cho generate_report_chart"""
        return self.generate_report_chart(save_path)

    def generate_report_chart(self, save_path: str = None) -> str:
        """
        Vẽ 4 biểu đồ phân tích pro — Dark theme TradingView style.
        1. Winrate theo Phiên
        2. Winrate theo Râu nến
        3. Equity Curve (R:R lũy kế)
        4. Breakdown Thắng/Thua (Donut)
        """
        save_path = save_path or REPORT_IMG_PATH
        df = self.logger.get_all_trades()

        if df.empty or len(df) < 3:
            return ""

        total = len(df)
        wins = len(df[df["outcome"].isin(["WIN", "PARTIAL"])])
        losses = len(df[df["outcome"] == "LOSS"])
        winrate = wins / max(1, wins + losses) * 100
        rr_series = pd.to_numeric(df["rr_achieved"], errors="coerce").fillna(0.0)
        total_rr = rr_series.sum()

        # ─── Setup Figure ───
        plt.style.use("dark_background")
        fig, axs = plt.subplots(2, 2, figsize=(16, 10))
        fig.patch.set_facecolor("#131722")

        title = f"PERFORMANCE REPORT  |  {total} Trades  |  Winrate: {winrate:.1f}%  |  Total: +{total_rr:.1f}R"
        fig.suptitle(title, fontsize=15, fontweight="bold", color="#00e5ff",
                     fontfamily="monospace", y=0.98)

        # Color palette
        c_green = "#26a69a"
        c_red = "#ef5350"
        c_blue = "#2962ff"
        c_cyan = "#00e5ff"
        c_yellow = "#f7931a"
        c_purple = "#ab47bc"
        c_text = "#d1d4dc"
        c_muted = "#787b86"

        # ─── 1. Winrate by Session ───
        ax = axs[0, 0]
        ax.set_facecolor("#1e222d")
        session_colors = {"London": c_blue, "New York": c_purple, "Asian": c_yellow}
        if "session" in df.columns:
            sessions = ["Asian", "London", "New York"]
            wr_vals = []
            bar_colors = []
            for s in sessions:
                sdf = df[df["session"] == s]
                if len(sdf) > 0:
                    sw = len(sdf[sdf["outcome"] == "WIN"])
                    st = len(sdf[sdf["outcome"].isin(["WIN", "LOSS"])])
                    wr_vals.append(sw / max(1, st) * 100)
                else:
                    wr_vals.append(0)
                bar_colors.append(session_colors.get(s, c_muted))

            bars = ax.bar(sessions, wr_vals, color=bar_colors, width=0.5,
                          edgecolor="none", alpha=0.9, zorder=3)
            for bar, val in zip(bars, wr_vals):
                ax.text(bar.get_x() + bar.get_width() / 2, val + 2,
                        f"{val:.1f}%", ha="center", va="bottom",
                        color=c_text, fontweight="bold", fontsize=11)

        ax.set_title("Winrate by Session", color=c_text, fontsize=12, fontweight="bold")
        ax.set_ylim(0, 110)
        ax.grid(True, axis="y", alpha=0.1, color="#363a45")
        ax.tick_params(colors=c_muted)
        for spine in ax.spines.values():
            spine.set_color("#2a2e39")

        # ─── 2. Winrate by Wick % ───
        ax = axs[0, 1]
        ax.set_facecolor("#1e222d")
        if "wick_percent" in df.columns:
            df["wick_grp"] = pd.cut(df["wick_percent"],
                                     bins=[0, 50, 65, 100],
                                     labels=["< 50%", "50-65%", "> 65%"])
            wick_colors = [c_red, c_yellow, c_green]
            grps = ["< 50%", "50-65%", "> 65%"]
            wr_vals = []
            for g in grps:
                gdf = df[df["wick_grp"] == g]
                if len(gdf) > 0:
                    sw = len(gdf[gdf["outcome"] == "WIN"])
                    st = len(gdf[gdf["outcome"].isin(["WIN", "LOSS"])])
                    wr_vals.append(sw / max(1, st) * 100)
                else:
                    wr_vals.append(0)

            bars = ax.bar(grps, wr_vals, color=wick_colors, width=0.5,
                          edgecolor="none", alpha=0.9, zorder=3)
            for bar, val in zip(bars, wr_vals):
                ax.text(bar.get_x() + bar.get_width() / 2, val + 2,
                        f"{val:.1f}%", ha="center", va="bottom",
                        color=c_text, fontweight="bold", fontsize=11)

        ax.set_title("Winrate by Wick Length", color=c_text, fontsize=12, fontweight="bold")
        ax.set_ylim(0, 110)
        ax.grid(True, axis="y", alpha=0.1, color="#363a45")
        ax.tick_params(colors=c_muted)
        for spine in ax.spines.values():
            spine.set_color("#2a2e39")

        # ─── 3. Equity Curve ───
        ax = axs[1, 0]
        ax.set_facecolor("#1e222d")
        cum_rr = df["rr_achieved"].cumsum().values
        x_vals = np.arange(len(cum_rr))

        # Gradient fill
        ax.fill_between(x_vals, cum_rr, alpha=0.15, color=c_cyan)
        ax.plot(x_vals, cum_rr, color=c_cyan, linewidth=2.5, zorder=5)

        # Highlight current value
        if len(cum_rr) > 0:
            ax.scatter([x_vals[-1]], [cum_rr[-1]], color=c_cyan, s=60, zorder=6)
            ax.text(x_vals[-1] + 0.5, cum_rr[-1],
                    f"+{cum_rr[-1]:.1f}R", color=c_cyan, fontsize=11,
                    fontweight="bold", va="center")

        ax.axhline(0, color=c_muted, linestyle="--", alpha=0.4)
        ax.set_title(f"Equity Curve (Total: +{total_rr:.1f}R)", color=c_text,
                     fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.1, color="#363a45")
        ax.tick_params(colors=c_muted)
        for spine in ax.spines.values():
            spine.set_color("#2a2e39")

        # ─── 4. Win/Loss Donut ───
        ax = axs[1, 1]
        ax.set_facecolor("#1e222d")
        if wins + losses > 0:
            sizes = [wins, losses]
            colors_pie = [c_green, c_red]
            labels = [f"WIN ({wins})", f"LOSS ({losses})"]
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=colors_pie,
                autopct="%1.1f%%", startangle=90,
                wedgeprops=dict(width=0.45, edgecolor="#131722", linewidth=3),
                textprops={"color": c_text, "fontsize": 11, "fontweight": "bold"},
            )
            for at in autotexts:
                at.set_color(c_text)
                at.set_fontweight("bold")

        ax.set_title("Win / Loss Distribution", color=c_text, fontsize=12, fontweight="bold")

        plt.tight_layout(rect=[0, 0.02, 1, 0.94])
        plt.savefig(save_path, dpi=180, facecolor="#131722", bbox_inches="tight")
        plt.close()

        return save_path

    def generate_symbol_chart(self, save_path: str = None) -> str:
        """Vẽ biểu đồ so sánh hiệu suất theo symbol"""
        df = self.logger.get_all_trades()
        if df.empty or "symbol" not in df.columns:
            return ""

        save_path = save_path or REPORT_IMG_PATH.replace(".png", "_symbols.png")

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor("#131722")
        ax.set_facecolor("#1e222d")

        symbols = df["symbol"].unique()
        sym_colors = ["#2962ff", "#26a69a", "#f7931a", "#ab47bc", "#ef5350"]
        wr_vals = []
        rr_vals = []
        for sym in symbols:
            sdf = df[df["symbol"] == sym]
            sw = len(sdf[sdf["outcome"] == "WIN"])
            st = len(sdf[sdf["outcome"].isin(["WIN", "LOSS"])])
            wr_vals.append(sw / max(1, st) * 100)
            rr_vals.append(sdf["rr_achieved"].sum())

        x = np.arange(len(symbols))
        width = 0.35
        bars1 = ax.bar(x - width / 2, wr_vals, width, label="Winrate %",
                        color=sym_colors[:len(symbols)], alpha=0.8)
        ax2 = ax.twinx()
        bars2 = ax2.bar(x + width / 2, rr_vals, width, label="Total R:R",
                         color=sym_colors[:len(symbols)], alpha=0.4)

        ax.set_xticks(x)
        ax.set_xticklabels(symbols, color="#d1d4dc")
        ax.set_ylabel("Winrate %", color="#d1d4dc")
        ax2.set_ylabel("Total R:R", color="#d1d4dc")
        ax.set_title("Performance by Symbol", color="#d1d4dc", fontsize=14, fontweight="bold")

        ax.tick_params(colors="#787b86")
        ax2.tick_params(colors="#787b86")
        for spine in ax.spines.values():
            spine.set_color("#2a2e39")
        for spine in ax2.spines.values():
            spine.set_color("#2a2e39")

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, facecolor="#131722")
        plt.close()
        return save_path
