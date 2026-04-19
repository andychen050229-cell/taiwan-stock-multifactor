# Phase 4 架構設計 — 基本面深化 × Market Regime 強化

> 版本：2026-04-07
> 狀態：規劃中
> 發起人：林芮靚建議 → 團隊討論 → 架構設計

---

## 0. 設計動機

### 0.1 現狀分析

目前系統五支柱特徵共 43 個候選因子，經 MI + VIF 三階段篩選後保留 21 個。

**Pillar 2 基本面（10 個候選 → 7 個入選）**：
全部來自損益表（Income Statement），涵蓋營收、毛利率、營益率、淨利率、營收 YoY、EPS YoY。

**Pillar 3 估值（2 個候選 → 2 個入選）**：
僅有 P/E 和 P/E 分位數。

**Pillar 5 風險（3 個候選 → 2 個入選）**：
`risk_drawdown` + `risk_market_ret_20d` 入選。`risk_volatility_regime` 因與波動度特徵共線被 VIF 移除。

### 0.2 不足之處

| 維度 | 缺口 | 影響 |
|------|------|------|
| 資本效率 | 無 ROE / ROIC / ROAE | 無法衡量公司用股東資金賺錢的效率 |
| 價值創造 | 無 EBITDA → NOPAT 鏈 | 無法判斷公司是否真正創造超額報酬 |
| 資本結構 | 無 D/E / WACC / CoE | 無法區分高槓桿暴利 vs 穩健獲利 |
| 多元估值 | 僅 P/E | 遺漏 P/B, P/S, EV/EBITDA 等互補視角 |
| 市場狀態 | regime 特徵被 VIF 淘汰 | 模型無法在不同市況下調適預測邏輯 |

---

## 1. 新增資料來源

### 1.1 FinMind API 擴充

需要新增兩張資料表，皆可透過 FinMind 免費 API 取得：

| 資料表 | FinMind dataset | 資料起始 | 說明 |
|--------|----------------|---------|------|
| 資產負債表 | `TaiwanStockBalanceSheet` | 2008-06 | date, stock_id, type, value, origin_name |
| 現金流量表 | `TaiwanStockCashFlowsStatement` | 2005-05 | date, stock_id, type, value, origin_name |

**資料格式**：FinMind 財報 API 回傳的是「長格式」（long format），每筆記錄代表一個科目：

```
date         stock_id  type                     value        origin_name
2024-03-31   2330      TotalAssets              4500000000   資產總額
2024-03-31   2330      StockholdersEquity       3200000000   股東權益總額
```

需要 pivot 成寬格式後才能使用。

### 1.2 必要科目對照表

**資產負債表（計算 ROE / ROIC / P/B / D/E / WACC 所需）**：

| IFRS 科目 type | 中文名稱 | 用途 |
|----------------|---------|------|
| `StockholdersEquity` | 股東權益總額 | ROE 分母、P/B 分母 |
| `TotalAssets` | 資產總額 | 資產報酬率、資本效率 |
| `TotalLiabilities` | 負債總額 | D/E 比、WACC |
| `LongTermBorrowings` | 長期借款 | 有息負債、WACC |
| `ShortTermBorrowings` | 短期借款 | 有息負債、WACC |
| `CurrentAssets` | 流動資產 | 淨營運資金 |
| `CurrentLiabilities` | 流動負債 | 淨營運資金 |

**現金流量表（計算 EBITDA 近似值所需）**：

| IFRS 科目 type | 中文名稱 | 用途 |
|----------------|---------|------|
| `DepreciationExpense` | 折舊費用 | EBITDA = 營業利益 + D&A |
| `AmortizationExpense` | 攤銷費用 | EBITDA = 營業利益 + D&A |

### 1.3 PIT 一致性

資產負債表與現金流量表的申報期限與損益表完全相同（同一份季報），因此可共用現有的 `PIT_DEADLINES` 設定：

```python
PIT_DEADLINES = {
    1: {"month": 5, "day": 15},    # Q1 → 5/15
    2: {"month": 8, "day": 14},    # Q2 → 8/14
    3: {"month": 11, "day": 14},   # Q3 → 11/14
    4: {"month": 3, "day": 31, "next_year": True},  # Q4 → 隔年 3/31
}
```

---

## 2. 新增特徵設計

### 2.1 Pillar 2 基本面深化（+10 個特徵）

#### A. 資本效率指標

