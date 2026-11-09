"""Hằng số toán học lý thuyết chính xác cho Bingo18 (3 xúc xắc 1..6).

Tính toán hoàn toàn bằng số nguyên và phân số (fractions.Fraction)
để đảm bảo tính chính xác tuyệt đối, không có sai số làm tròn số thực.
"""

from fractions import Fraction
import itertools

# Tổng số biến cố có thứ tự: 6^3 = 216
TOTAL_ORDERED_OUTCOMES = 216

# Số cách xuất hiện w(s) cho tổng s = 3..18
# Tương ứng hệ số của (x + x^2 + x^3 + x^4 + x^5 + x^6)^3
THEORETICAL_WAYS = {
    3: 1,
    4: 3,
    5: 6,
    6: 10,
    7: 15,
    8: 21,
    9: 25,
    10: 27,
    11: 27,
    12: 25,
    13: 21,
    14: 15,
    15: 10,
    16: 6,
    17: 3,
    18: 1
}

assert sum(THEORETICAL_WAYS.values()) == TOTAL_ORDERED_OUTCOMES

# Vector xác suất lý thuyết p(s) = w(s) / 216
THEORETICAL_PROB_SUM = {
    s: Fraction(w, TOTAL_ORDERED_OUTCOMES)
    for s, w in THEORETICAL_WAYS.items()
}

assert sum(THEORETICAL_PROB_SUM.values()) == Fraction(1, 1)

# Phân nhóm Lớn / Hòa / Nhỏ
# Nhỏ: 3..9; Hòa: 10..11; Lớn: 12..18
P_SMALL = Fraction(81, TOTAL_ORDERED_OUTCOMES)
P_DRAW = Fraction(54, TOTAL_ORDERED_OUTCOMES)
P_BIG = Fraction(81, TOTAL_ORDERED_OUTCOMES)

assert sum(THEORETICAL_PROB_SUM[s] for s in range(3, 10)) == P_SMALL
assert sum(THEORETICAL_PROB_SUM[s] for s in (10, 11)) == P_DRAW
assert sum(THEORETICAL_PROB_SUM[s] for s in range(12, 19)) == P_BIG
assert P_SMALL + P_DRAW + P_BIG == Fraction(1, 1)

# Phân loại dạng kết quả
# Tam hoa: 6 biến cố (111, 222, 333, 444, 555, 666) -> 6/216
# Đúng 1 cặp: 6 * 5 * 3 = 90 biến cố -> 90/216
# 3 số khác nhau: 6 * 5 * 4 = 120 biến cố -> 120/216
P_ANY_TRIPLE = Fraction(6, TOTAL_ORDERED_OUTCOMES)
P_EXACT_ONE_PAIR = Fraction(90, TOTAL_ORDERED_OUTCOMES)
P_THREE_DISTINCT = Fraction(120, TOTAL_ORDERED_OUTCOMES)

assert P_ANY_TRIPLE + P_EXACT_ONE_PAIR + P_THREE_DISTINCT == Fraction(1, 1)

# Xác suất một số cụ thể x in [1..6] xuất hiện k lần (k in 0..3)
# Phân phối nhị thức Binomial(3, 1/6)
P_NUMBER_OCCURRENCE = {
    0: Fraction(125, TOTAL_ORDERED_OUTCOMES),  # (5/6)^3
    1: Fraction(75, TOTAL_ORDERED_OUTCOMES),   # 3 * (1/6) * (5/6)^2
    2: Fraction(15, TOTAL_ORDERED_OUTCOMES),   # 3 * (1/6)^2 * (5/6)
    3: Fraction(1, TOTAL_ORDERED_OUTCOMES)     # (1/6)^3
}

assert sum(P_NUMBER_OCCURRENCE.values()) == Fraction(1, 1)

# P(tổng kỳ này = tổng kỳ trước) dưới giả thuyết H0 độc lập:
# sum_{s=3}^{18} p_s^2 = 4332 / 46656 ≈ 0.092850
P_CONSECUTIVE_SAME_SUM = sum(p**2 for p in THEORETICAL_PROB_SUM.values())
assert P_CONSECUTIVE_SAME_SUM == Fraction(4332, 46656)

# 56 tổ hợp không thứ tự (unordered combinations with replacement)
# Phân rã theo số hoán vị tương ứng
UNORDERED_COMBINATIONS = []
for combo in itertools.combinations_with_replacement(range(1, 7), 3):
    d1, d2, d3 = combo
    if d1 == d2 == d3:
        perms = 1  # Tam hoa
    elif d1 == d2 or d2 == d3 or d1 == d3:
        perms = 3  # Đúng 1 cặp
    else:
        perms = 6  # 3 số khác nhau
    UNORDERED_COMBINATIONS.append({
        "combination": combo,
        "sum": d1 + d2 + d3,
        "permutations": perms,
        "probability": Fraction(perms, TOTAL_ORDERED_OUTCOMES)
    })

assert len(UNORDERED_COMBINATIONS) == 56
assert sum(c["permutations"] for c in UNORDERED_COMBINATIONS) == TOTAL_ORDERED_OUTCOMES

# Ngưỡng Chi-Square lý thuyết (df=15, alpha=0.05)
# scipy.stats.chi2.ppf(0.95, 15) ≈ 24.995790139728616
CHI2_CRITICAL_DF15_ALPHA05 = 24.995790139728616
