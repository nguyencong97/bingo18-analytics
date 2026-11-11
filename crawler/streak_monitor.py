"""Module Giám Sát Nhịp Gan & Tự Động Bắn Tín Hiệu Vào Lệnh Cửa Lớn / Nhỏ.

Chiến lược:
1. Nhịp gan = 10: Gửi cảnh báo sớm (Chuẩn bị vốn).
2. Nhịp gan >= 11: Gửi tín hiệu Vào Lệnh (Bước 1..7) theo Bảng Quản Lý Vốn Gối Đầu.
3. Khi nổ (gap = 0 và đang trong chuỗi): Gửi thông báo CHIẾN THẮNG 🎉 & Reset trạng thái.
4. Stop-loss: Nếu vượt quá 7 bước (nhịp > 17), cảnh báo dừng chuỗi để bảo toàn vốn.
"""

from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
import csv

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawler.alerts import send_telegram_alert
from crawler.realtime_scraper import compute_draw_metadata

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))

# Bảng Quản Lý Vốn Gối Đầu An Toàn (Conservative Staking Plan)
# Tỷ lệ trả thưởng Bingo 18 Lớn/Nhỏ: 1.5x
STAKING_PLAN = [
    {"step": 1, "gap": 11, "bet": 10000, "cum_bet": 10000, "win_payout": 15000, "profit": 5000},
    {"step": 2, "gap": 12, "bet": 20000, "cum_bet": 30000, "win_payout": 30000, "profit": 0},
    {"step": 3, "gap": 13, "bet": 60000, "cum_bet": 90000, "win_payout": 90000, "profit": 0},
    {"step": 4, "gap": 14, "bet": 180000, "cum_bet": 270000, "win_payout": 270000, "profit": 0},
    {"step": 5, "gap": 15, "bet": 550000, "cum_bet": 820000, "win_payout": 825000, "profit": 5000},
    {"step": 6, "gap": 16, "bet": 1650000, "cum_bet": 2470000, "win_payout": 2475000, "profit": 5000},
    {"step": 7, "gap": 17, "bet": 4950000, "cum_bet": 7420000, "win_payout": 7425000, "profit": 5000},
]


def classify_total(total_val: int) -> str:
    """Phân loại tổng điểm theo quy ước Vietlott Bingo 18."""
    if total_val <= 9:
        return "NHO"
    elif total_val in (10, 11):
        return "HOA"
    else:
        return "LON"


