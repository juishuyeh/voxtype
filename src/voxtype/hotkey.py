"""全域快捷鍵（pynput）。

兩種格式：
    <ctrl>+<alt>+<space>   一般組合鍵（pynput 格式）
    double:<ctrl>          連擊兩下修飾鍵（ctrl / cmd / alt / shift）
"""

from __future__ import annotations

import subprocess
import sys
import time

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


DOUBLE_PREFIX = "double:"
DEFAULT_DOUBLE_TAP_MS = 400


def _modifier_keys(name: str) -> set:
    """把 ctrl 這種名字展開成左右鍵都算（Key.ctrl / ctrl_l / ctrl_r）。"""
    keys = set()
    for suffix in ("", "_l", "_r", "_gr"):
        key = getattr(keyboard.Key, name + suffix, None)
        if key is not None:
            keys.add(key)
    if not keys:
        raise ValueError(f"不認得的修飾鍵：{name}")
    return keys


def _parse_double(combo: str) -> str:
    """'double:<ctrl>' -> 'ctrl'；格式不對就丟 ValueError。"""
    name = combo[len(DOUBLE_PREFIX) :].strip().strip("<>").lower()
    if name not in ("ctrl", "cmd", "alt", "shift"):
        raise ValueError(f"連擊只支援 ctrl / cmd / alt / shift，收到：{name or '(空白)'}")
    return name


def validate(combo: str) -> None:
    """格式不對就丟 ValueError。"""
    combo = (combo or "").strip()
    if combo.startswith(DOUBLE_PREFIX):
        _modifier_keys(_parse_double(combo))
        return
    keyboard.HotKey.parse(combo)


def create_listener(combo: str, callback, double_tap_ms: int = DEFAULT_DOUBLE_TAP_MS):
    """依快捷鍵字串決定要用組合鍵還是連擊監聽器。"""
    combo = (combo or "").strip()
    if combo.startswith(DOUBLE_PREFIX):
        return DoubleTapListener(combo, callback, double_tap_ms)
    return HotkeyListener(combo, callback)


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


class DoubleTapListener:
    """連擊兩下同一個修飾鍵就觸發，例如連按兩下 Ctrl。

    規則刻意保守，避免誤觸：兩次按下之間如果夾了別的鍵（Ctrl+C 那種）就不算，
    程式自己送出的按鍵（injected，例如自動貼上的 Ctrl+V）也不算。
    """

    def __init__(self, combo: str, callback, double_tap_ms: int = DEFAULT_DOUBLE_TAP_MS) -> None:
        self.combo = combo
        self.name = _parse_double(combo)
        self._keys = _modifier_keys(self.name)
        self._callback = callback
        self._interval = max(double_tap_ms, 100) / 1000
        self._listener: keyboard.Listener | None = None
        self._last_press: float | None = None
        self._other_key_since = False

    def _on_press(self, key, injected=False) -> None:
        if injected:
            return
        if key not in self._keys:
            # 夾了別的鍵，這輪不算連擊
            self._other_key_since = True
            self._last_press = None
            return
        now = time.monotonic()
        if (
            self._last_press is not None
            and not self._other_key_since
            and now - self._last_press <= self._interval
        ):
            self._last_press = None
            self._callback()
        else:
            self._last_press = now
            self._other_key_since = False

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
