"""全域快捷鍵（pynput）。快捷鍵字串格式即 pynput 格式，例如 <ctrl>+<alt>+space。"""

from __future__ import annotations

from pynput import keyboard


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
