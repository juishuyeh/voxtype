"""設定視窗（tkinter）。獨立行程執行：python -m tapsay.ui"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import api, config, hotkey

PAD = {"padx": 8, "pady": 4}


class SettingsWindow:
    def __init__(self) -> None:
        self.cfg = config.load()
        self.root = tk.Tk()
        self.root.title("TapSay 設定")
        self.root.minsize(560, 640)

        self.vars = {
            "hotkey": tk.StringVar(value=self.cfg.get("hotkey", "")),
            "auto_paste": tk.BooleanVar(value=bool(self.cfg.get("auto_paste", True))),
            "ca_bundle": tk.StringVar(value=self.cfg.get("ca_bundle", "")),
            "insecure_ssl": tk.BooleanVar(value=bool(self.cfg.get("insecure_ssl", False))),
            "stt_endpoint": tk.StringVar(value=self.cfg["stt"].get("endpoint", "")),
            "stt_key": tk.StringVar(),
            "stt_model": tk.StringVar(value=self.cfg["stt"].get("model", "")),
            "llm_endpoint": tk.StringVar(value=self.cfg["llm"].get("endpoint", "")),
            "llm_key": tk.StringVar(),
            "llm_model": tk.StringVar(value=self.cfg["llm"].get("model", "")),
        }
        self.status = tk.StringVar(value=f"設定檔：{config.config_path()}")

        self._build()

    # ---- 版面 ----

    def _build(self) -> None:
        root = self.root
        root.columnconfigure(0, weight=1)

        general = ttk.LabelFrame(root, text="一般")
        general.grid(row=0, column=0, sticky="ew", **PAD)
        general.columnconfigure(1, weight=1)
        ttk.Label(general, text="全域快捷鍵").grid(row=0, column=0, sticky="w", **PAD)
        ttk.Combobox(
            general,
            textvariable=self.vars["hotkey"],
            values=[
                "<ctrl>+<alt>+<space>",
                "<cmd>+<shift>+<space>",
                "double:<ctrl>",
                "double:<cmd>",
            ],
        ).grid(row=0, column=1, sticky="ew", **PAD)
        ttk.Label(
            general,
            text="組合鍵：<ctrl>+<alt>+<space>　／　連擊兩下：double:<ctrl>（可用 ctrl cmd alt shift）",
            foreground="#777",
        ).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Checkbutton(
            general, text="自動貼到游標位置（關閉則只複製到剪貼簿）", variable=self.vars["auto_paste"]
        ).grid(row=2, column=1, sticky="w", **PAD)
        ttk.Label(general, text="公司 CA 憑證").grid(row=3, column=0, sticky="w", **PAD)
        ca_row = ttk.Frame(general)
        ca_row.grid(row=3, column=1, sticky="ew", **PAD)
        ca_row.columnconfigure(0, weight=1)
        ttk.Entry(ca_row, textvariable=self.vars["ca_bundle"]).grid(row=0, column=0, sticky="ew")
        ttk.Button(ca_row, text="瀏覽…", command=self._pick_ca).grid(row=0, column=1, padx=(4, 0))
        ttk.Button(ca_row, text="清除", command=lambda: self.vars["ca_bundle"].set("")).grid(
            row=0, column=2, padx=(4, 0)
        )
        ttk.Label(
            general,
            text="受限網路（公司 MITM proxy / 自簽憑證）才需要；系統原有的信任清單仍然有效",
            foreground="#777",
        ).grid(row=4, column=1, sticky="w", padx=8)
        ttk.Checkbutton(
            general,
            text="關閉 TLS 憑證驗證（最後手段）",
            variable=self.vars["insecure_ssl"],
        ).grid(row=5, column=1, sticky="w", **PAD)
        ttk.Label(
            general,
            text="完全不檢查憑證，連線可被中間人竊聽；能用上面的 CA 憑證就不要勾這個",
            foreground="#a00",
        ).grid(row=6, column=1, sticky="w", padx=8)

        self._api_frame(root, 1, "STT（語音轉文字）", "stt")
        self._api_frame(root, 2, "LLM（文字整理）", "llm")

        prompt_frame = ttk.LabelFrame(root, text="LLM Prompt")
        prompt_frame.grid(row=3, column=0, sticky="nsew", **PAD)
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)
        self.prompt = tk.Text(prompt_frame, height=10, wrap="word", undo=True)
        self.prompt.grid(row=0, column=0, sticky="nsew", **PAD)
        self.prompt.insert("1.0", self.cfg["llm"].get("prompt", ""))
        ttk.Button(prompt_frame, text="回復預設 Prompt", command=self._reset_prompt).grid(
            row=1, column=0, sticky="w", **PAD
        )

        bottom = ttk.Frame(root)
        bottom.grid(row=4, column=0, sticky="ew", **PAD)
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.status, foreground="#777").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(bottom, text="取消", command=self.root.destroy).grid(row=0, column=1, padx=4)
        ttk.Button(bottom, text="儲存並關閉", command=self._save).grid(row=0, column=2, padx=4)

    def _api_frame(self, root: tk.Misc, row: int, title: str, kind: str) -> None:
        frame = ttk.LabelFrame(root, text=title)
        frame.grid(row=row, column=0, sticky="ew", **PAD)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Endpoint").grid(row=0, column=0, sticky="w", **PAD)
        ttk.Entry(frame, textvariable=self.vars[f"{kind}_endpoint"]).grid(
            row=0, column=1, columnspan=2, sticky="ew", **PAD
        )
        ttk.Label(frame, text="API Key").grid(row=1, column=0, sticky="w", **PAD)
        ttk.Entry(frame, textvariable=self.vars[f"{kind}_key"], show="•").grid(
            row=1, column=1, sticky="ew", **PAD
        )
        ttk.Label(frame, text="留白＝沿用已儲存的金鑰", foreground="#777").grid(
            row=1, column=2, sticky="w", **PAD
        )
        ttk.Label(frame, text="Model").grid(row=2, column=0, sticky="w", **PAD)
        combo = ttk.Combobox(frame, textvariable=self.vars[f"{kind}_model"])
        combo.grid(row=2, column=1, sticky="ew", **PAD)
        ttk.Button(
            frame, text="測試連線 / 取得模型", command=lambda: self._fetch_models(kind, combo)
        ).grid(row=2, column=2, **PAD)

    # ---- 行為 ----

    def _pick_ca(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="選擇 CA 憑證（PEM）",
            filetypes=[("憑證", "*.pem *.crt *.cer *.ca-bundle"), ("所有檔案", "*.*")],
        )
        if path:
            self.vars["ca_bundle"].set(path)

    def _reset_prompt(self) -> None:
        self.prompt.delete("1.0", "end")
        self.prompt.insert("1.0", config.DEFAULT_PROMPT)

    def _fetch_models(self, kind: str, combo: ttk.Combobox) -> None:
        endpoint = self.vars[f"{kind}_endpoint"].get()
        key = self.vars[f"{kind}_key"].get() or config.get_api_key(kind)
        # 測試連線用當下的 TLS 設定，不必先存檔
        api.set_ca_bundle(self.vars["ca_bundle"].get())
        api.set_insecure_ssl(self.vars["insecure_ssl"].get())
        self.status.set(f"連線中：{endpoint} …")

        def work() -> None:
            try:
                models = api.list_models(endpoint, key)
            except Exception as exc:
                self.root.after(0, lambda: self.status.set(f"{kind.upper()} 連線失敗：{exc}"))
                return

            def done() -> None:
                combo["values"] = models
                self.status.set(f"{kind.upper()} 連線成功，取得 {len(models)} 個模型")

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _save(self) -> None:
        combo_hotkey = self.vars["hotkey"].get().strip()
        try:
            hotkey.validate(combo_hotkey)
        except Exception:
            messagebox.showerror("快捷鍵格式錯誤", "例如：<ctrl>+<alt>+<space>")
            return

        ca = self.vars["ca_bundle"].get().strip()
        try:
            api.check_ca_bundle(ca)
        except api.ApiError as exc:
            messagebox.showerror("CA 憑證無法使用", str(exc))
            return

        self.cfg["hotkey"] = combo_hotkey
        self.cfg["auto_paste"] = bool(self.vars["auto_paste"].get())
        self.cfg["ca_bundle"] = ca
        self.cfg["insecure_ssl"] = bool(self.vars["insecure_ssl"].get())
        self.cfg["stt"]["endpoint"] = self.vars["stt_endpoint"].get().strip()
        self.cfg["stt"]["model"] = self.vars["stt_model"].get().strip()
        self.cfg["llm"]["endpoint"] = self.vars["llm_endpoint"].get().strip()
        self.cfg["llm"]["model"] = self.vars["llm_model"].get().strip()
        self.cfg["llm"]["prompt"] = self.prompt.get("1.0", "end").strip()

        try:
            config.save(self.cfg)
            for kind in ("stt", "llm"):
                new_key = self.vars[f"{kind}_key"].get().strip()
                if new_key:  # 留白代表不動已儲存的金鑰
                    config.set_api_key(kind, new_key)
        except Exception as exc:
            messagebox.showerror("儲存失敗", str(exc))
            return
        self.root.destroy()


def _focus(root: tk.Tk) -> None:
    """設定視窗是獨立行程；macOS 上要主動把自己提到前景才拿得到鍵盤焦點。"""
    if sys.platform == "darwin":
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyRegular

            app = NSApplication.sharedApplication()
            app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            app.activateIgnoringOtherApps_(True)
        except Exception:
            pass
    root.lift()
    root.focus_force()


def run() -> None:
    window = SettingsWindow()
    window.root.after(50, lambda: _focus(window.root))
    window.root.mainloop()


if __name__ == "__main__":
    run()
