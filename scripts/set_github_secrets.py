"""Tự động thiết lập GitHub Actions Secrets qua GitHub API bằng PyNaCl."""

import base64
import json
import subprocess
import urllib.request
import urllib.error
from nacl import encoding, public


def get_git_token() -> str:
    p = subprocess.Popen(
        ["git", "credential", "fill"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    out, _ = p.communicate("protocol=https\nhost=github.com\n\n")
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise RuntimeError("Không tìm thấy GitHub token trong git credential manager.")


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder)
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def set_repo_secret(owner: str, repo: str, secret_name: str, secret_value: str, token: str) -> bool:
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "Bingo18Analytics/1.0",
        "Accept": "application/vnd.github+json",
    }
    # 1. Lấy public key của repo
    key_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    req = urllib.request.Request(key_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        key_data = json.loads(resp.read().decode("utf-8"))

    key_id = key_data["key_id"]
    public_key_b64 = key_data["key"]

    # 2. Mã hóa giá trị secret
    encrypted_value = encrypt_secret(public_key_b64, secret_value)

    # 3. Gửi PUT lưu secret
    put_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
    payload = json.dumps({"encrypted_value": encrypted_value, "key_id": key_id}).encode("utf-8")
    req_put = urllib.request.Request(put_url, data=payload, headers=headers, method="PUT")
    with urllib.request.urlopen(req_put) as resp:
        return resp.status in (201, 204)


if __name__ == "__main__":
    owner = "nguyencong97"
    repo = "bingo18-analytics"
    token = get_git_token()
    secrets = {
        "TELEGRAM_BOT_TOKEN": "8706050151:AAFL3nHaHU0lPdL5Wlsnk7-u_e3vbLdwulE",
        "TELEGRAM_CHAT_ID": "6042038660",
    }
    for k, v in secrets.items():
        ok = set_repo_secret(owner, repo, k, v, token)
        print(f"Set secret {k}: {'SUCCESS (201/204)' if ok else 'FAILED'}")
