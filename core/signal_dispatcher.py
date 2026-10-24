"""
=============================================================================
SIGNAL DISPATCHER v3.0 — Bắn tín hiệu song song 2 nơi
- Signal với nhiều mức TP linh động
- Format Telegram pro với TP1/TP2/TP3
- Queue thread-safe cho UI
=============================================================================
"""
import os
import sys
import queue
import threading
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Callable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Signal:
    """Tín hiệu giao dịch v3.0 — SL/TP linh động, nhiều mức TP"""
    signal_id: str = ""
    timestamp: str = ""
    symbol: str = ""
    timeframe: str = ""
    direction: str = ""           # BUY / SELL / SKIP
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0      # TP chính (= tp2)
    tp1: float = 0.0              # TP bảo toàn
    tp2: float = 0.0              # TP trung bình
    tp3: float = 0.0              # TP tham vọng
    ai_score: float = 0.0
    ai_analysis: str = ""
    chart_image_path: str = ""
    session: str = ""
    wick_percent: float = 0.0
    sweep_pips: float = 0.0
    has_fvg: bool = False
    has_ob: bool = False
    market_structure: str = ""
    atr: float = 0.0
    rr_ratio: float = 0.0
    outcome: str = ""             # WIN / LOSS / PARTIAL / PENDING
    rr_achieved: float = 0.0
    tp_hit: str = ""              # TP1 / TP2 / TP3 / SL
    # V4 fields — method that proposed the candidate + AI breakdown.
    # ai_score is the AI confidence (0..10) from a parsed JSON verdict,
    # never a hard-coded 8.0/8.5 fallback.
    method_id: str = ""
    ai_reason: str = ""
    ai_components: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def risk_reward_ratio(self) -> float:
        if self.entry_price <= 0 or self.stop_loss <= 0:
            return 0
        risk = abs(self.entry_price - self.stop_loss)
        tp = self.tp2 if self.tp2 > 0 else self.take_profit
        reward = abs(tp - self.entry_price)
        return round(reward / risk, 1) if risk > 0 else 0

    def format_telegram(self) -> str:
        """Format signal cho Telegram — với TP1/TP2/TP3 linh động"""
        emoji = "🟢" if self.direction == "BUY" else ("🔴" if self.direction == "SELL" else "⚪")
        rr = self.risk_reward_ratio()

        msg = f"{emoji} *{self.direction}  {self.symbol}  {self.timeframe}*\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⏰ {self.timestamp}\n"
        msg += f"🎯 Entry: `{self.entry_price}`\n"
        msg += f"🛑 SL: `{self.stop_loss}`\n"

        # Nhiều mức TP
        if self.tp1 > 0:
            msg += f"🥇 TP1 (bảo toàn): `{self.tp1}` — chốt 40%\n"
        if self.tp2 > 0:
            msg += f"🥈 TP2 (mục tiêu): `{self.tp2}` — chốt 40%\n"
        if self.tp3 > 0:
            msg += f"🥉 TP3 (tham vọng): `{self.tp3}` — trailing 20%\n"
        if not self.tp1 and self.take_profit > 0:
            msg += f"✅ TP: `{self.take_profit}`\n"

        msg += f"📊 R:R ≈ 1:{rr}\n"
        if self.method_id:
            msg += f"🧩 Method: {self.method_id}\n"
        if self.ai_reason:
            msg += f"🧠 AI: {self.ai_reason}\n"
        if self.market_structure:
            msg += f"📐 Structure: {self.market_structure}\n"
        msg += f"⭐ AI Score: {self.ai_score}/10\n"
        msg += f"📍 Session: {self.session}\n"

        # Chiến lược
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💡 *Chiến lược:*\n"
        msg += f"• Hit TP1 → trailing SL lên breakeven\n"
        msg += f"• TP2 chốt phần lớn, để TP3 chạy\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"

        if self.ai_analysis:
            analysis = self.ai_analysis[:800]
            msg += f"\n🧠 *AI Analysis:*\n{analysis}\n"

        return msg


class SignalDispatcher:
    """Phân phối signal song song đến Desktop UI + Telegram"""

    def __init__(self):
        self._ui_queue: queue.Queue = queue.Queue()
        self._callbacks: List[Callable] = []
        self._signal_history: List[Signal] = []
        self._lock = threading.Lock()

    def register_callback(self, callback: Callable):
        """Đăng ký callback nhận signal (VD: Telegram sender)"""
        with self._lock:
            self._callbacks.append(callback)

    def dispatch(self, signal: Signal):
        """Bắn signal đến TẤT CẢ đích đồng thời"""
        with self._lock:
            self._signal_history.append(signal)

        # 1. Push to UI queue
        self._ui_queue.put(signal)

        # 2. Call all registered callbacks (non-blocking)
        for cb in self._callbacks:
            try:
                threading.Thread(target=cb, args=(signal,), daemon=True).start()
            except Exception as e:
                print(f"[SignalDispatcher] Callback error: {e}")

    def get_ui_signal(self, timeout: float = 0.1) -> Optional[Signal]:
        try:
            return self._ui_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_history(self, n: int = 50) -> List[Signal]:
        with self._lock:
            return list(self._signal_history[-n:])

    def clear_history(self):
        with self._lock:
            self._signal_history.clear()