| 特徵名 | 公式 | 說明 |
|--------|------|------|
| `fund_roe_sq` | net_income_sq / avg(stockholders_equity) | 股東權益報酬率（單季年化） |
| `fund_roa_sq` | net_income_sq / avg(total_assets) | 資產報酬率 |
| `fund_roic_sq` | NOPAT_sq / invested_capital | 投入資本報酬率 |

**計算細節**：
- `avg()` = (期初 + 期末) / 2，避免時點偏誤
- `NOPAT_sq` = operating_income_sq × (1 - effective_tax_rate)
- `effective_tax_rate` = 1 - (net_income_sq / operating_income_sq)，clip 至 [0, 0.5]
- `invested_capital` = stockholders_equity + long_term_borrowings + short_term_borrowings - cash

#### B. 獲利品質鏈（EBITDA → NOPAT）

| 特徵名 | 公式 | 說明 |
|--------|------|------|
| `fund_ebitda_sq` | operating_income_sq + depreciation + amortization | 稅息折舊攤銷前利潤 |
| `fund_ebitda_margin_sq` | ebitda_sq / revenue_sq | EBITDA 利潤率 |
| `fund_nopat_sq` | operating_income_sq × (1 - eff_tax_rate) | 稅後營業淨利 |

**注意**：若現金流量表中折舊攤銷取得困難，可退而求其次用 `operating_income_sq` 近似（已有），並在文件中標注。

#### C. 資本結構

| 特徵名 | 公式 | 說明 |
|--------|------|------|
| `fund_debt_equity` | total_liabilities / stockholders_equity | 負債權益比 |
| `fund_current_ratio` | current_assets / current_liabilities | 流動比率（短期償債能力） |

#### D. 效率變化率

| 特徵名 | 公式 | 說明 |
|--------|------|------|
| `fund_roe_yoy` | (roe_sq - roe_sq_去年同季) / abs(roe_sq_去年同季) | ROE 年增率 |
| `fund_ebitda_yoy` | (ebitda_sq - ebitda_sq_去年同季) / abs(ebitda_sq_去年同季) | EBITDA 年增率 |

### 2.2 Pillar 3 估值擴充（+3 個特徵）

| 特徵名 | 公式 | 說明 |
|--------|------|------|
| `val_pb` | closing_price / (stockholders_equity / shares_outstanding) | 股價淨值比 |
| `val_ps` | closing_price × shares_outstanding / revenue_sq_annualized | 股價營收比 |
| `val_ev_ebitda` | (market_cap + total_liabilities - cash) / ebitda_annualized | 企業價值倍數 |

**注意**：`shares_outstanding` 需從 companies 表取得或從資產負債表反推。若無法取得，`val_pb` 可用 `market_cap / stockholders_equity` 替代。

### 2.3 Pillar 5 Market Regime 強化（+3 個特徵）

#### 問題回顧
現有 `risk_volatility_regime` 因與 `trend_volatility_60` 高度共線，在 VIF 篩選被移除。

#### 設計策略：降低與現有技術面特徵的共線性

| 特徵名 | 公式 | 說明 |
|--------|------|------|
| `risk_regime_composite` | f(market_ret_60d, vol_ratio, breadth) | 多維度複合 regime 指標 |
| `risk_market_breadth` | 上漲家數 / 全部家數（20日滾動） | 市場廣度（與個股波動度正交性高） |
| `risk_vol_term_structure` | volatility_20 / volatility_60 | 波動率期限結構（短/長波動比） |

**`risk_regime_composite` 設計**：

```python
# 三維度等權合成，每個維度先做 0-1 標準化
market_trend  = rank_pct(market_ret_60d)      # 大盤趨勢
market_breadth = rank_pct(advance_ratio_20d)  # 市場廣度
vol_regime    = 1 - rank_pct(vol_60)          # 波動率（反向：低波 = 高分）

regime_composite = (market_trend + market_breadth + vol_regime) / 3
# 分位分類：
# >= 0.67 → Bull (2)
# 0.33~0.67 → Neutral (1)
# < 0.33 → Bear (0)
```

**為何這樣設計**：
- `risk_volatility_regime` 之所以被 VIF 淘汰，是因為它本質上只是 `trend_volatility_60` 的分位化版本
- 複合指標加入了「市場廣度」和「大盤趨勢」兩個維度，與個股技術面指標的相關性大幅降低
- 波動率期限結構（`vol_term_structure`）捕捉的是「短期恐慌 vs 長期趨勢」的關係，不是絕對波動度水準

---

## 3. 程式碼修改計畫

### 3.1 新增檔案

