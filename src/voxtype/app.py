"""核心流程：Hotkey -> Record -> STT -> LLM -> Clipboard -> Paste。"""

from __future__ import annotations

import threading
import time

from . import api, config, notify, paste
from .hotkey import HotkeyListener
from .recorder import Recorder, RecorderError

IDLE = "idle"
RECORDING = "recording"
PROCESSING = "processing"
SUCCESS = "success"
ERROR = "error"


class VoxType:
    def __init__(self) -> None:
        self.config = config.load()
        self.recorder = Recorder()
        self.state = IDLE
        self.on_state = lambda state: None  # 由 tray 覆寫
        self._lock = threading.Lock()
        self._hotkey: HotkeyListener | None = None

    # ---- 狀態 ----

    def _set_state(self, state: str, message: str | None = None) -> None:
        self.state = state
        try:
            self.on_state(state)
        except Exception:
            pass
        if message:
            notify.notify(message)

    def _flash_back_to_idle(self, from_state: str, delay: float) -> None:
        def revert() -> None:
            if self.state == from_state:
                self._set_state(IDLE)

        timer = threading.Timer(delay, revert)
        timer.daemon = True
        timer.start()

    # ---- 快捷鍵 ----

    def start_hotkey(self) -> None:
        combo = self.config.get("hotkey", "")
        try:
            self._hotkey = HotkeyListener(combo, self.toggle)
            self._hotkey.start()
        except Exception as exc:
            self._hotkey = None
            notify.notify(f"快捷鍵 {combo} 無法註冊：{exc}")

    def restart_hotkey(self) -> None:
        if self._hotkey is not None:
            self._hotkey.stop()
            self._hotkey = None
        self.start_hotkey()

    def reload_config(self) -> None:
        old = self.config.get("hotkey")
        self.config = config.load()
        if self.config.get("hotkey") != old:
            self.restart_hotkey()

    # ---- 主流程 ----

    def toggle(self) -> None:
        with self._lock:
            if self.state == PROCESSING:
                return
            if self.recorder.is_recording:
                try:
                    wav = self.recorder.stop()
                except RecorderError as exc:
                    self._set_state(ERROR, str(exc))
                    self._flash_back_to_idle(ERROR, 2.0)
                    return
                self._set_state(PROCESSING)
                worker = threading.Thread(target=self._process, args=(wav,), daemon=True)
                worker.start()
            else:
                try:
                    self.recorder.start()
                except RecorderError as exc:
                    self._set_state(ERROR, str(exc))
                    self._flash_back_to_idle(ERROR, 2.0)
                    return
                self._set_state(RECORDING)

    def _process(self, wav: bytes) -> None:
        started = time.monotonic()
        try:
            text = self._transcribe_and_refine(wav)
        except api.ApiError as exc:
            self._set_state(ERROR, f"處理失敗：{exc}")
            self._flash_back_to_idle(ERROR, 3.0)
            return
        except Exception as exc:  # 任何意外都不該讓常駐程式死掉
            self._set_state(ERROR, f"未預期錯誤：{exc}")
            self._flash_back_to_idle(ERROR, 3.0)
            return

        # 保底：先寫剪貼簿，再嘗試自動貼上
        try:
            paste.copy(text)
        except Exception as exc:
            self._set_state(ERROR, str(exc))
            self._flash_back_to_idle(ERROR, 3.0)
            return

        if self.config.get("auto_paste", True):
            try:
                paste.paste()
            except Exception:
                self._set_state(ERROR, "自動貼上失敗 — 文字已複製到剪貼簿")
                self._flash_back_to_idle(ERROR, 3.0)
                return

        print(f"[voxtype] 完成，耗時 {time.monotonic() - started:.1f}s、{len(text)} 字")
        self._set_state(SUCCESS)
        self._flash_back_to_idle(SUCCESS, 1.2)

    def _transcribe_and_refine(self, wav: bytes) -> str:
        stt = self.config["stt"]
        raw = api.transcribe(stt["endpoint"], config.get_api_key("stt"), stt["model"], wav)
        llm = self.config["llm"]
        return api.refine(
            llm["endpoint"], config.get_api_key("llm"), llm["model"], llm["prompt"], raw
        )
