"""VoxType — 按一下、說話、再按一下，整理好的文字出現在游標位置。"""

from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(
            "用法：voxtype [--settings | --no-tray]\n"
            "  （無參數）  常駐執行，顯示 tray / menu bar 圖示\n"
            "  --settings  只開啟設定視窗\n"
            "  --no-tray   不顯示圖示，只註冊快捷鍵（除錯用）"
        )
        return
    if args and args[0] == "--settings":
        from .ui import run as run_settings

        run_settings()
        return
    if args and args[0] == "--no-tray":
        from .app import VoxType

        app = VoxType()
        app.start_hotkey()
        print(f"[voxtype] 已啟動（無 tray），快捷鍵 {app.config.get('hotkey')}，Ctrl+C 結束")
        try:
            import threading

            threading.Event().wait()
        except KeyboardInterrupt:
            app.recorder.cancel()
        return

    from .tray import run as run_tray

    run_tray()
