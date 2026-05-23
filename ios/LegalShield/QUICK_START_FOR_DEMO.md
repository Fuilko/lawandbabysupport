---
title: "LegalShield iOS — 5 分快速演示部署指南"
author: "劉 建志"
date: "2026 年 5 月 24 日"
---

# LegalShield iOS — 5 分鐘快速部署（演示用）

> 鈴木教授面談 / 任何展示場合用。**從零到 iPhone Simulator 跑起來只需 5 分鐘。**

---

## 0. 前提條件

- macOS（推薦 macOS 14 Sonoma 以上）
- Xcode 15 以上（從 App Store 安裝）
- Homebrew（從 https://brew.sh 安裝）

---

## 1. 從 GitHub 取得最新版本

```bash
cd ~/Desktop   # 或任何您喜歡的位置
git clone https://github.com/Fuilko/lawandbabysupport.git
cd lawandbabysupport
```

> ⚠ 注意：repo 名稱是 `lawandbabysupport`，不是 `LegalShield`。

---

## 2. 安裝 XcodeGen（首次需要，約 30 秒）

```bash
brew install xcodegen
```

---

## 3. 產生 Xcode 專案

```bash
cd ios/LegalShield
xcodegen generate
```

成功時會出現：
```
Loaded project:
  Name: LegalShield
  Targets: 2
  Schemes: 0
Generated project successfully
```

並產生 `LegalShield.xcodeproj`。

---

## 4. 開啟 Xcode 並執行

```bash
open LegalShield.xcodeproj
```

在 Xcode 內：
1. 左上角選擇 **Scheme：LegalShield**
2. 旁邊選擇 **iPhone 15 Pro Simulator**（或任何 iOS 17+ 模擬器）
3. 按 **⌘R**（Cmd + R）執行

首次編譯約 30~60 秒，之後 Simulator 會自動啟動 LegalShield app。

---

## 5. 演示功能巡禮（推薦順序）

| 順序 | 功能 | 操作 |
|---|---|---|
| ① | **Evidence Vault** | 點主畫面「証拠保管庫」→ 拍一張照片 → 觀察 SHA-256 立即生成 |
| ② | **防誘導取證 Copilot** | 點「取調支援」→ 按 🎤 錄音 → 模擬被問問題 → 觀察 AI 即時提示「該問題可能違法」 |
| ③ | **Anomaly Detection** | 點「異常監視」→ 觀察心率、位置 mock 資料 → 模擬壓力升高 |
| ④ | **法律文書生成** | 點「書類起案」→ 選「準備書面」→ 觀察自動填入 Mapry 案件範本 |
| ⑤ | **Audit Log** | 點「監査ログ」→ 觀察所有上述操作以 hash chain 形式記錄 |

---

## 6. 給審查者的「亮點」說明

**技術亮點**
- ✅ 純 SwiftUI 原生實作，無第三方框架（除標準 iOS SDK）
- ✅ 證據鏈使用 SHA-256 + 時間戳 + GPS 三重綁定
- ✅ AI 採 **on-device 優先**（隱私保護）
- ✅ 全部 OSS（MIT License）

**社會價值亮點**
- ✅ 弁護士費用ゼロで本人訴訟が可能
- ✅ DV/ストーキング/フリーランス被害者全員対応
- ✅ 外国籍研究者・地方在住者も使いやすい多言語 UI
- ✅ 既に **Mapry 仲裁手続**（第二東京弁護士会）で実証実験中

**研究亮点**
- ✅ CALL4 76 件 + 裁判所書式 166 件 = 3,837 chunks RAG 語料庫
- ✅ 多言語 sentence-embedding + LanceDB vector search
- ✅ 民法・民訴・消費者契約法・労動審判の自動論述支援

---

## 7. 故障排除

| 問題 | 解決 |
|---|---|
| `xcodegen: command not found` | `brew install xcodegen` 再試 |
| Xcode 編譯錯誤「No such module 'X'」| Xcode → Product → Clean Build Folder → 再 ⌘R |
| Simulator 無法啟動 | Xcode → Window → Devices and Simulators → 重新建立 |
| Git clone 失敗 | 確認網路、確認 GitHub 帳號權限 |

---

## 8. 進階：拉最新 RAG 後端

```bash
# 從 repo 根目錄
cd ~/Desktop/lawandbabysupport
python -m pip install -r requirements.txt  # 如果有
python -m legalshield.crawlers.litigation_docs.call4_scraper  # 爬 CALL4 (~4 分鐘)
python -m legalshield.crawlers.litigation_docs.courts_jp_forms priority  # 下載書式 (~5 分鐘)
python -m legalshield.crawlers.litigation_docs.extract_text  # 抽文本
python -m legalshield.crawlers.litigation_docs.vectorize  # 向量化
python -m legalshield.backend.litigation_rag "答弁書 書き方"  # 測試 RAG
```

---

**作成日**：2026 年 5 月 24 日
**作成者**：劉 建志（kenji@hiiforest.com）
**GitHub**：https://github.com/Fuilko/lawandbabysupport
