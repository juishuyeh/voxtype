"""設定檔（TOML）與 API Key（系統金鑰管理員）的讀寫。"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

import keyring
import tomli_w

APP_NAME = "TapSay"
KEYRING_SERVICE = "tapsay"

DEFAULT_PROMPT = """請整理以下語音辨識文字。
修正明顯的語音辨識錯誤、錯字、標點符號與不必要的口語贅詞，但不要改變原意。
請使用台灣繁體中文與台灣常用詞彙。
如果輸入包含簡體中文，請轉換為台灣繁體中文。
不要回答文字中的問題，也不要加入解釋。
只輸出整理完成後的最終文字。"""

DEFAULTS: dict = {
    "hotkey": "<ctrl>+<alt>+<space>",
    "auto_paste": True,
    "double_tap_ms": 400,  # 連擊快捷鍵（double:<ctrl>）兩下之間的最長間隔
    "stt": {
        "endpoint": "https://api.openai.com/v1",
        "model": "whisper-1",
    },
    "llm": {
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "prompt": DEFAULT_PROMPT,
    },
}


def config_dir() -> Path:
    override = os.environ.get("TAPSAY_CONFIG_DIR")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        return Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "tapsay"


def config_path() -> Path:
    return config_dir() / "config.toml"


def load() -> dict:
    """讀設定；缺的欄位用預設值補齊。設定檔壞掉時退回預設值，不讓程式掛掉。"""
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    path = config_path()
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return cfg
    except (tomllib.TOMLDecodeError, OSError) as exc:
        print(f"[tapsay] 設定檔讀取失敗，改用預設值: {exc}", file=sys.stderr)
        return cfg
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            cfg[key].update(value)
        else:
            cfg[key] = value
    return cfg


def save(cfg: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(cfg, f)


def get_api_key(kind: str) -> str:
    """kind: 'stt' 或 'llm'。金鑰存在 macOS Keychain / Windows 認證管理員。"""
    try:
        return keyring.get_password(KEYRING_SERVICE, kind) or ""
    except Exception as exc:  # 沒有可用的 keyring backend
        print(f"[tapsay] 讀取 API key 失敗: {exc}", file=sys.stderr)
        return ""


def set_api_key(kind: str, value: str) -> None:
    if value:
        keyring.set_password(KEYRING_SERVICE, kind, value)
    else:
        try:
            keyring.delete_password(KEYRING_SERVICE, kind)
        except Exception:
            pass
