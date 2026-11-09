#!/usr/bin/env bash
# Kịch bản chạy tự động cho cron và systemd trên Linux
# Cú pháp crontab đề xuất:
# */3 * * * * flock -n /tmp/bingo18.lock timeout 150 /opt/bingo18/scripts/run.sh >> /var/log/bingo18/crawl.log 2>&1

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# Jitter ngẫu nhiên từ 0 đến 20 giây để tránh tải dồn
sleep $((RANDOM % 20))

# Nạp biến môi trường nếu có
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "[$(date -Iseconds)] Bắt đầu chu kỳ cào và kiểm tra tính toàn vẹn..."

# 1. Chạy Crawler
CRAWL_OUT=$(python3 -m crawler.run 2>&1)
echo "$CRAWL_OUT"

# 2. Kiểm tra toàn vẹn
python3 -m stats.integrity

# 3. Commit nếu có dữ liệu mới
if git status --porcelain | grep -q "data/"; then
  NEW_DRAWS_LINE=$(echo "$CRAWL_OUT" | grep "data: +")
  if [ -n "$NEW_DRAWS_LINE" ]; then
    COMMIT_MSG="$NEW_DRAWS_LINE"
  else
    COMMIT_MSG="data: update draws $(date +'%Y-%m-%d %H:%M')"
  fi

  git add data/
  git commit -m "$COMMIT_MSG"
  git push origin master || echo "Cảnh báo: Không thể đẩy commit lên remote."
fi

# 4. Gửi heartbeat tới Healthchecks
if [ -n "${HEALTHCHECKS_URL:-}" ]; then
  curl -fsS -m 10 --retry 3 "${HEALTHCHECKS_URL}" > /dev/null || true
fi

echo "[$(date -Iseconds)] Hoàn tất chu kỳ cào."
