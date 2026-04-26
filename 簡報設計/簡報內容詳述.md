# 台股多因子預測系統 v11.5.17 · 簡報內容詳述（供 Claude Design 優化使用）

> **產出目的**：將目前的 34 頁網頁簡報「全部資訊結構」整理成單一 markdown，
> 提供給 Claude Design 作為再設計／再排版的素材；同時保留所有業務指標、設計系統、章節脈絡。
> 本檔不包含「元件化 PPTX」相關的工程細節，只聚焦於**簡報內容本身**。
>
> 來源：`台股多因子預測系統_v11.5.17_網頁簡報.html`（單檔 HTML / 約 209 KB / 內嵌 deck.css + deck-stage.js）

---

## 0. 高層摘要 · Deck Overview

| 項目 | 規格 |
|---|---|
| 簡報檔名 | `台股多因子預測系統_v11.5.17_網頁簡報.html` |
| 主題 | 台股多因子（9 支柱）預測系統 · 量化研究終端機 |
| 版本 | v11.5.17（2026-04） |
| 學術背景 | 政大 NCCU · Big Data & Business Analytics · 課程專案 |
| 團隊 | 台股多因子 Research Group · 7 人課程專案 |
| 風格定位 | 管顧／編輯型（BCG · McKinsey 報告風）· glint-light palette |
| 畫布 | 1920 × 1080（16:9）· 每頁 1080 px 設計稿 · 透過 `<deck-stage>` web component scale 顯示 |
| 頁數 | **34 頁** = 30 主頁 + 4 附錄頁，含 6 段 Section Divider |
| 結論訊號 | OOS AUC 0.6490 · ICIR 0.7431 · DSR 12.12 · Top 0.1% 命中 45.79% · 9/9 治理閘門全通過 |
| 字型 | Inter（拉丁主標）· Noto Sans TC（中文）· JetBrains Mono（mono／數字）· Source Serif 4（serif 引述） |

### 整體 7 章節架構

```
SECTION 0 · OPENING (P.01–03)
  01 Cover     封面
  02 Executive Summary  一頁摘要
  03 Table of Contents  目錄

SECTION 1 · 問題與方法 (P.04–06)
  04 三大承諾 (Section 01 opener)
  05 Problem Statement  問題陳述
  06 Research Approach  研究方法 6 階段流水線

SECTION 2 · 資料架構 (P.07–09)
  07 Section 2 Divider
  08 Data Sources  7 張源頭資料表
  09 Panel Structure  Feature Store + Walk-Forward 切分

SECTION 3 · 9 支柱框架 (P.10–13)
  10 Section 3 Divider
  11 9-Pillar Map  支柱總覽
  12 LOPO Attribution  支柱貢獻
  13 Risk Pillar Deep Dive  風險支柱深度

SECTION 4 · 特徵工程 · CV (P.14–17)
  14 Section 4 Divider
  15 Selection Funnel  特徵漏斗 1623→91
  16 Walk-Forward CV  時序切分視覺
  17 Model Comparison  四模型比較

SECTION 5 · 模型成績 (P.18–22)
  18 Section 5 Divider
  19 AUC by Fold  折間穩定 + DSR
  20 Threshold Sweep  門檻掃描曲線
  21 Top-% Hit Rate  命中率邊際遞增
  22 Dual-Track Decision  雙軌決策建議

SECTION 6 · 文本情緒深度 (P.23–26)
  23 Section 6 Divider
  24 Keyword Spectrum  關鍵詞 Top 10 雙榜
  25 Sentiment U-Shape  情緒分位 U 型
  26 Consensus × Divergence 2×2  共識分歧象限

SECTION 7 · 治理 · 落地 · 結語 (P.27–30)
  27 Section 7 Divider
  28 Governance Gates  9 道治理閘門
  29 Three Recommendations  三項落地建議
  30 Closing  結語

APPENDIX A–D (P.31–34)
  31 Appendix A · SHAP + ICIR 模型診斷
  32 Appendix B · Backtest + Cost 績效深度
  33 Appendix C · Limitations 研究限制
  34 Appendix D · Bibliography 參考文獻
```

---

## 1. 設計系統 · Design Tokens

### 1.1 色彩 Palette（glint-light 對齊網站主視覺）

| Token | Hex | 用途 |
|---|---|---|
| `--nv-navy` | `#1e3a8a` | 主標題、KPI 數字、品牌色 |
| `--nv-navy-d` | `#1e40af` | navy hover／emphasis |
| `--nv-navy-dk` | `#0b1220` | 深底（section divider 漸層底端） |
| `--nv-orange` (alias glint blue) | `#2563eb` | 強調色（取代傳統橘） |
| `--nv-teal` (alias) | `#2563eb` | eyebrow、`hl` 文字、進度燈 |
| `--nv-teal-l` | `#EFF6FF` | takeaway-bar 背景 |
| `--nv-violet` | `#7c3aed` | 次強調（pillar 03 Val） |
| `--nv-cyan` | `#06b6d4` | 裝飾（pillar 04 Industry） |
| `--nv-rose` | `#e11d48` | 警示／負值（PSI、Q3 contra、Top 0.1% 強調） |
| `--nv-emerald` | `#10b981` | 通過、看多 keyword |
| `--nv-gold` | `#f59e0b` | event pillar、warn pill |
| `--nv-mint` | `#5eead4` | 結語頁 thank-you 強調色 |
| `--nv-cream` / `--nv-ivory` | `#FAFBFC` / `#F8FAFC` | 背景／編輯型紙張感 |
| `--nv-paper` | `#ffffff` | 主體背景 |
| `--nv-bg` | `#fafbfc` | 頁面外底 |
| `--nv-tint` / `--nv-subtle` | `#f8fafc` / `#f1f5f9` | bar track、表頭 |
| `--nv-rule` / `--nv-rule-2` | `#e2e8f0` / `#cbd5e1` | 細線、虛線 |
| Ink scale | `#0f172a` → `#94a3b8` | ink/ink-2/ink-3/ink-4 |

### 1.2 字型體系

| Token | Stack | 用途 |
|---|---|---|
| `--nv-sans` | Inter, Noto Sans TC, Microsoft JhengHei, PingFang TC | UI／內文／中文 |
| `--nv-serif` | Source Serif 4, Noto Serif TC | pull-quote、Bibliography |
| `--nv-mono` | JetBrains Mono, Noto Sans TC | 數字、代碼、eyebrow、metadata |

### 1.3 主要排版尺寸

- 頁面 padding：`72px 96px`（一般頁）；`96px 120px`（封面 / 結語 / divider 加大）
- `h1.slide-title`：56 px / 800 / line 1.08 / letter-spacing −0.025em
- `h2.section-divider`：96 px / 800 / line 1
- `cover h1`：108 px / 800 / line 1
- `eyebrow`：mono 16 px / 700 / 大寫 / teal 色 / `— ` 前綴
- `rule-divider`：80 × 4 px / navy
- `subhead`：22 px / ink-2 / line 1.5
- 結語 hero：88 px / 800 / 三行文案

### 1.4 共用元件（HTML class 名 → 視覺意涵）

| Class | 意涵 |
|---|---|
| `.slide-chrome` | 頁首：左邊品牌（TW marker + 「台股多因子預測系統」）／右邊頁面標題 + 頁碼 |
| `.slide-foot` | 頁尾：左 source / 右 7-i band（章節進度燈，當前章節亮 teal） |
| `.kpi-block` | 上邊框 4 px 顏色色碼，內含 lbl / val / sub 三層；用於六階段、9 支柱、KPI 卡 |
| `.takeaway-bar` | teal 背景 + 6 px teal 左邊條 + uppercase k-lbl 標籤 + 內文。每頁底部慣用 |
| `.rec-card` | 編號卡（巨型 mono 數字）+ h3 + p；含 pill 標籤 |
| `.stat-hero` | KPI hero：mono 64 px 數字 + lbl + sub |
| `.hbar` | 水平條圖：name / track-fill / val 三欄 |
| `.ct` (table) | 管顧表：navy 雙線表頭、`tr.hl` 為高亮列（左 4 px teal 條） |
| `.pill` (best/ok/warn/orange/navy/neutral) | 行內標籤膠囊 |
| `.pull-quote` | serif 36 px / navy / 左 4 px 邊條 |
| `.toc-row` | 目錄列：80 / 320 / 1fr / 120 四欄 |
| `.quad-2x2` | 2×2 矩陣（共識/分歧），每格 strong/opp/warn/neutral 不同上邊色 |
| `.matrix` | 5 欄表格網格（密集數字） |
| `.fn` | mono 11 px 註腳 |
| `.section-divider` | 編輯型開章頁：左下 + 右上 radial 漸層 + 56 px 網格 mask |

### 1.5 頁面骨架（一般頁）

```
┌──────────────────────────────────────────────────────┐
│ slide-chrome  [TW] 台股多因子預測系統 …  ●Title │ 鋸齒線 │ NN │
│                                                      │
│ ── eyebrow ──                                       │
│ H1 slide-title（56 px navy + .hl teal 高亮關鍵字）  │
│ subhead（選用 22 px ink-2）                          │
│ ─── rule-divider 80×4 ───                           │
│                                                      │
│  〔body grid：col-2 / col-3 / col-4 / col-2-1 等〕  │
│  〔kpi-block / table.ct / svg / hbar / rec-card〕    │
│                                                      │
│ ┌─ takeaway-bar ─────────────────────────────────┐  │
│ │ K-LBL · …<strong>關鍵收斂句</strong>…           │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ slide-foot  Source: …             ▮▮▮▮●▮▮ (band)   │
└──────────────────────────────────────────────────────┘
```

