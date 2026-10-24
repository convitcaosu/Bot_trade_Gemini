"""
V4 AI judge — structured verdicts, never free-text score parsing.

The old code did:  score = 8.5 if Gemini was offline, and direction by
searching for the substring 'SELL' in free text.  That is gone.

Rules:
- If Gemini is not ready, verdict is SKIP with reason 'ai_offline'.
  No signal is dispatched on a guessed score.
- If the model reply is not valid JSON with the required fields,
  verdict is SKIP with reason 'ai_parse_failed'.
- A verdict only counts if direction matches the candidate direction.
- AI may adjust entry/SL/TP, but the gate (v4_gate) re-validates them.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .v4_candidates import Candidate


@dataclass
class AIVerdict:
    decision: str  # BUY / SELL / SKIP
    confidence: float = 0.0  # 0..10
    entry_price: float = 0.0
    stop_loss: float = 0.0
    tp1: float = 0.0
    tp2: float = 0.0
    tp3: float = 0.0
    components: dict = field(default_factory=dict)  # trend/structure/liquidity/timing
    reason: str = ""
    raw: str = ""


def build_judge_prompt(candidate: Candidate, method_history: str = "") -> str:
    f = candidate.to_feature_dict()
    return f"""
Bạn là chuyên gia SMC/ICT. Chỉ trả về JSON hợp lệ, không thêm văn bản ngoài JSON.
Schema bắt buộc:
{{"decision": "BUY|SELL|SKIP", "confidence": 0-10,
 "entry_price": number, "stop_loss": number, "tp1": number, "tp2": number, "tp3": number,
 "components": {{"trend": 0-10, "structure": 0-10, "liquidity": 0-10, "timing": 0-10}},
 "reason": "1-2 câu, nêu rõ bằng chứng mạnh nhất và yếu nhất"}}

Quy tắc:
- SKIP nếu không có BOS/CHoCH xác nhận và không có OB/FVG đủ mạnh, hoặc nếu xu hướng khung lớn ngược hướng và không có bằng chứng đảo chiều mạnh.
- Không dùng RR cố định. SL phải nằm sau râu sweep / OB, TP1 là swing gần nhất, TP2 là OB/cản tiếp theo.
- Spread/ATR cao thì phải trừ vào RR, không được coi như không có spread.

Ứng viên:
{f}

Lịch sử phương pháp này (nếu có):
{method_history or "Chưa có dữ liệu."}
""".strip()


def parse_verdict(raw: str, candidate: Candidate) -> AIVerdict:
    if not raw or not raw.strip():
        return AIVerdict("SKIP", reason="ai_empty_reply", raw=raw or "")
    # Tolerate ```json fences, but nothing else is accepted as a signal.
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return AIVerdict("SKIP", reason="ai_parse_failed", raw=raw)
    try:
        d = json.loads(m.group(0))
    except Exception:
        return AIVerdict("SKIP", reason="ai_parse_failed", raw=raw)
    decision = str(d.get("decision", "SKIP")).upper()
    if decision not in ("BUY", "SELL", "SKIP"):
        return AIVerdict("SKIP", reason="ai_bad_decision", raw=raw)
    if decision != "SKIP" and decision != candidate.direction:
        return AIVerdict("SKIP", reason="ai_direction_mismatch", raw=raw)
    try:
        conf = float(d.get("confidence", 0))
    except Exception:
        conf = 0.0
    def _num(k, fallback):
        try:
            return float(d.get(k, fallback))
        except Exception:
            return fallback
    return AIVerdict(
        decision=decision, confidence=max(0.0, min(10.0, conf)),
        entry_price=_num("entry_price", candidate.entry_price),
        stop_loss=_num("stop_loss", candidate.stop_loss),
        tp1=_num("tp1", candidate.tp1), tp2=_num("tp2", candidate.tp2),
        tp3=_num("tp3", candidate.tp3),
        components=d.get("components", {}) if isinstance(d.get("components", {}), dict) else {},
        reason=str(d.get("reason", ""))[:500], raw=raw,
    )


def judge_with_gemini(gemini_brain, candidate: Candidate, chart_path: str = "",
                      method_history: str = "") -> AIVerdict:
    """Call Gemini via its structured prompt. Returns SKIP if not ready."""
    if gemini_brain is None or not getattr(gemini_brain, "ready", False):
        return AIVerdict("SKIP", reason="ai_offline")
    prompt = build_judge_prompt(candidate, method_history)
    try:
        # gemini_brain gains analyze_text() in the V4 patch; fall back to
        # the old chart path only if a chart exists, still parsed as JSON.
        if hasattr(gemini_brain, "analyze_text"):
            raw = gemini_brain.analyze_text(prompt)
        elif chart_path:
            raw = gemini_brain.analyze_chart(chart_path, stats_summary=method_history)
        else:
            return AIVerdict("SKIP", reason="ai_no_input")
    except Exception as e:
        return AIVerdict("SKIP", reason=f"ai_error: {e}")
    return parse_verdict(raw, candidate)
