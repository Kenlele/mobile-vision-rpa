# 📱 Mobile Vision RPA (極簡 iOS AI 自動化測試與 RPA 系統)

> 🚀 **用自然語言指令直接操控 iOS 裝置！** 結合雲端 **Gemini Vision AI (Gemini 2.5 Flash)**、Swift 本地 OCR 與 **Skill 自主學習引擎** 的極簡高效 iOS 自動化測試與 RPA 框架。

---

## ✨ 專案亮點 (Features)

* 🧠 **自然語言 AI 視覺驅動**：不需要寫死 XPath 或座標，直接輸入「幫我打開相簿」、「點擊第一個商品」即可完成自動化操作。
* ⚡ **極輕量與秒級響應**：採用 Google **Gemini 2.5 Flash** 視覺模型，零本機記憶體與 GPU 負擔，推論響應時間 < 0.5 秒。
* 🚀 **Skill 自主學習與 Persistence 引擎**：
  * **首跑探索**：由 Vision AI 自動尋找按鈕並完成操作。
  * **自動儲存**：成功後自動於 `skills/` 生成結構化 `SKILL.md` 腳本。
  * **二次執行零成本**：再次執行相同任務時直接復用 Skill 腳本，**省去 95% API 費用與等待時間**！
* 📱 **雙驅動模式 (Dual Drivers)**：
  * **Xcode iOS Simulator (`--driver ios`)**：適合開發者與 CI/CD 測試，背景執行不佔用桌面滑鼠焦點。
  * **macOS iPhone 鏡像 (`--driver iphone_mirror`)**：支援實體 iPhone 畫面同步與真實裝置操控。
* 🔍 **Swift 本地 Vision OCR + Visual Delta 斷言**：毫秒級文字定位與畫面轉場驗證，確保每一次點擊都真正觸發了 UI 變更。

---

## ⚡ 3 步驟快速開始 (Quick Start)

### 步驟 1：下載專案與安裝環境

```bash
git clone https://github.com/Kenlele/mobile-vision-rpa.git
cd mobile-vision-rpa

# 建立並啟用虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝必要套件
pip install -r requirements.txt
```

---

### 步驟 2：設定 Gemini API Key (建立 `config.ini`)

將預設範本複製一份為 `config.ini`：

```bash
cp config.ini.template config.ini
```

編輯 `config.ini`，貼上您的 Gemini API Key：

```ini
[LLM]
gemini_api_key = 貼上您的_Gemini_API_Key_在此處
model_name = gemini-2.5-flash

[DRIVER]
# 預設使用 Xcode iOS 模擬器 (欲使用實機鏡像請改為 iphone_mirror)
driver_type = ios
udid = booted
```

> 💡 **環境變數提示**：您也可以直接在 Terminal 設定 `export GEMINI_API_KEY="您的Key"`，無需寫入檔案。

---

### 步驟 3：開始執行自動化任務！

#### 方式 A：單行指令指定任務
```bash
python main.py --prompt "幫我打開相簿"
```

#### 方式 B：互動式對話模式 (持續接受 Prompt 指令)
```bash
python main.py
```
進入互動模式後，系統會維持與 iOS 裝置的連線，您可以連續下達多個指令：
```
👉 請輸入 Prompt 指示: 幫我打開設定
👉 請輸入下一個 Prompt 指示: 幫我點擊 Wi-Fi
👉 請輸入下一個 Prompt 指示: 結束
```

---

## 🛠️ 常用驅動切換

### 使用 macOS iPhone 鏡像操控「實體 iPhone」
若您的 Mac 已升級至 macOS Sequoia，且開啟了「iPhone 鏡像」App：
```bash
python main.py --driver iphone_mirror --prompt "幫我打開相簿"
```

---

## 📂 專案架構說明

```
mobile-vision-rpa/
├── config.ini.template      # 全域設定檔範本 (勿將真實 API Key 提交至 Git)
├── main.py                  # CLI 互動式程式入口
├── core/
│   ├── agent.py             # RPA 核心調度心臟 (Vision 決策 -> Action -> 斷言)
│   ├── runner.py            # 框架測試組裝與執行報告生成器
│   └── skill_manager.py     # Skill 自主學習與 Markdown Persistent 引擎
├── drivers/
│   ├── base_driver.py       # 驅動器抽象介面 (Base class)
│   ├── ios_driver.py        # Xcode iOS 模擬器控制器 (xcrun simctl)
│   └── iphone_mirror_driver.py # macOS iPhone 鏡像實體機控制器
├── vision/
│   ├── apple_vision_ocr.swift # Swift 原生 Apple Vision OCR 源碼
│   ├── ocr_engine.py        # 本地 OCR 識別封裝
│   └── screen_verifier.py   # 畫面轉場 Visual Delta 驗證器
├── ai/
│   ├── llm_planner.py       # Gemini Vision 視覺分析器
│   └── prompts.py           # Pure Vision System Prompts
└── skills/                  # 自動學習生成之 SKILL.md Persistent 知識庫
```

---

## 🔒 隱私與安全說明 (Security & Privacy)

* `config.ini` 已自動納入 `.gitignore`，確保您的私人 API Key 絕對不會意外推送到 GitHub 上。
* 建議在團隊協作時，透過 `export GEMINI_API_KEY="..."` 帶入金鑰。

---

## 📄 授權條款 (License)

本專案基於 [MIT License](LICENSE) 開源。歡迎 Star 🌟 與提交 PR 共同完善 iOS AI Vision RPA 生態系！