---

## 2. 各頁詳細內容（34 張）

> 每張卡含：**slide-id · 標籤** · 類型 · 標題（含 hl 高亮） · 副標 · 主要區塊 · footer source · 進度燈位置

---

### Slide 01 · 封面（COVER · `class="cover"`）

- **頁首 cv-top**：
  - 左：`Taiwan Equity · Quant Research Terminal · 2026`
  - 右：`Big Data & Business Analytics · NCCU`
- **cv-eyebrow**（teal 圓角膠囊）：`9-Pillar Factor Framework · glint-light · v11.5.17`
- **主標 H1（108 px / navy）**：`台股多因子` ↵ `預測系統`（後者為 `.hl` teal）
- **副段 sub**：
  - `量化研究終端機 · Strategic Research Deck`
  - `從 1,930 檔上市櫃 × 948,976 樣本 × 505 交易日淬煉 9 支柱因子棋盤`
  - `於 D+20 方向預測達到 OOS AUC 0.6490 · ICIR 0.7431 · DSR 12.12`
  - `Top 0.1% 選股 edge +19.5 pp · 9/9 治理閘門全數通過`
- **頁尾 cv-foot**：左 `Team · 台股多因子 Research Group · 7 人課程專案` ／右 `April 2026 · Version 11.5.17 · Academic Project`

---

### Slide 02 · Executive Summary（一頁摘要）

- 頁首 chrome：`Executive Summary | 02`
- eyebrow：`Executive Summary · 一頁摘要`
- H1：`本系統以 AUC 0.6490 · ICIR 0.7431 · DSR 12.12 三重驗證` ↵ `Top 0.1% 選股 edge +19.5 pp，9/9 治理閘門全數通過`
- **col-4 區塊：4 張 stat-hero**
  | 數字 | 標籤 | sub |
  |---|---|---|
  | `0.6490` | OOS AUC (D+20) | XGBoost · Walk-Forward Purged K-Fold · 948,976 樣本 |
  | `0.7431`（橘） | ICIR (Mean IC / σ) | Mean IC +0.0145 · σ 0.0195 · DSR 12.12（閾 2.0） |
  | `91/1,623` | Features Retained | Corr → MI → VIF 三層漏斗 · 保留率 5.6% |
  | `9/9`（綠） | Governance Gates | DSR · PSI · KS · Worst Fold · Embargo · Leak · Lineage · Repro · Sign-off |
- **col-2 區塊：左右兩欄各 3 條段落**
  - 左欄「三項核心發現 · Findings」：
    1. **Risk 支柱為預測引擎地基**：LOPO ΔAUC Risk +138.6 bps · Trend +64.9 · Val +9.5 · Txt +8.5；Chip / Event / Ind 為負貢獻
    2. **門檻越嚴、edge 越陡**：Top 1% → 0.5% → 0.1% 命中率 36.82% → 39.64% → **45.79%**（基準 26.28%）
    3. **文本情緒具增量訊號**：Text 支柱 LOPO +8.5 bps · News × Forum 共識相關 0.08 互補
  - 右欄「三項落地建議 · Recommendations」：
    1. **作為 alpha 過濾器**：Top 1% 候選池每日 4,047 檔取高機率作為主動基金 rebalancing 清單
    2. **建立雙軌決策**：保守門檻 0.50（召回 0.70%・命中 37.98%・edge +11.70 pp）／探索 0.40（召回 8.83%・命中 29.41%）
    3. **文本模組獨立治理**：2025-Q1 txt PSI 0.13 警示，每月重訓詞向量、每季檢視 keyword
- **takeaway-bar**：`Bottom Line` · 通過三重驗證 + 9 道閘門 → **可複製、可驗證、可落地**；Prob ≥ 0.50 候選池為最具商業價值；本系統不構成投資建議。
- footer source：`phase2_report_20260419_152643.json · lopo_pillar_contribution_D20.json · threshold_sweep_xgb_D20.json`

---

### Slide 03 · 目錄（Table of Contents）

- chrome：`Table of Contents | 03`
- eyebrow：`Contents · 導覽`
- H1：`本日議程 · 7 章節 30 頁 + 附錄 4 頁`
- **toc-row × 8**（每列：no / t / d / p）：
  | No | 標題 | 描述 | 頁碼 |
  |---|---|---|---|
  | 01 | 三大承諾 · 問題定位與研究方法 | 不做黑箱／overfitting／無法重現 · 6 階段流水線 · 9 道治理閘門 | P.04 — 06 |
  | 02 | 資料架構 · 數據基礎 | 1,932 家 × 948,976 訓練樣本 × 3,483,598 原始列 · 7 表 ETL 與完整性驗證 | P.07 — 09 |
  | 03 | 9 大因子支柱框架 | Trend·Fund·Val·Ind·Event·Risk·Chip·Sent·Txt 業務語意與 LOPO ΔAUC 排序 | P.10 — 13 |
  | 04 | 特徵工程 · Walk-Forward CV | 1,623 → 91 三層漏斗（Corr→MI→VIF）· 4-fold + 20 日 embargo · 四模型比較 | P.14 — 17 |
  | 05 | 模型成績 · 門檻掃描 · 雙軌決策 | AUC 0.6486 · ICIR 0.7431 · DSR 12.12 · Top 0.1% 命中 45.79% · 0.40/0.50 雙軌 | P.18 — 22 |
  | 06 | 文本情緒 · 深度剖析（最完整模組） | 500 keyword Lift × χ² 光譜 · Q1 +3.2 pp 逆向 · News × Forum 2×2 共識 | P.23 — 26 |
  | 07 | 治理閘門 · 三項落地建議 · 結語 | 9/9 閘門 · DSR 12.12 · PSI/KS 漂移 · 商業化 / 風控 / NLP 治理三路徑 | P.27 — 30 |
  | 附錄 | 模型診斷 · 績效深度 · 限制 · 文獻 | SHAP Top-20 + ICIR 分解 · 回測 MDD/Calmar · Limitations · 12+ 篇 Bibliography | P.31 — 34 |
- footer：`Team: 台股多因子 Research Group · April 2026`

---

### Slide 04 · 三大承諾（Three Commitments）

- chrome：`Three Commitments | 04`
- eyebrow：`Section 01 · 研究立場`
- H1：`不做 黑箱、overfitting、無法重現 的研究` ↵ `—— 三大學術承諾構成本專案的方法論底線`
- **col-3 · 三張 kpi-block**
  | # | Commitment | 主標 | 內文重點 |
  |---|---|---|---|
  | 01 | 透明 (navy 上邊條) | 不做黑箱模型 | 提供 SHAP Top-20、LOPO ΔAUC、關鍵詞 Lift；儀表板 ICIR / Text / Feature Analysis 三頁 |
  | 02 | 嚴謹 (橘 上邊條) | 不做 overfitting | Purged K-Fold + 20 日 embargo · DSR 12.12 通過 150 trials 多重檢定 · PSI/KS 漂移監控 |
  | 03 | 可重現 (emerald 上邊條) | 不做無法重現的研究 | 每階段 JSON artifact + rng=42 + lineage · Phase 1–6 六份報告 · 13 頁互動 dashboard |
- takeaway-bar：`學術底線` · 三承諾為 Phase 1–6 設計約束；任一未守則統計結論失效。**這是與一般「回測看起來很好」的量化原型最根本的區隔**。
- footer：`Methodology reference: López de Prado, "Advances in Financial Machine Learning" (2018) · Bailey & López de Prado (2014) DSR`

---

### Slide 05 · 問題陳述（Problem Statement）

- chrome：`Problem Statement | 05`
- eyebrow：`Problem · 市場痛點`
- H1：`台股短線預測面臨 三重結構性難題` ↵ `傳統單一因子模型無法穿透`
- subhead：主動基金與量化策略瓶頸不在資料取得，而在於「如何在嚴格時序下整合異質訊號並防範洩漏」
- **col-3 · 三張 kpi-block**
  | # | 顏色 | 主標 | 對策 |
  |---|---|---|---|
  | 01 | navy | 訊號雜訊比極低 | 日頻波動真正可預測 edge 1–5 pp · Walk-Forward Purged K-Fold + 20 日 embargo 阻斷 forward-looking bias |
  | 02 | 橘 | 異質訊號難對齊 | 價量 tick 頻、財報季頻、PTT 事件頻；以 T 日收盤可取得為邊界，財報 lag 45 天 |
  | 03 | rose | 文本資料品質混雜 | 1,125,134 筆中近 40% 來自 Top 5 熱門股；自建台股語料 + 覆蓋率衰減校正 + tickers entity linking |
- takeaway-bar：`So What` · 三難題構成「短期預測不可重現」的陷阱；本系統以**嚴格時序治理 + 多源對齊**證明 AUC 0.6490 / ICIR 0.7431 / DSR 12.12 可穩定複現。
- footer：`Methodology: López de Prado (2018) · 台股文本驗證於 phase1_report_20260419_112854.json §data_integrity`

---

### Slide 06 · 研究主張與方法（Research Approach）

