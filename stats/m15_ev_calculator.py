"""Mô-đun M15: Tính toán Giá trị kỳ vọng (EV), Tỷ lệ hoàn trả (RTP) và Lợi thế nhà cái (House Edge)."""

import json
from pathlib import Path
from typing import Dict, Optional

from stats.constants import (
    THEORETICAL_PROB_SUM,
    P_SMALL,
    P_DRAW,
    P_BIG,
    P_ANY_TRIPLE,
    P_NUMBER_OCCURRENCE
)


def compute_expected_values(config_path: Optional[Path] = None) -> Dict:
    """M15: Tính toán EV, RTP, House Edge cho từng cách chơi dựa trên config/payouts.json."""
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config" / "payouts.json"

    with open(config_path, "r", encoding="utf-8") as f:
        payouts_data = json.load(f)

    is_verified = payouts_data.get("verified", False)
    ticket_price = payouts_data.get("ticket_price", 10000)
    payouts = payouts_data.get("payouts", {})

    results = {
        "verified": is_verified,
        "warning": (
            None
            if is_verified
            else "CẢNH BÁO: Bảng hệ số thưởng chưa được người dùng xác minh chính thức. Kết quả chỉ mang tính tham khảo."
        ),
        "ticket_price": ticket_price,
        "bets": {}
    }

    # 1. Các tổng cụ thể 3..18
    sum_payouts = payouts.get("sum", {})
    results["bets"]["sum"] = {}
    for s in range(3, 19):
        p_s = float(THEORETICAL_PROB_SUM[s])
        mult = float(sum_payouts.get(str(s), 0.0))
        ev = (p_s * mult) - 1.0
        rtp = p_s * mult * 100.0
        house_edge = (1.0 - (p_s * mult)) * 100.0
        breakeven_prob = (1.0 / mult) if mult > 0 else 0.0

        results["bets"]["sum"][s] = {
            "sum": s,
            "prob": round(p_s, 6),
            "multiplier": mult,
            "expected_value": round(ev, 4),
            "rtp_pct": round(rtp, 2),
            "house_edge_pct": round(house_edge, 2),
            "breakeven_prob": round(breakeven_prob, 6)
        }

    # 2. Lớn / Nhỏ / Hòa
    bsd_payouts = payouts.get("big_small_draw", {})
    bsd_probs = {"small": float(P_SMALL), "draw": float(P_DRAW), "big": float(P_BIG)}
    results["bets"]["big_small_draw"] = {}
    for name, p in bsd_probs.items():
        mult = float(bsd_payouts.get(name, 0.0))
        ev = (p * mult) - 1.0
        rtp = p * mult * 100.0
        results["bets"]["big_small_draw"][name] = {
            "name": name,
            "prob": round(p, 6),
            "multiplier": mult,
            "expected_value": round(ev, 4),
            "rtp_pct": round(rtp, 2),
            "house_edge_pct": round(100.0 - rtp, 2)
        }

    # 3. Tam hoa bất kỳ
    triple_payouts = payouts.get("triple_number", {})
    any_triple_mult = float(triple_payouts.get("any_triple", 0.0))
    p_any_triple = float(P_ANY_TRIPLE)
    ev_triple = (p_any_triple * any_triple_mult) - 1.0
    rtp_triple = p_any_triple * any_triple_mult * 100.0
    results["bets"]["any_triple"] = {
        "prob": round(p_any_triple, 6),
        "multiplier": any_triple_mult,
        "expected_value": round(ev_triple, 4),
        "rtp_pct": round(rtp_triple, 2),
        "house_edge_pct": round(100.0 - rtp_triple, 2)
    }

    return results
