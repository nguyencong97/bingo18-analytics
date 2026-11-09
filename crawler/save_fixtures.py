"""Tải 5 mẫu thật từ Vietlott để lưu vào fixtures/ và tạo tài liệu cấu trúc."""

import json
import urllib.request
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")
fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
fixtures_dir.mkdir(parents=True, exist_ok=True)

url = "https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.GameBingoCompareWebPart,Vietlott.PlugIn.WebParts.ashx"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "text/plain; charset=utf-8",
    "X-AjaxPro-Method": "ServerSideDrawResult",
    "Origin": "https://vietlott.vn",
    "Referer": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-bingo18"
}

# Lấy 5 trang hoặc 5 truy vấn khác nhau
for page in range(1, 6):
    payload = json.dumps({
        "ORenderInfo": {
            "SiteId": "main.frontend.vi",
            "SiteAlias": "main.vi",
            "SiteLang": "vi",
            "SiteName": "Vietlott"
        },
        "GameId": "8",
        "GameDrawNo": "",
        "number": "",
        "DrawDate": "",
        "PageIndex": page,
        "TotalRow": 10
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = res.read().decode("utf-8")
            out_file = fixtures_dir / f"vietlott_sample_{page}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(data)
            print(f"Đã lưu {out_file.name} ({len(data)} bytes)")
    except Exception as e:
        print(f"Lỗi khi tải trang {page}: {e}")