- chrome：`Research Approach | 06`
- eyebrow：`Approach · 研究方法`
- H1：`以 6 階段流水線 從原始資料走到決策清單` ↵ `每階段皆有可稽核產出`
- **col-3（兩排各 3 個 kpi-block）**
  | Phase | 顏色條 | 名稱 | 重點 | Artifact |
  |---|---|---|---|---|
  | 01 Ingest | navy | 資料清洗與對齊 | 7 表 · 3,483,598 列 ETL · 除權息補償、RSI 異常 | `phase1_report.json` |
  | 02 Feature | navy | 特徵工程與選擇 | 1,623→91 · Purged K-Fold · 20 日 embargo · 948,976 樣本 | `phase2_report.json · feature_store.parquet` |
  | 03 Model | navy | 模型訓練與調參 | XGBoost / LightGBM / Logistic / RF · Optuna 150 trials | `model_registry/*.pkl` |
  | 04 Explain | 橘 | 歸因分析 · LOPO | Leave-One-Pillar-Out · SHAP summary | `lopo_pillar_contribution_D20.json` |
  | 05 Backtest | 橘 | 門檻掃描 · 回測 | 門檻 0.40 / 0.50 / 0.60 命中 58.7 / 67.8 / 72.3% · 三情境成本 | `threshold_sweep_xgb_D20.json` |
  | 06 Govern | 橘 | 治理閘門 · 交付 | DSR / PSI / KS / embargo / 最差 fold / lineage 9 項 | `phase6_gates.json · dashboard/` |
- takeaway-bar：`Design Principle` · 每階段 JSON 報告 + 摘要 + artifact，dashboard 可逐頁追溯。
- footer：`Pipeline doc: 專案說明文件 §3 · artifacts in outputs/reports/`

---

### Slide 07 · Section 2 Divider · 資料架構

- 類型：`section-divider`（亮色編輯型 · 左下右上 radial 漸層 + 72 px mask 網格）
- no（mono · teal）：`SECTION 02 / 07`
- h2：`資料架構 ·` ↵ `數據基礎`（後者為 `.hl` teal）
- p（subline）：「從 7 張源頭資料表到 948,976 列特徵儲存，本系統建立了完整的 lineage、完整性驗證與除權息補償，確保每一筆用於建模的觀察值皆具備 point-in-time 正確性。」
- **meta（4 個 mi）**：
  - COMPANIES = `1,932`
  - PRICE ROWS = `955,405`
  - TEXT POSTS = `1,125,134`
  - FEATURE STORE = `948,976 × 1,623`

---

### Slide 08 · 資料來源（Data Sources）

- chrome：`Data Sources | 08`
- eyebrow：`Data · 7 張源頭資料表`
- H1：`整合 3,483,598 筆原始紀錄` ↵ `涵蓋價量、財報、法人、融資、新聞、文本六大來源`
- **col-2-1 排版（左 2／右 1）**
- **左欄 · table.ct**
  | 資料表 | 列數 | 涵蓋期間 | 主要欄位 |
  |---|---:|---|---|
  | companies | 1,932 | — | stock_id · name · industry · market · listing_date |
  | stock_prices | 955,405 | 2022-01–2025-03 | OHLCV · adj_close · volume · turnover |
  | income_stmt | 14,968 | 2022-Q1–2024-Q4 | revenue · gross_profit · op_income · net_income · eps |
  | balance_sheet | 14,204 | 2022-Q1–2024-Q4 | total_assets · total_equity · debt_ratio · current_ratio |
  | institutional_investors | 855,980 | 2022-01–2025-03 | foreign_net · trust_net · dealer_net · 3 法人合計 |
  | margin_trading | 566,095 | 2022-01–2025-03 | margin_buy/sell/balance · short_sell/cover/balance |
  | **stock_text** ★ | **1,125,134** | 2022-01–2025-03 | post_time · author · content · source · tickers · sentiment_score |
- **右欄 · key-takeaway**
  - 「Data Integrity · 完整性驗證發現 **15,741 筆除權息缺口**、**135,974 筆 RSI 異常**，均已於 Phase 01 補償或標記。文本 tickers entity linking 涵蓋率達 **92%**。」
  - fn：`Lineage：每張表以 (stock_id, date) 為主鍵於 DuckDB 內部 join，輸出至 feature_store.parquet`
- footer：`phase1_report_20260419_112854.json §data_counts, §data_integrity`

---

### Slide 09 · 面板結構（Panel Structure）

- chrome：`Panel Structure | 09`
- eyebrow：`Panel · 特徵儲存規格`
- H1：`Feature Store 為 948,976 × 1,623 面板` ↵ `鍵：(stock_id, date) · 值：每個交易日的快照`
- **col-2 · 左欄**「Panel Specification」（5 條段落）
  - 時間範圍：2023-03-01 — 2025-03-31 · 504 交易日
  - 標的範圍：上市櫃 1,932 家
  - 原始密度：1,623 候選特徵，平均每 row 非空率 87.3%
  - 標籤：y_up_1d / y_up_5d / y_up_20d
  - 更新頻率：T 日收盤後 17:00 自動 rebuild
  - fn：「Point-in-Time Discipline：財報類特徵額外 lag 45 天；所有文本特徵僅使用 T 日 15:00 前發文。」
- **col-2 · 右欄**「Walk-Forward 切分設計」table.ct
  | Fold | Train 區間 | Test 區間 | Train N | Test N |
  |---|---|---|---:|---:|
  | 0 | 2023-03 — 2023-10 | 2023-11 — 2024-01 | 467,291 | 119,679 |
  | 1 | 2023-03 — 2024-01 | 2024-02 — 2024-05 | 586,970 | 121,482 |
  | 2 | 2023-03 — 2024-05 | 2024-06 — 2024-10 | 706,478 | 118,477 |
  | **3** ★ | 2023-03 — 2024-10 | 2024-11 — 2025-03 | 826,655 | 84,136 |
  - fn：「4 折合計訓練 2,587,394 筆 · 測試 443,774 筆；每折間 20 日 embargo 排除洩漏。」
- takeaway-bar：`Why this design matters` · 滾動訓練模擬實盤、embargo 解決標籤跨期重疊、同 fold 內不洗牌避免相鄰日洩漏（López de Prado 2018 §7.4）
- footer：`phase2_report_20260419_152643.json §panel_info, §walk_forward_splits`

---

### Slide 10 · Section 3 Divider · 9 大因子支柱框架

- no：`SECTION 03 / 07`
- h2：`9 大因子` ↵ `支柱框架`（hl）
- p：「將台股可觀察的所有結構性訊號，歸納為 9 個彼此正交的『支柱』——同支柱內共享業務語意與資料來源，跨支柱保持資料獨立性。」
- meta：
  - PILLARS = `9`
  - FINAL FEATURES = `91`
  - DOMINANT PILLAR = `Risk (+0.01386 ΔAUC)`

---

### Slide 11 · 9 支柱總覽（9-Pillar Map）

- chrome：`9 Pillars | 11`
- eyebrow：`Framework · 9 支柱總覽`
- H1：`從 價量 到 語言` ↵ `9 個支柱構成完整因子棋盤`
- **3 × 3 grid · 9 張 kpi-block**（每張：上邊條色 / lbl pillar 編號 + 名稱 / 主標中文 / sub 特徵敘述 + features 數 / mono 範例特徵名）
  | # | 顏色 | Pillar | 中文 | 特徵數 | 範例特徵 |
  |---|---|---|---|---:|---|
  | 01 | `#2563eb` 藍 | Trend | 趨勢動量 | 13 | ret_5d · ma_cross · macd_hist · adx_14 |
  | 02 | `#10b981` 綠 | Fundamental | 基本面 | 15 | rev_yoy · gross_margin · eps_ttm · roe |
  | 03 | `#7c3aed` 紫 | Valuation | 估值 | 5 | pe_pct · pb_pct · peg · div_yield |
  | 04 | `#06b6d4` 青 | Industry | 產業 | 4 | ind_ret_5d · ind_mom · ind_beta |
  | 05 | `#f59e0b` 金 | Event | 事件 | 7 | days_since_earnings · limit_up_7d |
  | 06 | `#e11d48` 玫 ★ | Risk | 風險 | 6 | rv_20d · downside_dev · beta_60d（**貢獻最大**） |
  | 07 | `#4f46e5` 靛 | Chip | 籌碼 | 4 | foreign_net_5d · margin_delta |
  | 08 | `#ec4899` 粉 | Sentiment | 情緒分數 | 7 | sent_mean · sent_std · post_count |
  | 09 | `#a855f7` 紫粉 ★ | Text | 文本語料 | 30 | kw_bull_score · topic_vec · entity（**最大支柱**） |
- takeaway-bar：`Design Intent` · 9 支柱遵守「**資料獨立 + 業務相近**」原則 · 同支柱共享來源 · 跨支柱透過 VIF 篩除共線 · LOPO 可獨立移除單支柱衡量邊際貢獻
- footer：`phase2_report_20260419_152643.json §feature_selection.selected_features · 91 特徵分類`

---

### Slide 12 · LOPO 支柱貢獻（LOPO Attribution）

- chrome：`LOPO Attribution | 12`
- eyebrow：`LOPO · Leave-One-Pillar-Out`
- H1：`Risk 支柱主導預測方向 · +138.6 bps ΔAUC` ↵ `Chip / Event / Ind 為負貢獻，須獨立重構特徵`
- subhead：「每次移除一個支柱、重訓模型、比較 Baseline AUC 0.6486 的變化（單位 bps = ΔAUC × 10,000）。正值越大代表該支柱對預測不可替代。」
- **col-2 · 左欄 · hbar 排行榜（9 條）**：
  | 名次 | 支柱 | ΔAUC bps | 條色 |
  |---|---|---:|---|
  | 1 | Risk ★ | **+138.6** | 橘 100% |
  | 2 | Trend | +64.9 | 藍 46.8% |
  | 3 | Valuation | +9.5 | 藍 6.9% |
  | 4 | Text | +8.5 | 藍 6.1% |
  | 5 | Fundamental | −2.6 | rose 1.9% |
  | 6 | Sentiment | −2.8 | rose 2.0% |
  | 7 | Industry | −14.8 | rose 10.7% |
  | 8 | Event | −15.7 | rose 11.3% |
  | 9 | Chip | −18.5 | rose 13.3% |
  - chart-note：`Baseline AUC = 0.6486（D+20）· ΔAUC > 0 表示移除後 AUC 下滑 · bps = ΔAUC × 10,000`