```
src/data/balance_sheet_processor.py    # 資產負債表處理（pivot + PIT + 品質檢查）
src/data/cashflow_processor.py         # 現金流量表處理（pivot + PIT）
scripts/fetch_balance_sheet.py         # FinMind 資產負債表抓取腳本
scripts/fetch_cashflow.py              # FinMind 現金流量表抓取腳本
```

### 3.2 修改檔案

| 檔案 | 修改內容 |
|------|---------|
| `src/config/base.yaml` | 新增 `balance_sheet` 和 `cashflow` 資料表設定 |
| `src/data/loader.py` | 新增 `load_balance_sheet()` 和 `load_cashflow()` 方法 |
| `src/data/financial_processor.py` | 新增 `run_balance_sheet_pipeline()` 函式 |
| `src/features/engineer.py` | Pillar 2 新增 ROE/ROIC/EBITDA 特徵、Pillar 3 新增 P/B/P/S/EV_EBITDA、Pillar 5 新增複合 regime |
| `run_phase1.py` | 加入資產負債表 + 現金流量表處理步驟 |
| `run_phase2.py` | 傳入擴充後的財務資料（無需改模型邏輯） |
| `dashboard/pages/4_🔬_Feature_Analysis.py` | 更新五支柱說明文字 |
| `dashboard/pages/5_🗃️_Data_Explorer.py` | 新增資產負債表/現金流量表資料概覽 |

### 3.3 base.yaml 新增設定

```yaml
data:
  tables:
    # 現有
    companies: "companies.parquet"
    stock_prices: "stock_prices.parquet"
    income_stmt: "income_stmt.parquet"
    stock_text: "stock_text.parquet"
    # Phase 4 新增
    balance_sheet: "balance_sheet.parquet"
    cashflow: "cashflow.parquet"
```

---

## 4. 執行步驟

### Step 1：資料抓取（新增）

```
1a. 撰寫 scripts/fetch_balance_sheet.py
    - 使用 FinMind API: dataset=TaiwanStockBalanceSheet
    - 與現有 抓取OHLCV資料.py 相同的批次架構（斷點續傳、rate limit）
    - 日期範圍：2023-03-01 ~ 2025-03-31
    - 輸出：選用資料集/parquet/balance_sheet.parquet

1b. 撰寫 scripts/fetch_cashflow.py
    - 使用 FinMind API: dataset=TaiwanStockCashFlowsStatement
    - 同上批次架構
    - 輸出：選用資料集/parquet/cashflow.parquet
```

### Step 2：資料處理（新增 + 修改）

```
2a. 撰寫 src/data/balance_sheet_processor.py
    - long → wide pivot（type → 欄位名）
    - 型別轉換
    - fiscal_year / fiscal_quarter 推算（從 date 欄位）
    - PIT 日期估算（共用 PIT_DEADLINES）
    - 品質檢查

2b. 修改 src/data/loader.py
    - 新增 load_balance_sheet() / load_cashflow()

2c. 修改 run_phase1.py
    - Step 3.5: 資產負債表處理
    - Step 3.6: 現金流量表處理
    - 合併至同一份品質報告
```

### Step 3：特徵工程擴充

```
3a. 修改 src/features/engineer.py
    - build_fundamental_features() 擴充：接受 balance_sheet_df 參數
    - 新增 ROE/ROA/ROIC/EBITDA/NOPAT/D_E/current_ratio 計算
    - build_valuation_features() 擴充：P/B, P/S, EV/EBITDA
    - build_risk_features() 擴充：regime_composite, market_breadth, vol_term_structure

3b. 修改 src/config/base.yaml
    - features.pillars 更新特徵列表說明
```

### Step 4：重跑 Phase 1 → 2 → 3

```
4a. python run_phase1.py    # 重建 feature_store（含新特徵）
4b. python run_phase2.py    # 重新訓練 + 篩選（MI/VIF 會重新決定哪些特徵入選）
4c. python run_phase3.py    # 重跑治理
4d. python scripts/build_recommendations.py  # 重建推薦資料
```

### Step 5：儀表板更新

```
5a. 更新 Feature Analysis 頁的五支柱說明
5b. 更新 Data Explorer 頁的資料來源文件
5c. 更新 README 的特徵列表
```

---

## 5. 特徵候選清單（Phase 4 全覽）

### 新增 16 個特徵

