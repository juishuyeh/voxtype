"""剪貼簿與自動貼上。順序永遠是先寫剪貼簿，再嘗試貼上。"""

from __future__ import annotations

import sys
import time

import pyperclip
from pynput.keyboard import Controller, Key

_keyboard = Controller()


def copy(text: str) -> None:
    try:
        pyperclip.copy(text)
    except Exception as exc:
        raise RuntimeError(f"寫入剪貼簿失敗：{exc}") from exc


def paste() -> None:
    """對目前游標位置送出 Cmd+V / Ctrl+V。"""
    modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl
    time.sleep(0.05)  # 等剪貼簿內容就緒
    try:
        with _keyboard.pressed(modifier):
            _keyboard.press("v")
            _keyboard.release("v")
    except Exception as exc:  # macOS 未授權輔助使用時會失敗
        raise RuntimeError(f"自動貼上失敗：{exc}") from exc