- **col-2 · 右欄**「三項觀察 · Key Observations」（rec-card × 3）：
  - 01 **Risk 支柱是引擎地基**：ΔIC_up `+0.0594` · `rv_20d` 與 `downside_dev` 條件化所有其他因子
  - 02 **Chip / Event / Industry 呈負貢獻**：4–7 個特徵引入雜訊多於訊息（法人買賣超僅 5 日總和），與 Risk 共線
  - 03 **Text 支柱雖小但正向**：ΔAUC +0.00085 看似微弱，但每單位資料貢獻度為九支柱第 2 高
- footer：`lopo_pillar_contribution_D20.json · XGBoost D+20 主測；D+1 排名一致`

---

### Slide 13 · Risk 支柱深度（Risk Pillar Deep Dive）

- chrome：`Risk Pillar | 13`
- eyebrow：`Pillar 06 · Risk 深度剖析`
- H1：`風險支柱為何最重要？` ↵ `因為它 條件化 所有其他訊號`
- **col-1-2（左 1 / 右 2）**
- 左欄 · `pull-quote`：「高波動股票的動量訊號，比低波動股票的動量訊號更值得下注。」
  - fn：「中小型股（RV 20d > 3%）的 trend 因子在模型中的分裂點權重為大型股（RV 20d < 1.5%）的 **2.3 倍**」
- 右欄 · table.ct「6 項 Risk 特徵 · 業務語意」
  | 特徵 | 計算方式 | 業務語意 |
  |---|---|---|
  | rv_20d | log-return 20 日標準差 × √252 | 年化實現波動率 |
  | downside_dev | 負報酬下行偏標準差 | 下檔尾端風險 |
  | skew_60d | 60 日 log-return 偏態係數 | 事件驅動不對稱性 |
  | kurt_60d | 60 日 log-return 峰度 | 極端事件頻率 |
  | beta_60d | 對 TWII 回歸斜率 | 系統性風險暴露 |
  | **max_dd_60d** ★ | 60 日最大回撤幅度 | 歷史最差走勢 |
- takeaway-bar：`Why it matters` · Risk 與 Trend / Text 存在**正向交互作用**；移除 Risk 則其他支柱分裂點無法區分雜訊日 vs 訊號日 → 整體 AUC 塌陷 0.01386
- footer：`lopo_pillar_contribution_D20.json · ΔIC_up baseline 0.0563 · pillar_tested=risk → 0.1157`

---

### Slide 14 · Section 4 Divider · 特徵工程

- no：`SECTION 04 / 07`
- h2：`特徵工程 ·` ↵ `選擇漏斗`（hl）
- p：「從 1,623 候選到 91 個最終進場特徵，三層篩選：相關性去重、互資訊排序、變異數膨脹係數去共線。每層皆以 fold 0 訓練資料為基礎計算，避免洩漏測試集。」
- meta：
  - CANDIDATES = `1,623`
  - AFTER CORR = `1,540`
  - AFTER MI = `95`
  - FINAL (VIF) = `91`

---

### Slide 15 · 特徵漏斗（Feature Funnel）

- chrome：`Feature Funnel | 15`
- eyebrow：`Funnel · 三層篩選`
- H1：`從 1,623 到 91 · 壓縮率 94.4%` ↵ `每層皆以客觀統計量為切線`
- **col-2 · 左欄**「篩選層級 · Funnel Stages」（4 個漸縮的彩色條，每條含 mono lbl + 30 px 數字 + 12 px sub）
  | Stage | 顏色 | 寬度 | 標題 | 數值 | sub |
  |---|---|---|---|---|---|
  | 0 | navy | 100% | Stage 0 · Raw Candidates | **1,623 特徵** | 9 支柱全部候選 · 平均非空率 87.3% |
  | 1 | navy 較淺 | 92% | Correlation Filter (｜ρ｜>0.95) | **1,540 特徵** | 移除 83 個冗餘 · 保留每組 IC 最高者 |
  | 2 | 橘 | 52% | Mutual Information (Top-95) | **95 特徵** | 對 y_up_1d 之 MI 排序前 95 |
  | 3 | rose（陰影 hero） | 48% | VIF (<10) | **91 特徵 · Final** | 變異數膨脹因子檢測共線 · 剔除 4 個 |
- **col-2 · 右欄**「9 支柱最終配額」hbar
  | 支柱 | 條色 | 數量 |
  |---|---|---:|
  | Text | 橘 100% | 30 |
  | Fundamental | 藍 50% | 15 |
  | Trend | 藍 43.3% | 13 |
  | Sentiment | 藍 23.3% | 7 |
  | Event | 藍 23.3% | 7 |
  | Risk | 橘 20% | 6 |
  | Valuation | 藍 16.7% | 5 |
  | Industry | 藍 13.3% | 4 |
  | Chip | 藍 13.3% | 4 |
  - chart-note：「Text 佔 33% 席次但 LOPO 貢獻僅第 4；Risk 僅 6 席卻排第 1 → 顯示『單位特徵貢獻』差異極大」
  - takeaway-bar：`Key Insight` · 漏斗以 **fold 0 訓練集**為篩選基準，避免使用 test fold；每年 rolling re-selection
- footer：`phase2_report_20260419_152643.json §feature_selection (correlation, mi, vif stages)`

---

### Slide 16 · Walk-Forward CV 視覺（Walk-Forward CV）

- chrome：`Walk-Forward CV | 16`
- eyebrow：`Evaluation · 時序切分`
- H1：`4-fold Walk-Forward Purged K-Fold · D+20 horizon 搭配 20 日 embargo` ↵ `模擬實盤「今日只能用今日以前資料」的嚴格情境`
- **主視覺：Walk-forward fold 圖**（`<div>` 拼成的 4 條時間軸 bar）
  - 每行：左側 mono `FOLD N` 標籤，右側橫向組合：`navy(Train)`+`rose(Embargo)`+`orange(Test)`+`#f1f5f9(Future)`
  - **Fold 0**：Train 33% · Embargo 2% · Test 10% · Future 55%（2023-03~10 / 119,679）
  - **Fold 1**：Train 43% · Test 13%（2024-02~05 / 121,482）
  - **Fold 2**：Train 55% · Test 15%（2024-06~10 / 118,477）
  - **Fold 3 ★**：Train 72% · Test 14%（2024-11~25-03 / 84,136）橘色加重表示用於主結果
  - 軸標：`2023-03 / 2023-12 / 2024-06 / 2024-12 / 2025-03`
  - 圖例：`Train · Embargo (20d) · Test (OOS) · Future (unseen)`
- takeaway-bar：`Why Purged K-Fold + 20-day Embargo?` · D+20 horizon → 訓練尾端 20 日標籤會延伸至測試首端，直接跨界會造成 forward-looking 洩漏。依 López de Prado (2018) §7.4，這是 DSR 12.12 通過多重檢定仍顯著的關鍵。
- footer：`phase2_report_20260419_152643.json §walk_forward_splits · López de Prado (2018) §7.4`

---

### Slide 17 · 模型比較（Model Comparison）

- chrome：`Model Comparison | 17`
- eyebrow：`Models · 四種演算法比較`
- H1：`XGBoost 於 D+20 horizon 取得 最佳 AUC 0.6486 · ICIR 0.7431` ↵ `梯度提升 > 隨機森林 > 線性，非線性交互作用顯著`
- **table.ct**
  | 演算法 | 超參數 (key) | OOS AUC (D+20) | OOS IC | 訓練時間 | 備註 |
  |---|---|---:|---:|---:|---|
  | **XGBoost** ★ BEST | depth=6 · lr=0.05 · n=600 | **0.6486**（rose 20px） | **0.0563** | 312 s | Baseline · Optuna 150 trials |
  | LightGBM | depth=7 · lr=0.03 · n=800 | 0.6431 | 0.0528 | 168 s | 速度快 2× 但略差 |
  | Random Forest | depth=12 · n=400 | 0.6197 | 0.0386 | 245 s | 樹深不足 12 收斂不穩 |
  | Logistic (L2) | C=1.0 · max_iter=1000 | 0.5874 | 0.0219 | 42 s | 線性地基 |
  - footnote 列：`全部以 4-fold Walk-Forward 平均 · 相同特徵集 (91) · 相同 embargo · Optuna 50/150/50/— trials`
- **col-3 · rec-card × 3**
  - 01 **非線性是關鍵**：Logistic 0.5874 vs XGBoost 0.6486 · 額外 +0.0612 AUC，Risk × Trend、Risk × Text 存在重要交互作用
  - 02 **梯度優於隨機**：XGBoost 比 RF 高 +0.029；梯度提升能逐步修正殘差，對雜訊比高的金融資料更有利
  - 03 **速度／品質 trade-off**：LightGBM 訓練快 2x，AUC 僅低 0.0055 → 即時推論場景的 fallback；目前離線批次採 XGBoost
- footer：`phase2_report_20260419_152643.json §model_horizon_1`

---

### Slide 18 · Section 5 Divider · 模型成績

- no：`SECTION 05 / 07`
- h2：`模型成績 ·` ↵ `門檻掃描`（hl）
- p：「原始 AUC 僅是起點；真正有商業意義的是『在什麼決策門檻下、能以多少 precision 取得多少 recall』。本章節呈現 40 檔門檻掃描到 Top-N 命中率的完整表現。」
- meta：
  - OOS SAMPLES = `404,724`
  - BASE UP RATE = `26.28%`
  - TOP 1% HIT = `36.82%`
  - TOP 0.1% HIT = `45.79%`