| # | 支柱 | 特徵名 | 資料需求 | 優先級 |
|---|------|--------|---------|--------|
| 1 | Fund | `fund_roe_sq` | 資產負債表 | 高 |
| 2 | Fund | `fund_roa_sq` | 資產負債表 | 高 |
| 3 | Fund | `fund_roic_sq` | 資產負債表 + 損益表 | 高 |
| 4 | Fund | `fund_ebitda_sq` | 現金流量表 + 損益表 | 高 |
| 5 | Fund | `fund_ebitda_margin_sq` | 同上 | 中 |
| 6 | Fund | `fund_nopat_sq` | 損益表 | 中 |
| 7 | Fund | `fund_debt_equity` | 資產負債表 | 高 |
| 8 | Fund | `fund_current_ratio` | 資產負債表 | 中 |
| 9 | Fund | `fund_roe_yoy` | 資產負債表 | 中 |
| 10 | Fund | `fund_ebitda_yoy` | 現金流量表 + 損益表 | 中 |
| 11 | Val | `val_pb` | 資產負債表 | 高 |
| 12 | Val | `val_ps` | 損益表 | 中 |
| 13 | Val | `val_ev_ebitda` | 資產負債表 + 現金流量表 | 高 |
| 14 | Risk | `risk_regime_composite` | 既有股價資料 | 高 |
| 15 | Risk | `risk_market_breadth` | 既有股價資料 | 高 |
| 16 | Risk | `risk_vol_term_structure` | 既有股價資料 | 中 |

Phase 4 完成後：**43 + 16 = 59 個候選特徵** → MI + VIF 篩選 → 預估 25-30 個入選

---

## 6. 風險與注意事項

### 6.1 資料品質風險

- FinMind 資產負債表的 `type` 欄位名稱可能因 IFRS 版本更迭而不一致，需建立映射表
- 小型公司可能缺少部分科目（如長期借款），需設計 fallback 邏輯
- 現金流量表的折舊攤銷可能合併報告，需支援 `DepreciationAndAmortization` 合併欄位

### 6.2 PIT 洩漏風險

- 資產負債表和損益表同屬一份季報，PIT 日期一致 → 不會產生新的洩漏風險
- 但 `fund_roe_sq` 使用「平均股東權益」時，需確保期初值也已過 PIT 門檻

### 6.3 共線性風險

- 新增 10 個基本面特徵可能與現有 margin 指標高度相關
- ROE ≈ net_margin × asset_turnover × equity_multiplier（杜邦分解）
- VIF 篩選會自動處理，但預期部分 margin 指標可能被新指標替代

### 6.4 Market Regime 特徵的前視偏誤

- `risk_market_breadth` 使用**當日**全市場漲跌家數，這是當日收盤後才完整可知的資訊
- 需使用 **T-1 日**的市場廣度作為 T 日特徵，避免前視偏誤
- `risk_regime_composite` 同理，所有成分都使用滯後一日的值

---

## 7. CoE / WACC 評估（暫不實作）

林芮靚提到的 CoE（Cost of Equity）和 WACC（Weighted Average Cost of Capital）：

**CoE 計算需要**：
- 無風險利率（台灣十年期公債殖利率）→ 需額外資料源（央行或 TEJ）
- 個股 Beta → 需對加權指數做滾動回歸（60-120 日）
- 市場風險溢酬 → 學術估計值（約 5-7%）

**WACC 計算需要**：
- CoE + 債務成本（利息費用 / 有息負債）+ 資本結構比重

**建議**：
- Beta 和無風險利率需額外資料管線，複雜度較高
- 可在 Phase 5 考慮，或直接用 `fund_debt_equity` 作為資本結構的代理指標
- ROIC vs WACC 的「超額報酬」概念，可用 ROIC 排名作為近似

---

## 8. 預期時程

| 階段 | 工作項目 | 預估時間 |
|------|---------|---------|
| Step 1 | 資料抓取腳本 + 執行 | 1-2 小時 |
| Step 2 | 資料處理模組 | 2-3 小時 |
| Step 3 | 特徵工程擴充 | 2-3 小時 |
| Step 4 | 重跑 Phase 1-3 | 1-2 小時（含等待） |
| Step 5 | 儀表板更新 | 1 小時 |
| **總計** | | **7-11 小時** |

---

## 9. 成功指標

Phase 4 完成後，應觀察：

1. **特徵篩選變化**：新增的 ROE/ROIC/EBITDA 是否通過 MI + VIF 進入最終模型
2. **模型 AUC 變化**：比較 Phase 4 前後的 OOF AUC，預期小幅提升（0.5-2%）
3. **ICIR 變化**：新特徵是否提升信號穩定性
4. **Market Regime 存活率**：`risk_regime_composite` 是否成功通過 VIF（不再被淘汰）
5. **回測表現**：Sharpe / 最大回撤 / 超額報酬是否改善
