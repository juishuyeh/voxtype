# VoxType

按一下快捷鍵、說話、再按一下 —— 幾秒後整理好的台灣繁體中文直接出現在游標位置。

```
Hotkey → 錄音 → STT → LLM 整理 → 剪貼簿 → 自動貼上
```

常駐背景，只有一個 menu bar / tray 圖示，沒有主視窗。

## 下載

[**Releases**](https://github.com/juishuyeh/voxtype/releases/latest) 有打包好的版本，不需要裝 Python：

| 平台 | 檔案 | 第一次打開 |
|---|---|---|
| macOS (Apple Silicon) | `VoxType-macOS-arm64.zip` | 解壓縮 → 拖進「應用程式」→ 右鍵「打開」 |
| Windows (x64) | `VoxType-Windows-x64.zip` | 解壓縮 → 執行 `VoxType.exe` → SmartScreen 選「仍要執行」 |

兩邊都沒有付費簽章，所以第一次要手動放行一次，之後正常。macOS 還要到
「系統設定 → 隱私權與安全性」開**麥克風**與**輔助使用**給 VoxType。

## 從原始碼執行

需要 Python 3.14（`uv` 會自動處理）。

```bash
uv sync
uv run voxtype            # 常駐執行，出現 menu bar / tray 圖示
uv run voxtype --settings # 只開設定視窗
uv run voxtype --no-tray  # 不顯示圖示，只註冊快捷鍵（除錯用）
```

第一次執行請先開設定視窗填 STT / LLM 的 Endpoint、API Key、Model。

## 使用

1. 游標停在任何可輸入文字的地方
2. 按 `Ctrl+Alt+Space`（預設）→ menu bar 圖示變**紅色**，開始錄音
3. 說話
4. 再按一次 `Ctrl+Alt+Space` → 圖示變**黃色**，處理中
5. 圖示變**綠色**→ 文字已寫入剪貼簿並自動貼到游標位置

失敗時會跳一則系統通知，而且**文字一定已經在剪貼簿裡**，可以自己 `Cmd+V` / `Ctrl+V`。

圖示顏色：灰＝待命、紅＝錄音、黃＝處理中、綠＝完成、紅＝錯誤。

## 設定

Menu bar 圖示 →「設定…」，或 `uv run voxtype --settings`。

| 項目 | 說明 |
|---|---|
| 全域快捷鍵 | pynput 格式，例如 `<ctrl>+<alt>+<space>`、`<cmd>+<shift>+r` |
| STT Endpoint / Key / Model | OpenAI 相容的 `/audio/transcriptions` |
| LLM Endpoint / Key / Model | OpenAI 相容的 `/chat/completions` |
| LLM Prompt | 可自由編輯，預設是「整理成台灣繁體中文」 |

API Key 欄位開啟時一律是空的，**留白代表沿用已儲存的金鑰**，只有真的輸入新值才會覆寫。
（設定視窗因此完全不讀 Keychain，才不會一點「設定」就先跳出要求鑰匙圈密碼的對話框。）

「測試連線 / 取得模型」會打 `GET {endpoint}/models`：成功就把模型填進下拉選單，
Endpoint 不支援模型清單時，Model 欄位照樣可以直接手動輸入。

Endpoint 填 base URL（例如 `https://api.openai.com/v1`），程式自己接 `/audio/transcriptions`、
`/chat/completions`、`/models`；填完整網址也可以。本機 LiteLLM proxy 就填 `http://localhost:4000/v1`。

**設定檔位置**

- macOS：`~/Library/Application Support/VoxType/config.toml`
- Windows：`%APPDATA%\VoxType\config.toml`

API Key **不寫進 config.toml**，存在 macOS Keychain / Windows 認證管理員（service 名稱 `voxtype`）。

## 系統權限

**macOS**（權限是掛在「啟動它的那個程式」上，所以固定用同一個終端機 / 同一種啟動方式）

- 系統設定 → 隱私權與安全性 → **麥克風**：允許你的終端機
- 系統設定 → 隱私權與安全性 → **輔助使用**：允許你的終端機（全域快捷鍵與自動貼上都需要）
- 第一次跳通知權限時允許（通知走 osascript）

**Windows**

- 不需要特別權限；防毒軟體偶爾會對鍵盤 hook 有意見
- 想避免黑色主控台視窗，用 `pythonw.exe -m voxtype` 啟動

## 技術選型

| 需求 | 選擇 | 理由 |
|---|---|---|
| 全域快捷鍵 + 自動貼上 | `pynput` | 一個套件同時解決兩件事，Win/mac 都支援；`GlobalHotKeys` 會忽略程式合成的按鍵，所以自動貼上的 Cmd+V 不會誤觸自己 |
| 錄音 | `sounddevice` | PortAudio 綁定，wheel 自帶二進位；用 `RawInputStream` 直接拿 int16 bytes，**不需要 numpy** |
| Tray / Menu Bar | `pystray` | 跨平台、純 Python；同時提供原生通知（macOS 走 osascript、Windows 走 balloon） |
| 剪貼簿 | `pyperclip` | 極小，Win/mac 原生實作，中文沒問題 |
| API Key | `keyring` | 直接接 macOS Keychain / Windows Credential Manager |
| HTTP | **標準函式庫 `urllib`** | 只需要一個 multipart 上傳和一個 JSON POST，實測 TLS 正常，不值得為此加 `requests` |
| 設定檔 | `tomllib`（讀，內建）+ `tomli-w`（寫） | 需求指定 TOML；tomli-w 沒有其他相依 |
| 設定 GUI | `tkinter` | Python 內建，設定畫面夠用 |
| 音訊暫存 | `io.BytesIO` + `wave`（內建） | 錄音只存在記憶體，送出後即消失，不落地 |

執行期相依只有 7 個直接套件（macOS 上 pynput 會帶 pyobjc）。

**兩個關鍵設計決定**

1. **設定視窗用獨立子行程開**（`python -m voxtype.ui`）。macOS 的 menu bar（NSApplication）和
   tkinter 都要求主執行緒，硬塞在同一個行程裡會打架；開子行程只花 0.3 秒，關掉後主程式重讀設定。
2. **剪貼簿是保底**。永遠先寫剪貼簿再送 Cmd+V，自動貼上失敗只是少了一步，結果不會遺失。

## 已在 macOS 實測通過

- 完整 E2E（錄音 → STT → LLM → 剪貼簿 → 自動貼進 TextEdit），處理約 4.6 秒（其中 LLM 佔大部分）
- STT 輸出簡體 `今天天气不错。那个，...` → LLM 整理成 `今天天氣不錯。我們等一下開會討論專案進度。`
- 錯誤路徑：連線被拒、HTTP 401/403、Model 沒設、沒錄到聲音 —— 都只跳通知並回到待命，不會讓程式掛掉
- Menu bar 圖示與狀態換色、設定視窗、設定檔 TOML round-trip

尚未在 Windows 上實機驗證（沒有 Windows 環境）；所有相依套件都有官方 Windows 支援。

## 打包成 .app / .exe

```bash
uv sync
uv run pyinstaller voxtype.spec --noconfirm
```

- macOS → `dist/VoxType.app`（實測 48 MB，建置約 10 秒，menu bar 圖示正常）
- Windows → `dist/VoxType/VoxType.exe`（`console=False`，不會有黑色主控台視窗）

`voxtype.spec` 裡兩個平台共用一份設定，重點只有三處：

- `LSUIElement: True` —— 只待在 menu bar，不佔 Dock
- `NSMicrophoneUsageDescription` —— **沒有這行 macOS 會直接不給麥克風**
- `hiddenimports` —— `pystray` 與 `keyring` 的後端是動態載入的，不寫會在執行期才炸

## 發佈到 GitHub Release

`.github/workflows/release.yml` 已經備好：推一個 tag 就自動在 macOS 與 Windows runner 上各打一包，
建立 Release 並附上兩個 zip。

```bash
git tag v0.1.0 && git push origin v0.1.0
```

macOS 的 zip 用 `ditto` 壓（`zip` 會破壞 .app 的簽章與符號連結）。

## 給下載的人：第一次打開

兩邊都是**沒有付費簽章**的程式，系統會擋一次：

- **macOS**：右鍵 →「打開」→「打開」，或 `xattr -dr com.apple.quarantine /Applications/VoxType.app`
- **Windows**：SmartScreen →「其他資訊」→「仍要執行」

想要免掉這個步驟，就得走付費路線：

- macOS：Apple Developer Program（US$99/年）→ `codesign --sign "Developer ID Application: ..."` → `xcrun notarytool submit`
- Windows：買一張程式碼簽章憑證（OV 一年約 US$200 起，EV 才能立刻免除 SmartScreen）

## 打包版的兩個 macOS 注意事項

1. **權限是綁在簽章上的。** PyInstaller 預設用 ad-hoc 簽章，每次重新打包簽章都會變，
   所以「輔助使用」要重新勾選、Keychain 會再問一次「VoxType 想使用您鑰匙圈中儲存的機密資訊」
   （按「永遠允許」）。用固定的 Developer ID 簽章就不會每次重來。
2. 打包後 `sys.executable` 就是 VoxType 自己，不是 python，所以設定視窗改用
   `VoxType --settings` 開子行程（`tray.py:46`）；跑原始碼時仍走 `python -m voxtype.ui`。

## 專案結構

```
src/voxtype/
├── __init__.py   進入點與命令列參數
├── app.py        狀態機與主流程
├── recorder.py   麥克風 → WAV bytes
├── api.py        STT / LLM HTTP（urllib）
├── paste.py      剪貼簿與自動貼上
├── hotkey.py     全域快捷鍵
├── notify.py     系統通知
├── tray.py       menu bar / tray 圖示
├── ui.py         設定視窗（tkinter）
└── config.py     config.toml + keyring
```

## 疑難排解

**打包版點「設定」沒反應** —— v0.1.0 的 macOS 版有這個 bug（CI 用到不含 tkinter 的 Homebrew Python，
設定視窗一開就死在 `tk.Tk()`，而且 `console=False` 讓錯誤無處可見）。v0.1.1 已修：CI 改用 uv 自己的
CPython、打包時直接 `import tkinter` 驗證、產物再檢查一次 `_tkinter` 是否存在，子行程失敗也會跳通知。

**第一次錄音時跳出鑰匙圈密碼對話框** —— 正常。因為 ad-hoc 簽章的 VoxType 和當初寫入金鑰的程式
不是同一個身分，輸入登入密碼並按**「永遠允許」**一次即可。每次改版重新打包會再問一次。

## 已知限制

- 快捷鍵不會被攔截（不 suppress），按下時前景程式也會收到；請避開前景程式有作用的組合。
  macOS 的 `Cmd+Alt+Space` 是 Finder 搜尋，所以預設用 `Ctrl+Alt+Space`。
- 沒有歷史紀錄、不保存錄音、沒有 Prompt 範本管理 —— 這些是刻意不做的。