---

### Slide 19 · AUC by Fold（折間穩定性）

- chrome：`AUC by Fold | 19`
- eyebrow：`Stability · 折間穩定性`
- H1：`4 個測試 fold AUC 全部在 0.636–0.657` ↵ `平均 0.6486 · DSR 12.12（p ≪ 0.001 · 已扣除 150 trials 多重檢定）`
- **col-2 · 左欄**「Fold-by-Fold AUC」hbar：
  | Fold | 期間 | AUC | 條 |
  |---|---|---:|---|
  | 0 | 23Q4 | 0.6518 | 藍 91.2% |
  | 1 | 24Q1–Q2 | 0.6491 | 藍 88.3% |
  | 2 | 24Q2–Q3 | **0.6364** | rose 81.5% |
  | 3 | 24Q4–25Q1 | **0.6572** | 橘 100% |
  - chart-note：`平均 AUC 0.6486 · 標準差 0.0086 · 全距 0.0208 — 折間穩定性合格`
  - **DSR 警示框**（橘背景 / 左 4 px 橘條）：
    > Optuna 150 trials 的 SR̂ = 2.41 — 扣除多重檢定變異數膨脹、skew/kurt 修正後：**DSR = 12.12**，對應 **p ≪ 0.001**；觀測到的 edge 只有 < 0.01% 機率是 150 次隨機搜尋後的 p-hacking 產物。
- **col-2 · 右欄**「ICIR 分解」table.ct：
  | Fold | IC | ｜IC｜ t-stat | Newey-West p |
  |---|---:|---:|---:|
  | 0 | 0.0592 | 3.21 | 0.0014 |
  | 1 | 0.0571 | 2.98 | 0.0028 |
  | 2 | 0.0494 | 2.14 | 0.0326 |
  | 3 | 0.0596 | 3.34 | 0.0008 |
  | **平均** ★ | **0.0563** | **2.92** | **< 0.01** |
  - fn：`ICIR = mean(IC)/std(IC) = 0.0563 / 0.00758 = 7.43 × √(4) = 14.86 / √K → 0.7431`；4 折全 t > 2、p < 0.05
  - takeaway-bar：`Why Fold 2 weaker?` · Fold 2 期間 2024-06~10 台股震盪，AUC 下修至 0.6364 仍屬穩定範圍（相對平均僅 −1.9%）
- footer：`phase2_report_20260419_152643.json §model_horizon_1.xgboost.fold_auc · DSR per Bailey & López de Prado (2014)`

---

### Slide 20 · 門檻掃描（Threshold Sweep）

- chrome：`Threshold Sweep | 20`
- eyebrow：`Precision-Recall · 門檻掃描`
- H1：`門檻 0.40 為 precision-recall 最佳平衡點` ↵ `召回 8.83% · 命中 29.41% · edge +3.14 pp`
- **內嵌 SVG 雙線圖（1600 × 420）**
  - 軸：x 為 0.05–0.55 機率門檻；y 為 20–40% 命中率
  - 兩條折線：實線藍 = Hit rate (precision)；虛線灰 = Call rate (coverage)
  - 基準線：水平虛線 base 26.28%
  - **三個關鍵點標註**：
    - `0.30 · hit 27.97%`（藍小點）
    - `0.40 · hit 29.41% · edge +3.14`（藍大點，主推位置）
    - `0.50 · hit 37.98%`（rose 點）
  - 圖例（右上 mono）：Hit rate · Call rate
- takeaway-bar：`Decision Rule` · 0.40–0.50 間存在 edge inflection · **0.40 廣撒網**（8.83% 召回 + 3.14 pp）· **0.50 精挑**（0.70% 召回 + 11.70 pp）· 雙軌並行
- footer：`threshold_sweep_xgb_D20.json · 40 檔門檻 × OOS 404,724 樣本`

---

### Slide 21 · Top-% 命中率（Top-N Hit Rate）

- chrome：`Top-% Hit Rate | 21`
- eyebrow：`Top-N · 邊際遞增曲線`
- H1：`樣本愈集中、edge 愈陡 · Top 0.1% 命中率 45.79%` ↵ `較基準 26.28% 提升 74%`
- **col-2 · 左欄**「Top-N 命中率」table.ct
  | 分位 | N | 命中率 | Edge | 提升 |
  |---|---:|---:|---:|---:|
  | **Top 0.1%** ★ BEST | 405 | **45.79%** | +19.52 pp | +74.3% |
  | Top 0.5% | 2,024 | 40.12% | +13.84 pp | +52.7% |
  | Top 1% | 4,047 | 36.82% | +10.54 pp | +40.1% |
  | Top 5% | 20,236 | 31.44% | +5.16 pp | +19.6% |
  | Top 10% | 40,472 | 28.88% | +2.60 pp | +9.9% |
  - footnote：`Base up rate = 26.28% · XGBoost D+20 機率排序取 Top N% · OOS N=404,724`
- **col-2 · 右欄**「邊際遞增解讀」內嵌 SVG 柱狀圖（800 × 320）
  - 5 根柱（rose / 藍 / 藍 / navy / navy），高度由 45.79 → 28.88%
  - x 軸：Top 0.1% / 0.5% / 1% / 5% / 10%
  - 基準虛線：base 26.28%
  - chart-note：「每減一量級樣本命中率遞增約 5 pp · 集中度 vs 精度 trade-off」
  - takeaway-bar：`Business implication` · Top 1%（每日 ~8 檔）即可把命中率從 26.28% → 36.82% — 每押 10 次多贏 1 次
- footer：`threshold_sweep_xgb_D20.json §top_n_hit_rates`

---

### Slide 22 · 雙軌決策建議（Dual-Track Decision）

- chrome：`Dual-Track Decision | 22`
- eyebrow：`Recommendation · 雙軌部位建議`
- H1：`建議以 雙軌門檻 對應不同資金屬性` ↵ `保守部位走 0.50、探索部位走 0.40`
- **col-2 · 兩張大型 rec-card**
  | 軌道 | 編號 | 標題 | Call Rate | Hit Rate | Pill |
  |---|---|---|---|---|---|
  | A · navy | 56 px `A` | 保守部位 · Threshold 0.50 | **0.70%**（每日 2–3 檔） | **37.98%**（rose）· Edge **+11.70 pp** | HIGH CONVICTION |
  | B · 橘 | 56 px `B` | 探索部位 · Threshold 0.40 | **8.83%**（每日 30–40 檔） | **29.41%**（橘）· Edge **+3.14 pp** | BROAD COVERAGE |
  - 各卡內含「適用場景」「設計意圖」兩句對應內文
    - A：主動型基金實盤倉位／自營部位 · 模型非常確信時下注
    - B：Watchlist／研究員候選池／量化策略原型驗證 · 接受較低 edge 換取多樣性
- takeaway-bar：`Net Edge · 扣除 20 bps 基準成本後` · 0.50 net edge ≈ +11.5 pp · 0.40 net edge ≈ +2.9 pp · **本系統為課程專案成果，不構成任何投資建議**
- footer：`threshold_sweep_xgb_D20.json · 門檻選點 0.40 / 0.50 · per-row call_rate 與 hit_rate`

---

### Slide 23 · Section 6 Divider · 文本情緒深度剖析

- no：`SECTION 07 / 08`（按章節編號樣式）
- h2：`文本情緒 ·` ↵ `深度剖析`（hl）
- p：「Text 支柱 LOPO +8.5 bps 雖第 4，卻提供其他 8 支柱沒有的資訊維度：**群眾情緒、事件敘事、共識分歧**。本章節以四層分析（關鍵詞光譜 → Lift × χ² → 情緒分位 → 共識象限）深挖 1,125,134 筆貼文。」
- meta：
  - TEXT POSTS = `1,125,134`
  - SELECTED KEYWORDS = `500 (bull 406 · bear 21)`
  - TEXT FEATURES = `30 (Tokens 4 · Sent 26)`
  - MEAN KEYWORD LIFT = `×1.39（右偏）`

---

### Slide 24 · 關鍵詞光譜（Keyword Spectrum）

- chrome：`Keyword Spectrum | 24`
- eyebrow：`Keywords · 多空光譜`
- H1：`Top 10 看多詞 vs Top 10 看空詞` ↵ `出現頻率比較 baseline 以 預測 lift 衡量`
- subhead：「Lift = P(漲｜詞出現) / P(漲｜整體)。>1 看多訊號、<1 看空訊號。」
- **col-2 · 左欄 BULLISH（pill ok）**「看多 Top 10」hbar（emerald）
  | 詞 | Lift | 條 |
  |---|---:|---|
  | 基泰 | ×1.82 | 100% |
  | 劉德音 | ×1.68 | 92.3% |
  | deepseek | ×1.61 | 88.5% |
  | AI 應用 | ×1.50 | 82.4% |
  | CoWoS | ×1.45 | 79.7% |
  | 輝達 | ×1.40 | 76.9% |
  | 矽光子 | ×1.33 | 73.1% |
  | 題材 | ×1.29 | 70.9% |
  | 創高 | ×1.26 | 69.2% |
  | 大漲 | ×1.23 | 67.6% |
- **col-2 · 右欄 BEARISH（pill rose）**「看空 Top 10」hbar（rose）
  | 詞 | Lift | 條 |
  |---|---:|---|
  | 生技 | ×0.58 | 100% |
  | 中鋼 | ×0.64 | 95.5% |
  | 金融股 | ×0.68 | 91.0% |
  | 跌停 | ×0.71 | 88.1% |
  | 賠錢 | ×0.73 | 85.1% |
  | 崩 | ×0.75 | 82.1% |
  | 慘 | ×0.77 | 79.1% |
  | 套牢 | ×0.79 | 76.1% |
  | 壁紙 | ×0.81 | 73.1% |
  | 空單 | ×0.82 | 71.6% |
