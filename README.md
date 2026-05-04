# Law & Baby Support

**數位賦權 (Digital Empowerment)** — AI 驅動的法律自救 + 婦幼醫療輔助平台

## 兩個產品

| App | 說明 | 對象 |
|-----|------|------|
| **LegalShield (法盾)** | 法律自救：證據保全 → 策略模擬 → 文書生成 → 律師轉介 | 本人訴訟者、被害者 |
| **PocketMidwife (口袋助產士)** | 婦幼醫療：症狀問卷 → Edge AI 檢傷 → Triage → 急診轉介 | 偏鄉父母、孕產婦 |

## 技術核心

- **存證引擎** — SHA256 + NTP 時間戳 + Audit Log
- **RAG 檢索** — 法規判例 / 醫學指引，強制引用出處
- **SLM/LLM 路由** — 隱私優先 (本地 SLM)，超限接雲端 LLM，高風險轉人工

## 免責設計

- App = 輔助工具，非法律代理 / 非醫療診斷
- 所有建議強制附帶法源或醫學指南出處
- 敏感資料優先本地處理，伺服器不持有原始資料

## 目錄結構

```
lawandbabysupport/
├── README.md
├── PRODUCT_PLAN.md          ← 完整產品規劃
├── shared/                  ← 共用底座 (存證 + RAG + Router)
├── legalshield/             ← 法律自救 App
│   ├── backend/
│   ├── frontend/
│   ├── knowledge/
│   └── agents/
├── pocketmidwife/           ← 婦幼醫療 App
│   ├── backend/
│   ├── ios/
│   ├── knowledge/
│   └── models/
└── tests/
```

## 狀態

🟡 規劃中 — 詳見 [PRODUCT_PLAN.md](./PRODUCT_PLAN.md)

## License

Private — All rights reserved.
