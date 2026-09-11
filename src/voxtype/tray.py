"""System Tray / macOS Menu Bar 圖示，同時作為狀態指示。"""

from __future__ import annotations

import subprocess
import sys
import threading

import pystray
from PIL import Image, ImageDraw

from . import notify
from .app import ERROR, IDLE, PROCESSING, RECORDING, SUCCESS, VoxType

COLORS = {
    IDLE: (130, 130, 130),
    RECORDING: (225, 60, 60),
    PROCESSING: (235, 170, 40),
    SUCCESS: (70, 180, 90),
    ERROR: (225, 60, 60),
}
LABELS = {
    IDLE: "VoxType — 待命",
    RECORDING: "VoxType — ● 錄音中",
    PROCESSING: "VoxType — 處理中…",
    SUCCESS: "VoxType — 完成",
    ERROR: "VoxType — 錯誤",
}


def _icon_image(color: tuple[int, int, int]) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, size - 10, size - 10), fill=color + (255,))
    return img


_IMAGES = {state: _icon_image(color) for state, color in COLORS.items()}


def open_settings(app: VoxType) -> None:
    """設定視窗用獨立行程開，避免 tkinter 與 menu bar 搶主執行緒。"""

    # 打包成 .app / .exe 之後 sys.executable 就是程式本身，不能用 -m
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--settings"]
    else:
        cmd = [sys.executable, "-m", "voxtype.ui"]

    def run() -> None:
        try:
            subprocess.run(cmd, check=False)
        except Exception as exc:
            notify.notify(f"無法開啟設定視窗：{exc}")
            return
        app.reload_config()

    threading.Thread(target=run, daemon=True).start()


def run() -> None:
    app = VoxType()
    icon = pystray.Icon(
        "voxtype",
        _IMAGES[IDLE],
        LABELS[IDLE],
        menu=pystray.Menu(
            pystray.MenuItem("開始 / 停止錄音", lambda: app.toggle()),
            pystray.MenuItem("設定…", lambda: open_settings(app)),
            pystray.MenuItem("結束 VoxType", lambda: icon.stop()),
        ),
    )

    def on_state(state: str) -> None:
        icon.icon = _IMAGES.get(state, _IMAGES[IDLE])
        icon.title = LABELS.get(state, LABELS[IDLE])

    app.on_state = on_state
    notify.set_notifier(lambda message, title: icon.notify(message, title))

    app.start_hotkey()
    hotkey = app.config.get("hotkey", "")
    print(f"[voxtype] 已啟動，快捷鍵 {hotkey}")
    try:
        icon.run()
    finally:
        app.recorder.cancel()