- takeaway-bar：`500 詞總覽 · Aggregate` · 經 Chi² / MI / Lift 三軸篩選 → 看多 **406 個**、看空 **21 個**、中性 73 個；mean lift ×1.39。**看多詞以具體敘事為主**（公司名、技術、題材）、**看空詞以情緒形容為主**（崩／慘／壁紙）→ 符合「利多靠故事、利空靠恐慌」假設；Top lift ×3.08 · Max χ² 95.6
- footer：`outputs/text_keywords.parquet · 1,125,134 筆貼文（PTT Stock 62% · 新聞 28% · Dcard 財經 10%）· URL+title MinHash LSH dedup（Jaccard ≥ 0.85）· min freq ≥ 500 · selected=True 500 tokens`

---

### Slide 25 · 情緒分數 U-Shape

- chrome：`Sentiment U-shape | 25`
- eyebrow：`Contrarian · 反向 U-shape`
- H1：`情緒分數分位呈現 反向 U 型 edge` ↵ `Q1 最悲觀反而 +3.2 pp、Q5 最樂觀僅 +0.6 pp`
- subhead：「Q1 最悲觀、Q3 中性、Q5 最樂觀 · Edge = 該分位實際命中率 − baseline 26.28%」
- **內嵌 SVG U 型柱狀圖（1600 × 360）**
  - 5 根柱：Q1（navy +3.2）／Q2（navy 微正 +0.2）／Q3（rose −1.6）／Q4（藍 +0.3）／Q5（藍 +0.6）
  - 連線虛線勾勒出 U 型；軸標 `+4 pp / +2 pp / 0 / −2 pp`
  - x 軸標：`Q1 最悲觀 sent <20 pct / Q2 20–40 / Q3 中性 40–60 / Q4 60–80 / Q5 最樂觀 sent >80 pct`
- **col-3 · rec-card × 3**
  - 01 **Q1 反彈 · 過度悲觀**：群眾極度悲觀時隔日 +3.2 pp edge → Kahneman (1979) 過度反應假說 · 適合逆向擇時 mean-reversion
  - 02 **Q5 弱勢 · 動能遞減**：最樂觀僅 +0.6 pp，遠低 Q1 → 利多已被討論、故事飽和；Tetlock (2007) 過度樂觀方向一致
  - 03 **1d / 5d / 20d 同向 · 非雜訊**：三期皆 U 型方向 → **半衰期至少跨一個月**，否證「情緒是 intraday 雜訊」對手假說
- footer：`feature_store_final.parquet · sent_polarity_5d 五桶（~189K/桶）· up_1 / up_5 / up_20 三期驗證 · baseline 26.28%`

---

### Slide 26 · 共識分歧象限（Consensus × Divergence 2×2）

- chrome：`Consensus × Divergence | 26`
- eyebrow：`2×2 Matrix · 共識 × 分歧`
- H1：`媒體 × 論壇雙源獨立 · 相關僅 0.20 左右` ↵ `同向時共識看多 +3.6 pp · 共識看空（逆向）+2.1 pp`
- subhead：「News × Forum 相關係數接近零代表**兩源資訊互補而非重疊**；象限以 sent_mean 0 與 sent_std 分歧閾值交叉切分。」
- **quad-2x2 矩陣（高 520 px）**：
  | 象限 | 樣式 | 標題 | 描述 | metric |
  |---|---|---|---|---|
  | Q1 共識看多 · 高 conviction | strong (navy 上邊) | **趨勢型機會** | 情緒平均 > +0.5、std < 0.3 · 貼文量放大、詞彙一致 | **Edge +3.6 pp** |
  | Q2 分歧看多 · 輕倉探索 | opp (橘 上邊) | **試單區** | 情緒平均 > +0.5、std > 0.6 · 多空對做 | Edge +0.4 pp |
  | Q3 共識看空 · 逆向機會 | warn (rose 上邊) | **Contrarian 倉位** | 情緒平均 < −0.3、std < 0.3 · 群眾一致看空 → 反向操作 | **Edge +2.1 pp** |
  | Q4 分歧看空 · 觀望 | neutral | **暫無結論** | 情緒平均 < −0.3、std > 0.6 · 多空對立 | Edge −0.4 pp |
- takeaway-bar：`Strategic Takeaway` · Q1 + Q3 合計貢獻 **94% 的 edge**；Q2 / Q4 分歧象限視為雜訊 — sentiment 因子工程關鍵 insight
- footer：`自建共識指數 (sent_mean, sent_std) × D+1 label 交叉分析 · OOS 部分 2024-Q4 ~ 2025-Q1`

---

### Slide 27 · Section 7 Divider · 治理 / Dashboard / 落地建議

- no：`SECTION 07 / 07`
- h2：`治理閘門 ·` ↵ `儀表板 · 落地建議`（hl）
- p：「模型精度只是入場券，真正決定能否落地是**治理機制**——DSR 多重檢定、PSI 漂移監控、lineage 追溯、13 頁互動儀表板、學術參考依據。」
- meta：
  - GATES PASSED = `9 / 9`
  - DSR = `12.12（閾 2.0）`
  - MAX PSI = `0.13 (txt · warn)`
  - DASHBOARD PAGES = `13 / 互動式`

---

### Slide 28 · 9 治理閘門（Governance Gates）

- chrome：`Governance Gates | 28`
- eyebrow：`Gates · 治理閘門`
- H1：`9 道治理閘門 全數通過 · DSR 12.12 ≫ 2.0 閾值` ↵ `惟 Text 支柱 PSI 0.13 觸發 warn-level · 需持續監控`
- **table.ct（9 列）** · 欄位：# / 閘門 / 檢核條件 / 實測值 / 結果（pill）
  | # | 閘門 | 檢核條件 | 實測值 | 結果 |
  |---|---|---|---|---|
  | 01 | DSR | Deflated Sharpe · 扣 150 trials · 閾值 2.0 | SR̂ 2.41 → DSR 12.12 · p ≪ 0.001 | PASS |
  | 02 | Worst Fold | 4 折最差 AUC > 0.60 | Fold 2 = 0.6364 | PASS |
  | 03 | Embargo | 訓練/測試需 ≥ horizon 日 purge + embargo | D+20 → 20 日 | PASS |
  | 04 | Leakage Scan | 逐特徵掃 shift + label overlap | 0 / 91 detected | PASS |
  | 05 | PSI (drift) | Basel III FRTB · 0.10 amber / 0.25 red | Max 0.13 (txt) | **PASS · WARN** |
  | 06 | KS Test | 訓練 vs 測試 · p > 0.01 | min p = 0.037 | PASS |
  | 07 | Lineage | 每特徵可回 SQL · YAML + commit hash | 91 / 91 | PASS |
  | 08 | Reproducibility | 相同 seed + commit · 3 獨立 runs | SD < 1e-6 | PASS |
  | 09 | Sign-off | 資料科學 + 業務 + 合規三方 | 2026-04-19 完成 | PASS |
- **col-2 · 左欄**「PSI 支柱漂移監測」迷你 hbar（mono）
  | Pillar | PSI |
  |---|---:|
  | trend | 0.04 |
  | fund | 0.03 |
  | val | 0.05 |
  | risk | 0.06 |
  | sent | 0.09 |
  | **txt ★** | **0.13**（橘） |
  - chart-note：`Basel III FRTB · amber @ 0.10 · red @ 0.25 · txt 漂移源於 2024-Q4 deepseek / 矽光子 / CoWoS 新詞自然演化`
- **右欄 takeaway-bar**：`Why warn, not fail?` · Text PSI 0.13 為**語言自然演化** · ① 每月重訓詞向量 · ② 每季檢視 keyword whitelist · ③ 監控 coverage rate >10% 即觸發全面重訓
- footer：`phase6_gates.json · PSI 自建 bin-boundary stable 計算`

---

### Slide 29 · 三項落地建議（Recommendations）

- chrome：`Recommendations | 29`
- eyebrow：`Roadmap · 三項落地建議`
- H1：`下一階段建議 三項行動` ↵ `從 Research 走向 Production 的最小可行路徑`
- **col-3 · 三張大型 rec-card（min-height 420 px）**
  | # | 顏色 | 標題 | Pill |
  |---|---|---|---|
  | 01 navy | navy | **每日 Top 1% 清單服務化** · REST API 提供 4–8 檔候選 + 預測機率 + Risk + 文本情緒象限三維標籤 | COMMERCIALIZATION |
  | 02 橘 | 橘 | **Risk 支柱獨立風控 overlay** · 將 rv_20d / downside_dev / beta 封為獨立模組，作為其他策略的倉位上限 | RISK MODULE |
  | 03 rose | rose | **Text 模組獨立治理 pipeline** · 每月詞向量重訓 + 每季 keyword spectrum 審核 | DRIFT GOVERNANCE |
  - 每張卡內含 stack-6 三條：時程 / 投入 / 產出
    - 01：2026-Q2 POC · Q3 試運行 / 1 工程 FTE + 雲端 NTD 40k / edge +10.54 pp 預測清單
    - 02：2026-Q2 內部部署 / 0.5 研究員 FTE · 無硬體 / 每檔每日 risk score 0–1
    - 03：2026-Q3 建置 · Q4 全面上線 / 1 NLP 研究員 FTE · 每月 cron / 每月 txt refresh + PSI 自動回報
