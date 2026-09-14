"""STT / LLM HTTP 呼叫，只用標準函式庫 urllib。相容 OpenAI 格式的 endpoint。"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
import uuid

STT_TIMEOUT = 120
LLM_TIMEOUT = 120
MODELS_TIMEOUT = 15

_insecure_ssl = False
_warned_insecure = False


def set_insecure_ssl(value: bool) -> None:
    """關閉 TLS 憑證驗證。受限網路（公司 MITM proxy、自簽憑證的內部 endpoint）才用。"""
    global _insecure_ssl
    _insecure_ssl = bool(value)


def insecure_ssl() -> bool:
    """環境變數 TAPSAY_INSECURE_SSL=1 可在不改設定檔的情況下強制關閉驗證。"""
    if os.environ.get("TAPSAY_INSECURE_SSL", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    return _insecure_ssl


def _ssl_context() -> ssl.SSLContext | None:
    """回傳 None＝用 urllib 預設（正常驗證）。"""
    if not insecure_ssl():
        return None
    global _warned_insecure
    if not _warned_insecure:
        _warned_insecure = True
        print("[tapsay] 警告：已關閉 TLS 憑證驗證，連線可被中間人竊聽", file=sys.stderr)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class ApiError(RuntimeError):
    pass


def _url(endpoint: str, path: str) -> str:
    base = (endpoint or "").strip().rstrip("/")
    if not base:
        raise ApiError("尚未設定 Endpoint")
    if base.endswith(path):  # 使用者填了完整網址
        return base
    return base + path


def _request(url: str, api_key: str, data: bytes | None, content_type: str | None, timeout: int) -> dict:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:400].decode("utf-8", "replace").strip()
        raise ApiError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise ApiError(
                f"憑證驗證失敗：{exc.reason.verify_message or exc.reason}"
                "（受限網路可在設定勾選「關閉 TLS 憑證驗證」）"
            ) from exc
        raise ApiError(f"連線失敗：{exc.reason}") from exc
    except TimeoutError as exc:
        raise ApiError("連線逾時") from exc

    text = body.decode("utf-8", "replace").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}  # 有些 STT endpoint 直接回純文字
    if not isinstance(parsed, dict):
        raise ApiError("回應格式不正確")
    if "error" in parsed:
        err = parsed["error"]
        msg = err.get("message") if isinstance(err, dict) else err
        raise ApiError(str(msg))
    return parsed


def _multipart(fields: dict[str, str], filename: str, content: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    out = bytearray()
    for name, value in fields.items():
        out += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        ).encode("utf-8")
    out += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8")
    out += content + b"\r\n"
    out += f"--{boundary}--\r\n".encode("utf-8")
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def transcribe(endpoint: str, api_key: str, model: str, wav: bytes) -> str:
    if not model.strip():
        raise ApiError("尚未設定 STT Model")
    body, content_type = _multipart({"model": model.strip()}, "audio.wav", wav)
    data = _request(_url(endpoint, "/audio/transcriptions"), api_key, body, content_type, STT_TIMEOUT)
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError("STT 沒有回傳文字")
    return text.strip()


def refine(endpoint: str, api_key: str, model: str, prompt: str, text: str) -> str:
    if not model.strip():
        raise ApiError("尚未設定 LLM Model")
    payload = {
        "model": model.strip(),
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
    }
    data = _request(
        _url(endpoint, "/chat/completions"),
        api_key,
        json.dumps(payload).encode("utf-8"),
        "application/json",
        LLM_TIMEOUT,
    )
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ApiError("LLM 回應格式不正確") from exc
    if isinstance(content, list):  # 少數 provider 回 content parts
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if not isinstance(content, str) or not content.strip():
        raise ApiError("LLM 沒有回傳文字")
    return content.strip()


def list_models(endpoint: str, api_key: str) -> list[str]:
    data = _request(_url(endpoint, "/models"), api_key, None, None, MODELS_TIMEOUT)
    items = data.get("data")
    if not isinstance(items, list):
        raise ApiError("Endpoint 沒有回傳模型清單")
    names = [m.get("id") for m in items if isinstance(m, dict) and m.get("id")]
    return sorted(str(n) for n in names)
