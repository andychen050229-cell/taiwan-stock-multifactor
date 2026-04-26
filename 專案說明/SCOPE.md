# 專案範圍紅線（SCOPE.md）

> 本文件定義「台灣股市多因子預測系統」的最終範圍邊界。
> **自 2026-04-19 起生效**，任何變更需經專案負責人書面同意。
>
> 目的：防止 scope creep，確保本專案回歸「大數據與商業分析」課堂專案的本質。

---

## 1. 資料來源紅線

### 1.1 核准資料來源（封版，不再新增）

**A. 教授提供（主資料）— `選用資料集/bda2026_backup_20260326.sql`**

| 資料表 | 用途 | 備註 |
|---|---|---|
| `companies` | 公司基本資料 | 1,932 家名單（其中 1,930 家在 2023-03 ~ 2025-03 期間有價格資料，進入 feature_store）|
| `stock_prices` | 每日收盤價 | 877,699 筆，**僅 closing_price 一欄** |
| `income_stmt` | 損益表季報 | 14,968 筆，6 個科目 |
| `stock_text` | 財經文章與新聞 | 1,125,134 篇，PTT/Dcard/Mobile01/Yahoo |

**B. FinMind 公開 API 補充（6 個封版檔案，不再增加）— `選用資料集/parquet/`**

| 檔案 | FinMind Dataset | 補充教授資料之原因 |
|---|---|---|
| `stock_prices_ohlcv.parquet` | `TaiwanStockPrice` | 教授僅提供 closing_price，補齊 OHLCV 供技術指標計算 |
| `balance_sheet.parquet` | `TaiwanStockBalanceSheet` | 教授僅提供損益表，補齊資產負債表供財務健康度分析 |
| `cashflow.parquet` | `TaiwanStockCashFlowsStatement` | 教授未提供現金流量表，補齊供現金品質分析 |
| `industry.parquet` | `TaiwanStockInfo` | 教授 `companies` 無產業欄位，補齊供產業中性化分析 |
| `institutional_investors.parquet` | `TaiwanStockInstitutionalInvestorsBuySell` | 教授未提供籌碼資料，補齊支援籌碼 pillar |
| `margin_trading.parquet` | `TaiwanStockMarginPurchaseShortSale` | **2026-04-19 下架**：覆蓋僅 58.8%（約 100 支為結構性不可下載），mg_ 支柱已停用。檔案保留作為資料透明之證明，不用於模型訓練。 |

### 1.2 禁止新增的資料來源

以下資料來源**明文禁止**引入，任何團隊成員、子 agent 均須遵守：

- ❌ **新聞爬蟲**（鉅亨、Anue、工商時報、經濟日報、聯合新聞網等）—— 教授 `stock_text` 已足夠
- ❌ **總體經濟資料**（利率、匯率、油價、DXY、VIX、美債殖利率）
- ❌ **即時報價 / 盤中資料**（tick data、分 K、逐筆交易）
- ❌ **付費情緒/輿情 API**（ThinkTech、Goodinfo、X 情緒 API）
- ❌ **國際股市資料**（費半、SOX、S&P500、道瓊）
- ❌ **衍生性商品資料**（選擇權、期貨未平倉、VIX）
- ❌ **公司治理/ESG 資料**（揭露資訊觀測站爬蟲、CSR 報告）
- ❌ **新聞圖片 / 影片 / 語音**（多模態資料）
- ❌ **FinMind 新增 endpoint**（已有 6 個封版，不再增加）

### 1.3 核准的離線模型/工具（不屬於外部資料）

以下為離線推論工具，不構成外部資料相依：

- ✅ **FinBERT 中文版**（Hugging Face 下載，本地推論）
- ✅ **jieba / monpa**（中文斷詞，本地）
- ✅ **text2vec-base-chinese**（語意嵌入，本地）
- ✅ **BERTopic + UMAP + HDBSCAN**（主題建模，本地）
- ✅ **SnowNLP**（辭典式情緒，本地）
- ✅ **Claude API / Ollama 本地 LLM**（僅限 Multi-Agent 階段使用，**禁止讓 Agent 聯網**）

---

## 2. 功能範圍紅線

### 2.1 本專案涵蓋
- 特徵工程：7 支柱（trend_/fund_/val_/event_/risk_/chip_/ind_）+ 文本三支柱（txt_/sent_/topic_）
  - **註**：原規劃 8 支柱包含 `mg_`（融資融券），已於 2026-04-19 下架。原因見 1.1 節 `margin_trading.parquet` 註記。
- 模型：LightGBM / XGBoost / CatBoost / Stacking Ensemble
- 回測：Walk-forward expanding window + embargo=20
- 決策：predict_threshold 掃描 + 出手率分析
- 視覺化：文字雲、雷達圖、熱圖、SHAP
- Case Study：3 檔代表股票深度分析
- LLM Multi-Agent（選配）：6 Agent 離線分析

### 2.2 本專案**不**涵蓋
- ❌ 實盤交易 / 下單 / 券商 API 串接
- ❌ 即時訊號推播 / 警報系統
- ❌ 券源查詢 / 借券系統
- ❌ 基金 / ETF 成份分析（本專案僅涵蓋上市上櫃個股）
- ❌ 外匯 / 加密貨幣 / 商品期貨預測
- ❌ 監管合規系統（KYC / AML）
- ❌ 客戶管理 / CRM 系統

---

## 3. 時間範圍紅線

- **資料期間**：2023-03-01 ~ 2025-03-31（依教授資料庫）
- **不做**：2025 年 4 月以後的新資料抓取、2023 年 3 月以前的回填

---

## 4. 運算資源紅線

- **不使用付費 API 消耗 token**（Claude API 若使用 Multi-Agent，以免費額度為限；或改用本地 Ollama）
- **不租用 GPU 雲端**（FinBERT 推論在本地 CPU 跑，大不了慢一點）
- **不建置 24/7 服務**（本專案為離線分析平台）

---

## 5. 變更流程

若未來確實需要突破本紅線（例：教授指定加入新資料表），須：

1. 在 `進度報告/` 下新增 `SCOPE_變更申請_YYYYMMDD.md`
2. 明確說明新增項目、原因、預期影響
3. 更新 `SCOPE.md`（本文件）的版本號
4. 在所有受影響的報告中加註「SCOPE 已於 YYYY-MM-DD 變更」

---

## 6. 版本歷史

| 版本 | 日期 | 變更 |
|---|---|---|
| v1.0 | 2026-04-19 | 初版。凍結 4 張教授表 + 6 張 FinMind 補充表。 |