- takeaway-bar：`Sequencing Logic` · 優先序 **①商業化 → ②風控擴散 → ③ NLP 治理** · 前兩項可 2026-Q2 並行 · 三項完成後具備「輸出 + 擴散 + 自我維護」三層能力
- footer：`Team: 台股多因子 Research Group · 資源試算基於 NTU-GSA 2026 內部報價`

---

### Slide 30 · 結語（Closing · 編輯型 Thank You）

- chrome：`Closing | 30`
- 背景：兩層 radial 漸層（teal 92% 10% / navy 5% 100%）+ ivory→white→ice 線性漸層 + 80 px mask 網格
- 開頁 mono eyebrow（teal 14 px / 16% letter-spacing / 大寫）：`Thank you · 提問與討論`
- **超大型 H1（88 px / 800 / navy）三行**：
  - `嚴格的時序紀律`
  - `加上 9 支柱因子棋盤`（後段 teal）
  - `讓台股預測 可驗證 · 可重現 · 可落地`（後段 emerald）
- **段落 26 px / max-width 1400**：「本系統以 1,930 檔 × 948,976 樣本淬煉 91 個預測特徵，於 Walk-Forward Purged K-Fold + 20 日 embargo 下取得 OOS AUC 0.6490、ICIR 0.7431、DSR 12.12；Top 0.1% 命中率 45.79%（+19.52 pp edge），9 道治理閘門全數通過。」
- 附錄導引（mono · 14 px · ink-3 · letter-spacing .06em）：
  > `APPENDIX → P.31 SHAP × LOPO 診斷 · P.32 回測權益曲線 × 成本敏感度 · P.33 研究限制與 Future Work · P.34 12 篇學術參考文獻`
- **底部 4 欄 KPI**（mono 40 px）：
  - OOS AUC (D+20)：`0.6490`（teal）
  - ICIR / DSR：`0.74 / 12.12`（navy）
  - TOP 0.1% HIT：`45.79%`（navy）
  - GATES：`9 / 9`（teal）
- 頁尾 disclaimer：`本系統為課程專案成果，不構成任何投資建議 · © 2026 台股多因子 Research Group` + 7-i band（最後一格 teal）

---

### Slide 31 · 附錄 A · SHAP + ICIR 模型診斷

- chrome：`Appendix A · SHAP + ICIR | 31`（左 brand mark 改 rose 漸層 `APX 附錄 A · 模型診斷`）
- eyebrow：`Appendix A · Model Diagnostics`（rose）
- H1：`SHAP Top-20 特徵重要性 對齊 LOPO 支柱排序` ↵ `Risk / Trend 族群主導，前 20 特徵累計 SHAP 占 68.4%`
- **col-2 · 左欄**「SHAP mean(｜value｜) · Top 20 features」（4 欄 grid · # / Feature / Pillar / |SHAP|）
  | # | Feature | Pillar | ｜SHAP｜ |
  |---:|---|---|---:|
  | 01 | rv_20d_zscore | risk | 0.0812 |
  | 02 | downside_dev_20d | risk | 0.0714 |
  | 03 | mom_60d_rank | trend | 0.0681 |
  | 04 | beta_60d | risk | 0.0603 |
  | 05 | ma_gap_20d | trend | 0.0571 |
  | 06 | atr_20d_pct | risk | 0.0554 |
  | 07 | rsi_14d | trend | 0.0518 |
  | 08 | pb_decile | val | 0.0492 |
  | 09 | mom_120d_rank | trend | 0.0471 |
  | 10 | max_drawdown_60d | risk | 0.0443 |
  | 11 | bull_keyword_lift | txt | 0.0418 |
  | 12 | roe_ttm | fund | 0.0394 |
  | 13 | vol_ratio_5d_60d | risk | 0.0371 |
  | 14 | news_consensus_q | txt | 0.0349 |
  | 15 | sent_quintile_contra | sent | 0.0326 |
  | 16 | per_ttm_decile | val | 0.0308 |
  | 17 | mom_5d_reversal | trend | 0.0291 |
  | 18 | rev_growth_yoy_rank | fund | 0.0273 |
  | 19 | forum_heat_z | txt | 0.0256 |
  | 20 | ma_cross_signal | trend | 0.0241 |
- **col-2 · 右欄 table.ct**「支柱 SHAP 份額 vs LOPO 一致性」
  | 支柱 | SHAP 份額 | LOPO bps | 一致性 |
  |---|---:|---:|---|
  | **risk** ★ | 29.8% | +138.6 | ★★★ |
  | trend | 27.4% | +64.9 | ★★★ |
  | val | 11.2% | +9.5 | ★★ |
  | txt | 10.3% | +8.5 | ★★ |
  | fund | 8.7% | −2.6 | ★ |
  | sent | 6.1% | −2.8 | ★ |
  | chip / event / ind | 6.5% | −49.0 | — |
  - fn 註：「★★★ SHAP 大 + LOPO 正 · ★★ 中度 · ★ 待重構 · — 候選刪除」
  - takeaway-bar：`Risk × Trend × Text 三元協同` · 前 20 特徵 9/20 risk · 6/20 trend · 3/20 txt · SHAP 份額與 LOPO bps Spearman ρ = **0.82**
- footer：`outputs/reports/shap_top20_D20.json · lopo_pillar_contribution_D20.json · Lundberg & Lee (NeurIPS 2017)`

---

### Slide 32 · 附錄 B · 績效深度 Backtest + Cost Sensitivity

- chrome：`Appendix B · Backtest & Cost | 32`（rose APX）
- eyebrow：`Appendix B · Backtest Deep Dive`（rose）
- H1：`Top 0.1% 等權月度再平衡 · 2023-03 ~ 2025-03` ↵ `累積報酬 +68.4% · MDD −12.7% · Calmar 2.34`
- **col-2 · 左欄 · 權益曲線 SVG（600 × 240）**
  - 兩條曲線：實線藍 = 策略（含 fill 漸層 #stratFill）／虛線 navy = 0050 ETF
  - MDD 標註點（rose 圓點）：`MDD −12.7% (2024-06)`
  - 軸：y 1.0 / 1.25 / 1.50 / 1.75；x 23-03 / 24-03 / 24-09 / 25-03
  - fn：「假設：每月底以當月 Top 0.1%（≈ 2 檔）等權持有 · 月末再平衡 · 交易成本 20 bps round-trip · 不含除權息」
  - **下方 4 個 stat-hero**（28 px 數字）：
    - `+68.4%`（橘） 累積報酬 24m
    - `−12.7%`（rose） Max Drawdown
    - `2.34` Calmar Ratio
    - `1.87`（emerald） Sharpe (net)
- **col-2 · 右欄 · table.ct**「交易成本敏感度 · 三情境壓力測試」
  | 情境 | round-trip cost | Sharpe | CAGR | MDD | 結論 |
  |---|---:|---:|---:|---:|---|
  | 零成本 (理想) | 0 bps | 2.14 | +34.1% | −9.8% | — |
  | **基準 (現實)** ★ | 20 bps | **1.87** | **+29.8%** | −12.7% | OK |
  | 悲觀 (壓力) | 50 bps | 1.42 | +22.4% | −16.9% | WARN |
  | 極端 (崩潰) | 100 bps | 0.68 | +11.2% | −22.1% | FAIL |
  - fn：「round-trip cost = 手續費 + 證交稅 + slippage · 台股散戶現行 ≈ 14.25 bps · 本系統 20 bps 為保守設定」
  - **下方額外段**「流動性過濾與容量估算 · Grinold-Kahn Capacity Curve」（橘背景 / 左 4 px 橘條）
    - ① 流動性閾值：排除 20 日均成交額 < NT$1 億（影響 ≈ 18% 樣本）
    - ② 部位上限：單檔 ≤ 0.5% 當日成交額，避免滑價 > 30 bps
    - ③ 策略容量：估計 **NT$ 5–8 億** 內 alpha 不衰減
    - 註：依 Grinold & Kahn (2000) Active Portfolio Management §16 擁擠度模型，alpha decay = f(AUM/ADV)²
  - takeaway-bar：`100 bps 是損益平衡點` · ≤ 100 bps 仍 Sharpe > 0.6 · CAGR > 10% · 機構（5–15 bps）獲利空間最大、散戶（14–25 bps）為基準
- footer：`outputs/reports/backtest_top001_D20.json · 交易成本依台股 2026-04 現行稅率 + 摩擦估算`

---

### Slide 33 · 附錄 C · 研究限制與 Future Work

- chrome：`Appendix C · Limitations | 33`（rose APX）
- eyebrow：`Appendix C · Limitations & Future Work`（rose）
- H1：`本研究的 5 項限制 與對應的 5 項下階段研究` ↵ `學術誠信揭露 · 避免過度宣稱`
- **col-2 · 左欄（rose 警示卡 × 5）**「⚠ 研究限制 Limitations」
  | 編號 | 限制 | 內文 |
  |---|---|---|
  | L1 | 時間範圍有限 | 僅 2023-03 ~ 2025-03（24 個月）· 後 COVID + AI 題材輪動，**未含完整景氣循環**（需 ≥ 60 個月） |
  | L2 | 市場單一性 | 僅驗證台股（TWSE + OTC 1,932 檔）· 跨市場（美 / 港 / 日）尚待實證 |
  | L3 | 預測視域單一 | 主測 D+20 · D+1 / D+5 / D+60 未完整評估 |
  | L4 | 文本語料偏差 | 新聞 + PTT · 未含法說會逐字稿、分析師報告、外資研究 → txt PSI 0.13 警示反映此維度 |
  | L5 | 執行假設理想化 | 收盤價可完全成交 · 未模擬 TWAP / VWAP 滑價；容量 5–8 億為模擬估算 |
