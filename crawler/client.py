"""HTTP Client cho Vietlott Crawler với Exponential Backoff, Jitter và Rate Limiting."""

import json
import logging
import random
import time
from datetime import datetime
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)

DEFAULT_URL = (
    "https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.GameBingoCompareWebPart,"
    "Vietlott.PlugIn.WebParts.ashx"
)


class VietlottClient:
    """Client giao tiếp với hệ thống Vietlott AjaxPro."""

    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        max_req_per_hour: int = 150,
        user_agent: str = "Bingo18Analytics/1.0 (+https://github.com/vietlot; contact@bingo18analytics.local)",
    ):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_req_per_hour = max_req_per_hour
        self.user_agent = user_agent
        self.request_timestamps: list[float] = []

    def _wait_for_rate_limit(self) -> None:
        """Đảm bảo không vượt quá giới hạn <= 20 request/giờ."""
        now = time.time()
        one_hour_ago = now - 3600.0
        # Loại bỏ các mốc thời gian ngoài 1 giờ trước
        self.request_timestamps = [t for t in self.request_timestamps if t > one_hour_ago]

        if len(self.request_timestamps) >= self.max_req_per_hour:
            oldest = self.request_timestamps[0]
            sleep_needed = (oldest + 3600.0) - now + 1.0
            if sleep_needed > 0:
                logger.warning(f"Đạt giới hạn tốc độ. Tạm dừng {sleep_needed:.1f}s...")
                time.sleep(sleep_needed)

    def fetch_page(self, page_index: int = 1, page_size: int = 10) -> Optional[str]:
        """Gửi request lấy kết quả các kỳ quay theo trang.

        Áp dụng Exponential Backoff + Jitter khi gặp sự cố tạm thời.
        Dừng ngay khi gặp 403 / 429.
        """
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "text/plain; charset=utf-8",
            "X-AjaxPro-Method": "ServerSideDrawResult",
            "Origin": "https://vietlott.vn",
            "Referer": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-bingo18",
        }

        payload = json.dumps({
            "ORenderInfo": {
                "SiteId": "main.frontend.vi",
                "SiteAlias": "main.vi",
                "SiteLang": "vi",
                "SiteName": "Vietlott",
            },
            "GameId": "8",
            "GameDrawNo": "",
            "number": "",
            "DrawDate": "",
            "PageIndex": page_index,
            "TotalRow": page_size,
        })

        for attempt in range(1, self.max_retries + 1):
            self._wait_for_rate_limit()
            try:
                self.request_timestamps.append(time.time())
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(self.url, content=payload.encode("utf-8"), headers=headers)

                if resp.status_code == 200:
                    return resp.text

                if resp.status_code in (403, 429):
                    logger.error(f"HTTP {resp.status_code} từ máy chủ Vietlott. Dừng lại.")
                    return None

                logger.warning(f"Thử lần {attempt}: Máy chủ trả về mã HTTP {resp.status_code}")

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning(f"Thử lần {attempt} thất bại do lỗi mạng: {e}")

            if attempt < self.max_retries:
                # Exponential backoff với random jitter
                backoff = (self.backoff_factor ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(backoff)

        logger.error(f"Đã thử {self.max_retries} lần nhưng không thể lấy dữ liệu từ Vietlott.")
        return None
