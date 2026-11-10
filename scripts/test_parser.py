import re

with open("fixtures/vietlott_sample_1.json", "r", encoding="utf-8") as f:
    import json
    data = json.load(f)

html = data["value"]["HtmlContent"]

# Check parsing
row_regex = re.compile(r"<tr[^>]*>([\s\S]*?)</tr>", re.IGNORECASE)
dice_regex = re.compile(r"<span[^>]*bong_tron_bingo[^>]*>(\d)</span>", re.IGNORECASE)

records = []
for m in row_regex.finditer(html):
    row_html = m.group(1)
    if "<th" in row_html:
        continue
    id_match = re.search(r"#(\d{7})", row_html)
    date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", row_html)
    dices = dice_regex.findall(row_html)
    if id_match and date_match and len(dices) == 3:
        d1, d2, d3 = int(dices[0]), int(dices[1]), int(dices[2])
        records.append({
            "draw_id": id_match.group(1),
            "date": f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}",
            "d1": d1, "d2": d2, "d3": d3, "total": d1 + d2 + d3,
            "result": f"{d1} {d2} {d3} {d1+d2+d3}"
        })

print(f"Parsed {len(records)} records successfully!")
for r in records[:3]:
    print(r)