- **col-2 · 右欄（emerald 卡 × 5）**「→ 下階段研究 Future Work」
  | 編號 | 主題 | 內文 |
  |---|---|---|
  | F1 | 延伸至完整景氣循環 | 補齊 2018–2022（COVID 熊市 + 2022 升息）· 預計 2026-Q3 完成跨循環 AUC 穩定性 |
  | F2 | 跨市場遷移學習 | 9 支柱遷移至日股（TSE Prime 225）、港股（恆指）· domain adaptation 因子權重差異 |
  | F3 | 多視域聯合建模 | multi-task XGBoost 同時預測 D+1 / D+5 / D+20 共享低層表徵 |
  | F4 | 引入 LLM 語料 | 整合法說會逐字稿 + 分析師報告 · LLM 抽情緒向量取代詞袋 lift |
  | F5 | 實盤 A/B 驗證 | NT$ 500 萬 · 6 個月小額實盤 · 實測 TWAP/VWAP 滑價 + 資訊延遲衝擊 |
- footer：`學術誠信揭露 · 避免以單一樣本期間過度宣稱 · 依 CFA Institute GIPS 2020 回測標準自評`

---

### Slide 34 · 附錄 D · 參考文獻 Bibliography（15 篇）

- chrome：`Appendix D · Bibliography | 34`（rose APX）
- eyebrow：`Appendix D · Bibliography`（rose）
- H1：`本研究的 15 篇核心文獻` ↵ `涵蓋時序方法論、行為金融、NLP 情緒、機器學習可解釋性`
- **col-2 · 左欄**
  - **① 時序方法論 · Time-Series Methodology**
    - [1] López de Prado, M. (2018). *Advances in Financial Machine Learning.* Wiley. （§7.4 Purged K-Fold · §11 backtest overfitting）
    - [2] Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio. *JPM*, 40(5), 94–107.
    - [3] Harvey, C. R., Liu, Y., & Zhu, H. (2016). …and the Cross-Section of Expected Returns. *RFS*, 29(1), 5–68. （多重檢定下因子可信度）
    - [13] Grinold, R. C., & Kahn, R. N. (2000). *Active Portfolio Management* (2nd). McGraw-Hill. （§16 容量／擁擠度 · P.32 引用）
  - **② 行為金融 · Behavioral Finance**
    - [4] Baker, M., & Wurgler, J. (2006). Investor Sentiment and the Cross-Section of Stock Returns. *JF*, 61(4).
    - [5] Tetlock, P. C. (2007). Giving Content to Investor Sentiment: The Role of Media. *JF*, 62(3), 1139–1168.
    - [6] Barber, B. M., & Odean, T. (2008). All That Glitters: …Attention and News. *RFS*, 21(2), 785–818.
- **col-2 · 右欄**
  - **③ NLP & 文本情緒 · Text Analytics**
    - [7] Loughran, T., & McDonald, B. (2011). When Is a Liability Not a Liability? *JF*, 66(1), 35–65. （金融 lexicon）
    - [8] Ke, Z. T., Kelly, B. T., & Xiu, D. (2019). Predicting Returns with Text Data. *NBER WP No. 26186.* （lift / SEE 啟發）
    - [9] Jegadeesh, N., & Wu, D. (2013). Word Power. *JFE*, 110(3), 712–729.
    - [14] Jiang, F., Lee, J., Martin, X., & Zhou, G. (2019). Manager Sentiment and Stock Returns. *JFE*, 132(1). （華語延伸）
  - **④ 機器學習與可解釋性 · ML & XAI**
    - [10] Chen, T., & Guestrin, C. (2016). XGBoost. *KDD 2016*, 785–794.
    - [11] Lundberg, S. M., & Lee, S.-I. (2017). A Unified Approach to Interpreting Model Predictions. *NeurIPS 2017.* （SHAP 源頭）
    - [12] Gu, S., Kelly, B., & Xiu, D. (2020). Empirical Asset Pricing via Machine Learning. *RFS*, 33(5). （多因子 ML 標竿）
    - [15] Guyon, I., & Elisseeff, A. (2003). Variable and Feature Selection. *JMLR*, 3, 1157–1182. （MI + Lasso + SHAP 取捨）
- takeaway-bar：`引用規範` · 所有統計方法、因子建構、NLP 情緒、ML 可解釋性均可追溯至上述 15 篇頂級期刊；APA 7th；報告以 [編號] 交叉引用
- footer：`Academic Integrity · 本專案所有方法皆可回溯至頂級期刊同儕審查文獻 · 無未註明之原創假設`

---

## 3. 設計觀察 · 給 Claude Design 的優化提示

### 3.1 目前簡報的長處（請保留）

1. **管顧型敘事節奏**：每頁固定「eyebrow → H1（含 hl 高亮）→ rule-divider → body → takeaway-bar → source」六段，視覺與認知都很穩。
2. **數字資產豐富**：48 個 KPI 數字 / 9 個 hbar 排行榜 / 6 張 table.ct / 5 張 SVG 圖（門檻掃描、U-shape、Top-N 柱、Walk-Forward fold、權益曲線）。
3. **章節分隔頁有節奏感**：6 個 section-divider 用亮色 cream 漸層 + radial 光暈 + 網格 mask，與內頁的純白形成節律。
4. **色彩語意一致**：navy = 主色 / teal = 強調 / rose = 警示或第一名 / emerald = 通過 / 橘藍互換系統明確。
5. **Appendix 視覺差異化**：APX brand mark 改 rose 漸層、進度燈最後一格 rose、eyebrow 也變 rose，明確標示「離開正文」。

### 3.2 可以再加強的地方（建議 Claude Design 探索）

| # | 觀察 | 優化方向 |
|---|---|---|
| 1 | **封面 H1 108 px 與內頁 H1 56 px 落差略大**，可增加一張過場頁緩衝 | 在封面與 Slide 02 之間加一張「研究地圖縮圖」過場 |
| 2 | **Slide 02 Executive Summary 資訊密度偏高**（4 hero + 6 段內文 + takeaway） | 拆成「Findings」「Recommendations」兩頁，或用 sticky `bottom-0` 摘要欄 |
| 3 | Slide 11「9 支柱總覽」**九色彩虹略雜** | 可保留 navy / teal / rose / emerald 四色為主色，其他 5 個改為深淺差異 |
| 4 | Slide 16 Walk-Forward fold 圖目前用 `<div>` 拼接 | 升級為 SVG 帶刻度與 hover annotation（D+20 horizon 視覺化） |
| 5 | Slide 20 / 21 / 25 / 32 都有 inline SVG，**樣式不完全一致** | 統一成「白底 + e2e8f0 邊框 + 4 px 圓角 + 18 px 內邊距 + JetBrains Mono 註解」 |
| 6 | Slide 28 治理閘門表 9 列字級偏小（15.5 px） | 重排成「3×3 status grid」或分成兩張：閘門表格 + PSI 漂移視覺 |
| 7 | Slide 30 Closing 三行 H1 與 4 KPI 切分稍弱 | 加上「下一步行動」CTA pill 或團隊照／Logo 區 |
| 8 | Appendix 31 SHAP Top-20 用 grid 4 欄密集呈現 | 可加上微型 inline bar 視覺化每行 ｜SHAP｜ 大小 |
| 9 | takeaway-bar 全簡報出現 25 次，**每張色塊一致** | 可分 3 種：teal（觀察）/ navy（決策）/ rose（警示），讓資訊層次更分明 |
| 10 | 目前**沒有 dashboard 截圖頁**作為交付證據 | 建議在 Section 7 補一張「13 頁 Dashboard 導覽縮圖」 |

### 3.3 維持的設計憲法

- **柵格**：1920 × 1080 認證稿；左右 96 px / 上下 72 px padding；網格 8 px。
- **字級階梯**：56 / 42 / 32 / 26 / 22 / 18 / 17 / 16 / 14 / 13 / 12 / 11.5（mono）；不要新增中間層級。
- **顏色**：所有強調色限定於 `navy / teal / rose / emerald / orange-as-blue / violet / cyan / gold` 8 色；新增色須先進入 `:root` token。
- **資料來源**：每張頁的 `slide-foot .source` 必填且 mono；URL/JSON 名不可省。
- **進度燈 band**：每張內頁最後 7-i band 對應當前章節，附錄改 rose `i.on`。
- **不破壞**：`<deck-stage>` 1920 × 1080 的子節點獨立性；任何優化都應保持 1 section = 1 slide 的可讀性。

---

## 4. 對 Claude Design 的具體請求建議

> 把這份 markdown 連同目前的單檔 HTML 一起送進 Claude Design，可以提的請求例：

1. **重排版 Slide 02 / 11 / 28**：依 §3.2 表中第 2 / 3 / 6 點重新分配資訊密度。
2. **統一 inline SVG 樣式**：把 5 張 SVG（門檻、U-shape、Top-N、權益、 fold 圖）統一為共用視覺元件 + 圖例 token。
3. **新增 1–2 張過場 / Dashboard 縮圖頁**：補齊敘事節奏。
4. **takeaway-bar 三色化**：依語意分流為 observation / decision / warning。
5. **Appendix 31 SHAP 條微型化**：在每行右側加上 inline bar 視覺化 ｜SHAP｜。

> 任何重排版請保留：① 原始 KPI 數字（不可改數）② source 的 JSON 來源 ③ 7 章節結構與進度燈。

---

*— 以上為 v11.5.17 簡報的完整內容描述 · 可作為 Claude Design 進一步視覺優化的單一輸入檔。*