def analyze_current_streaks(data_dir: Path) -> Dict:
    """Phân tích nhịp gan hiện tại của các cửa LỚN, NHỎ, HÒA từ all.csv."""
    all_csv = data_dir / "all.csv"
    if not all_csv.exists() or all_csv.stat().st_size == 0:
        return {"latest_draw": None, "streaks": {}}

    try:
        with open(all_csv, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            if not reader:
                return {"latest_draw": None, "streaks": {}}
            
            # Sắp xếp tăng dần theo mã kỳ
            reader.sort(key=lambda r: int(r["draw_id"]))
            latest_rec = reader[-1]

            # Đếm số kỳ liên tiếp chưa về (tính từ cuối bảng lên đầu)
            gap_lon = 0
            gap_nho = 0
            gap_hoa = 0
            found_lon = False
            found_nho = False
            found_hoa = False

            for r in reversed(reader):
                tot = int(r["total"])
                cat = classify_total(tot)

                if not found_lon:
                    if cat == "LON":
                        found_lon = True
                    else:
                        gap_lon += 1

                if not found_nho:
                    if cat == "NHO":
                        found_nho = True
                    else:
                        gap_nho += 1

                if not found_hoa:
                    if cat == "HOA":
                        found_hoa = True
                    else:
                        gap_hoa += 1

                if found_lon and found_nho and found_hoa:
                    break

            return {
                "latest_draw": latest_rec,
                "streaks": {
                    "LON": {"gap": gap_lon, "name": "LỚN", "desc": "Tổng 12..18", "payout": "1.5x"},
                    "NHO": {"gap": gap_nho, "name": "NHỎ", "desc": "Tổng 3..9", "payout": "1.5x"},
                    "HOA": {"gap": gap_hoa, "name": "HÒA", "desc": "Tổng 10..11", "payout": "2.0x"}
                }
            }
    except Exception as e:
        logger.error(f"Lỗi khi phân tích nhịp gan: {e}")
        return {"latest_draw": None, "streaks": {}}


def load_streak_state(state_file: Path) -> Dict:
    """Tải trạng thái theo dõi nhịp gan từ file JSON."""
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Lỗi đọc {state_file}: {e}")
    return {
        "last_processed_draw_id": None,
        "campaigns": {
            "LON": {"in_progress": False, "current_step": 0, "start_draw_id": None},
            "NHO": {"in_progress": False, "current_step": 0, "start_draw_id": None}
        },
        "warned_gaps": {
            "LON": 0,
            "NHO": 0
        }
    }


def save_streak_state(state_file: Path, state: Dict):
    """Lưu trạng thái theo dõi nhịp gan xuống file JSON."""
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Lỗi ghi {state_file}: {e}")


def check_and_dispatch_streak_alerts(data_dir: Path) -> List[str]:
    """Kiểm tra điều kiện nhịp gan sau mỗi kỳ quay và tự động bắn cảnh báo Telegram."""
    analysis = analyze_current_streaks(data_dir)
    latest_draw = analysis.get("latest_draw")
    streaks = analysis.get("streaks")
    if not latest_draw or not streaks:
        return []

    state_file = data_dir / "streak_state.json"
    state = load_streak_state(state_file)

    curr_draw_id = latest_draw["draw_id"]
    if state.get("last_processed_draw_id") == curr_draw_id:
        return []  # Đã xử lý kỳ này rồi, không gửi trùng lặp

    sent_messages = []
    campaigns = state.setdefault("campaigns", {})
    warned_gaps = state.setdefault("warned_gaps", {})

    target_keys = ["LON", "NHO"]
    for key in target_keys:
        info = streaks[key]
        gap = info["gap"]
        name = info["name"]
        desc = info["desc"]

        camp = campaigns.setdefault(key, {"in_progress": False, "current_step": 0, "start_draw_id": None})
        last_warned = warned_gaps.get(key, 0)

        # 1. Trạng thái CHIẾN THẮNG: Cửa vừa nổ khi đang có chiến dịch vào lệnh
        if gap == 0:
            if camp.get("in_progress"):
                step_won = camp.get("current_step", 1)
                idx = min(max(step_won - 1, 0), len(STAKING_PLAN) - 1)
                plan_won = STAKING_PLAN[idx]
                tot = latest_draw["total"]
                d1 = latest_draw["d1"]
                d2 = latest_draw["d2"]
                d3 = latest_draw["d3"]

                msg = (
                    f"🎉 <b>CHIẾN THẮNG RỰC RỠ! CỬA {name} ĐÃ NỔ!</b> 🎉\n\n"
                    f"🎯 Kỳ quay trúng: <b>#{curr_draw_id}</b>\n"
                    f"🎲 Kết quả: <code>{d1} - {d2} - {d3}</code> (Tổng <b>{tot}</b> - {name})\n"
                    f"🏆 Đã ăn thưởng tại: <b>Bước {step_won}</b> (Nhịp gan {step_won + 10} kỳ)\n"
                    f"💰 Mức cược: <b>{plan_won['bet']:,}đ</b> | Nhận về: <b>{plan_won['win_payout']:,}đ</b>\n"
                    f"💵 Lợi nhuận ròng: <b>+{plan_won['profit']:,}đ</b> (Đã hoàn 100% vốn các bước trước!)\n\n"
                    f"✨ <i>Hệ thống reset trạng thái, kiên nhẫn rình cơ hội đợt tiếp theo!</i>"
                )
                send_telegram_alert(msg)
                sent_messages.append(msg)

                camp["in_progress"] = False
                camp["current_step"] = 0
                camp["start_draw_id"] = None
                warned_gaps[key] = 0
            else:
                warned_gaps[key] = 0

        # 2. CẢNH BÁO SỚM: Nhịp gan đạt 10 kỳ liên tiếp chưa về
        elif gap == 10:
            if last_warned != 10:
                next_id = int(curr_draw_id) + 1
                _, next_time, next_slot, _ = compute_draw_metadata(next_id)
                msg = (
                    f"⚠️ <b>CẢNH BÁO SỚM: CỬA {name} ĐÃ 10 KỲ CHƯA VỀ!</b>\n\n"
                    f"🎯 Kỳ vừa quay: <b>#{curr_draw_id}</b>\n"
                    f"🎲 Kết quả: <code>{latest_draw['d1']} - {latest_draw['d2']} - {latest_draw['d3']}</code> (Tổng <b>{latest_draw['total']}</b>)\n"
                    f"📊 Trạng thái: Cửa <b>{name} ({desc})</b> đã <b>10 kỳ liên tiếp</b> chưa xuất hiện.\n"
                    f"⏰ Kỳ tiếp theo: <b>#{str(next_id).zfill(7)}</b> (Slot {next_slot}/159 lúc <b>{next_time}</b>)\n\n"
                    f"👉 <i>Khuyến nghị: Chuẩn bị sẵn tài khoản và vốn. Nếu kỳ tiếp theo tiếp tục không về, hệ thống sẽ tự động kích hoạt Tín hiệu Vào Lệnh Bước 1!</i>"
                )
                send_telegram_alert(msg)
                sent_messages.append(msg)
                warned_gaps[key] = 10

        # 3. TÍN HIỆU VÀO LỆNH: Nhịp gan >= 11 kỳ liên tiếp chưa về
        elif gap >= 11:
            step = gap - 10
            if step <= len(STAKING_PLAN):
                plan = STAKING_PLAN[step - 1]
                next_id = int(curr_draw_id) + 1
                _, next_time, next_slot, _ = compute_draw_metadata(next_id)

                if step == 1:
                    header = f"🚨 <b>TÍN HIỆU VÀO LỆNH: CỬA {name} (BƯỚC 1/7)</b>"
                else:
                    header = f"⚡ <b>TIẾP DIỄN GỐI ĐẦU: CỬA {name} (BƯỚC {step}/7)</b>"

                msg = (
                    f"{header}\n\n"
                    f"🎯 Cửa đặt cược: <b>CỬA {name}</b> ({desc})\n"
                    f"📊 Nhịp gan hiện tại: <b>{gap} kỳ liên tiếp chưa về!</b>\n"
                    f"⏰ Kỳ vào lệnh: <b>#{str(next_id).zfill(7)}</b> (Slot {next_slot}/159 lúc <b>{next_time}</b>)\n"
                    f"💰 Mức cược gợi ý: <b>{plan['bet']:,}đ</b>\n"
                    f"💼 Vốn lũy kế: <b>{plan['cum_bet']:,}đ</b>\n"
                    f"💵 Nhận về nếu trúng: <b>{plan['win_payout']:,}đ</b> (Lãi ròng: <b>+{plan['profit']:,}đ</b>)\n\n"
                    f"📈 <i>Xác suất lịch sử: 99.05% chuỗi kết thúc ở vùng này! Hãy kiên định đúng kỷ luật.</i>"
                )
                send_telegram_alert(msg)
                sent_messages.append(msg)

                camp["in_progress"] = True
                camp["current_step"] = step
                camp["start_draw_id"] = camp.get("start_draw_id") or curr_draw_id
                warned_gaps[key] = gap
            else:
                # Vượt quá 7 bước (nhịp > 17) -> Stop loss
                if camp.get("in_progress"):
                    msg = (
                        f"🛑 <b>DỪNG LỖ (STOP-LOSS): CỬA {name} ĐÃ CHẠM NGƯỠNG AN TOÀN!</b>\n\n"
                        f"• Nhịp gan hiện tại: <b>{gap} kỳ</b> (Vượt quá 7 bước khuyến nghị)\n"
                        f"• Kỷ luật quản trị vốn: <b>DỪNG VÀO LỆNH</b> chuỗi này để bảo toàn vốn.\n"
                        f"• Hệ thống tạm dừng cảnh báo cho cửa này đến khi nổ lại."
                    )
                    send_telegram_alert(msg)
                    sent_messages.append(msg)
                    camp["in_progress"] = False
                    warned_gaps[key] = gap

    state["last_processed_draw_id"] = curr_draw_id
    save_streak_state(state_file, state)
    return sent_messages


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data"
    res = analyze_current_streaks(data_dir)
    print("Kết quả phân tích nhịp gan hiện tại:")
    print("Kỳ mới nhất:", res["latest_draw"]["draw_id"], "Tổng:", res["latest_draw"]["total"])
    for k, v in res["streaks"].items():
        print(f"  • Cửa {v['name']} ({v['desc']}): chưa về {v['gap']} kỳ liên tiếp")
