"""全域快捷鍵（pynput）。快捷鍵字串格式即 pynput 格式，例如 <ctrl>+<alt>+space。"""

from __future__ import annotations

import subprocess
import sys

from pynput import keyboard

ACCESSIBILITY_PANE = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)


def is_trusted() -> bool:
    """macOS：本行程有沒有「輔助使用」權限。沒有的話 pynput 只會靜靜地收不到任何按鍵。"""
    if sys.platform != "darwin":
        return True
    try:
        from ApplicationServices import AXIsProcessTrusted

        return bool(AXIsProcessTrusted())
    except Exception:
        return True  # 查不出來就不要擋住流程


def request_trust() -> None:
    """跳出系統授權對話框，並開啟「隱私權與安全性 → 輔助使用」設定頁。"""
    if sys.platform != "darwin":
        return
    try:
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )

        AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
    except Exception:
        pass
    try:
        subprocess.Popen(["open", ACCESSIBILITY_PANE])
    except Exception:
        pass


def validate(combo: str) -> None:
    """格式不對就丟 ValueError。"""
    keyboard.HotKey.parse(combo)


class HotkeyListener:
    def __init__(self, combo: str, callback) -> None:
        validate(combo)
        self.combo = combo
        self._callback = callback
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        self._listener = keyboard.GlobalHotKeys({self.combo: self._callback})
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
