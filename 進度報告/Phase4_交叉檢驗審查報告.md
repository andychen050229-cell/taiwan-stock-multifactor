# Phase 4 完成後交叉檢驗審查報告（歷史版本）

> ⚠️ **此為 2026-04-09 的歷史審查快照。最新整合成果請參閱同資料夾下的 [`Phase4_終版綜合報告.md`](./Phase4_終版綜合報告.md)（2026-04-19 Andy）。**
>
> 自本報告發布後，Phase 1–3 已依本報告五項 Critical Bugs 建議全部修復並於 2026-04-19 以更嚴格的 PIT 路徑重跑一次，實際 OOS 績效（xgb_D20 Sharpe 0.81 / Rank IC 0.015）與本報告引用的 04-09 舊版數字（Sharpe 2.02 / IC 0.15）存在顯著落差，新版為現行交件基準。詳細對照請見終版報告第六章。

---

> 審查日期：2026-04-09  
> 審查範圍：Phase 1~3 全流程（含 BS/CF 擴充、估值因子修復）  
> 審查立場：以嚴格的團隊 Code Review 視角進行

---

## 一、整體狀態評估

| 維度 | 評級 | 說明 |
|------|------|------|
| 資料管線 | ✅ 通過 | PIT-safe merge 正確，會計方程式 PASS |
| 特徵工程 | ⚠️ 需改善 | 53 對高度共線性；估值因子計算有邏輯瑕疵 |
| 模型訓練 | ✅ 通過 | AUC 範圍合理，Walk-Forward 穩定，Permutation 全顯著 |
| 回測引擎 | ✅ 通過 | 無前瞻偏差，流動性與漲跌停過濾正確 |
| 統計驗證 | ⚠️ 部分弱 | D+1 ICIR < 0.5；Bootstrap CI 含 0 |
| 程式品質 | ⚠️ 需改善 | 3 項 Critical bugs 影響財務比率計算 |

**綜合評價：模型架構與回測邏輯健全，但財務比率計算和估值因子存在程式錯誤，修復後預期能提升模型效能。**

---

## 二、Feature Store 資料品質

### 2.1 基本統計
- 948,976 rows × 72 cols（56 個特徵 + 標籤 + meta）
- 1,930 家公司，2023-03 至 2025-03
- 無 Inf 值，無常數特徵

### 2.2 缺失值

| 前綴 | 特徵數 | NaN 平均 | NaN 最大 | 最嚴重欄位 |
|------|--------|----------|----------|-----------|
| trend_ | 25 | 1.8% | 5.9% | trend_ma_60 |
| fund_ | 18 | 17.0% | 60.7% | fund_revenue_yoy |
| val_ | 5 | 31.7% | 33.3% | val_ev_ebitda |
| event_ | 2 | 0.0% | 0.0% | — |
| risk_ | 6 | 3.3% | 4.1% | risk_regime_composite |

**審查意見：**
- fund_ 缺失率偏高源於 YoY 計算需要前一年同期數據，合理
- val_ 缺失率 ~33% 是因為需要 eps > 0 才能推算 implied shares，符合預期
- ⚠️ fund_revenue_yoy 60.7% NaN 過高，應確認是否只有 2023 年缺乏前年數據

### 2.3 高度共線性（嚴重問題）

檢測到 **53 對** |corr| > 0.95 的特徵對，包含：

- `trend_ma_10` ↔ `trend_ema_12`：r=1.000
- `fund_roe` ↔ `fund_roa`：r=1.000
- `trend_ma_20` ↔ `trend_ema_26`：r=1.000
- `fund_net_income_sq` ↔ `fund_nopat`：r=0.999

**影響：** VIF 篩選已剔除 6 個特徵（從 34 降至 28），但仍存在殘留共線性。模型解釋性受影響，但 LightGBM/XGBoost 對共線性容忍度高，不影響預測能力。

**建議：** Phase 5 前可進一步精簡 — 刪除 trend_ma_5/10（與 EMA 完全重疊）、fund_nopat（與 net_income 幾乎相同）。

### 2.4 極端值

trend_ 類特徵（MA/EMA/ATR/BB）約 0.24% 數據 |z|>10，來自高價股（如台積電），屬正常現象。模型使用的是 rank-based 特徵轉換，極端值影響有限。

### 2.5 PIT 安全性

抽查公司 9962 在 2023-03~05 的基本面特徵，跳變次數為 0（早期尚未有新季報公告），符合 PIT 邏輯。`merge_asof(direction="backward")` 確保只使用已公告數據。

---

## 三、模型效能深度審查

### 3.1 分類效能

| 模型 | D+1 AUC | D+5 AUC | D+20 AUC |
|------|---------|---------|----------|
| LightGBM | 0.6145 | 0.6415 | 0.6484 |
| XGBoost | 0.6136 | 0.6364 | 0.6453 |
| Ensemble | ~0.620 | ~0.640 | ~0.649 |

**審查意見：**
- AUC 範圍 0.61~0.65，在三分類台股預測中屬合理偏中上
- D+20 > D+5 > D+1 的趨勢與基本面因子主導的系統一致
- 沒有任何 AUC > 0.75 的異常值，排除嚴重洩漏

### 3.2 Walk-Forward Fold 穩定性

| 模型 | Fold 0 | Fold 1 | Fold 2 | Fold 3 | Std |
|------|--------|--------|--------|--------|-----|
| D+1 LGB | 0.623 | 0.636 | 0.620 | 0.591 | 0.017 |
| D+5 LGB | 0.653 | 0.624 | 0.636 | 0.653 | 0.012 |
| D+20 LGB | 0.669 | 0.645 | 0.659 | 0.622 | 0.018 |

所有 fold AUC std < 0.02，穩定性良好。Fold 3（2025-01~03）的 D+1 略低（0.591），可能反映市場結構變化。

### 3.3 ICIR（核心指標）

| Horizon | IC | ICIR | 評級 |
|---------|-----|------|------|
| D+1 | 0.020 | 0.105 | ⚠️ 弱（不建議實戰） |
| D+5 | 0.086 | 0.514 | ✅ 及格邊界 |
| D+20 | 0.115 | 1.789 | ✅ 優秀（可實戰） |

**關鍵結論：D+20 是唯一具備實戰級預測能力的 Horizon（ICIR > 1.5）。**

### 3.4 回測績效

D+20 Ensemble（最佳策略）：
- Standard：Return=+49.3%, Sharpe=1.87, MDD=-18.7%
- Discount：Return=+54.8%, Sharpe=2.02, MDD=-18.7%
- Conservative：Return=+45.8%, Sharpe=1.76, MDD=-18.7%
- Rank IC=0.1507

D+1 策略回報為負（-33%），驗證了 ICIR 分析的結論 — D+1 不適合實戰。

### 3.5 Bootstrap CI

| 策略 | Return 點估計 | 95% CI | 是否顯著 |
|------|-------------|--------|---------|
| D+1 | -33.0% | [-60.3%, +13.1%] | ⚠️ CI 含 0 |
| D+5 | +40.0% | [-16.7%, +121.3%] | ⚠️ CI 含 0 |
| D+20 | +54.6% | [-5.2%, +149.0%] | ⚠️ CI 含 0 |

**審查意見：** 所有 CI 都包含 0，但這主要是因為 OOS 期只有 ~10 個月。D+20 的 CI 下界 -5.2% 已接近 0，隨著數據累積（>2 年）預期會變得顯著。DSR 重新驗證 D+20 全部 PASS（p=1.0）也支持此結論。

---

## 四、回測邏輯與前瞻偏差

### 4.1 通過項目
- ✅ 信號生成僅使用 OOF predictions（非訓練集擬合值）
- ✅ Forward returns 僅用於 Rank IC 計算，不影響組合建構
- ✅ `merge_asof(direction="backward")` 確保 PIT 安全
- ✅ 流動性過濾（最低日均量 50 萬股）
- ✅ 漲跌停偵測（排除 ±9.5% 漲跌停股票）
- ✅ Embargo 20 天（訓練/測試之間）

### 4.2 潛在風險
- ⚠️ 無存活者偏差處理（但數據期僅 2 年，下市股票影響小）
- ⚠️ 成交量過濾使用歷史均量，實際執行可能面臨滑價

---

## 五、程式碼 Critical Bugs（需修復）

### Bug #1：ROIC 計算錯誤（Critical）
**位置：** `balance_sheet_processor.py` compute_bs_ratios()  
**問題：** `df.get("stockholders_equity", 0)` 返回 scalar 0 而非 Series，導致 invested_capital 計算異常  
**影響：** ROIC 值可能為 NaN 或不正確  
**修復：** 改用 `df.get("stockholders_equity", pd.Series(0, index=df.index))`

### Bug #2：NOPAT 有效稅率邏輯反轉（Critical）
**位置：** `balance_sheet_processor.py` line ~242  
**問題：** `eff_tax = 1 - (net_income / operating_income)` 在 net_income > operating_income 時產生負稅率  
**影響：** 動態稅率估計失效，永遠回退到 20% 假設  
**修復：** 改為 `eff_tax = (operating_income - net_income) / operating_income`

### Bug #3：Implied Shares 符號錯誤（Major）
**位置：** `engineer.py` build_valuation_features() 多處  
**問題：** `.abs()` 用於 `(net_income / eps)` 掩蓋了虧損公司的負值  
**影響：** P/B、P/S、EV/EBITDA 在虧損公司的計算結果不正確  
**修復：** 移除 `.abs()`，改為上游過濾 eps > 0 的樣本

### Bug #4：EV 計算缺少現金調整（Major）
**位置：** `engineer.py` line ~452  
**問題：** EV = market_cap + total_debt，但未扣除現金（current_assets 作為近似）  
**影響：** EV/EBITDA 系統性偏高  
**修復：** 加入 `- current_assets`（如果可用）

### Bug #5：EBITDA D&A 符號處理（Minor）
**位置：** `balance_sheet_processor.py`  
**問題：** `.abs()` 用於折舊攤銷，資料錯誤時可能膨脹 EBITDA  
**修復：** 驗證 D&A 資料品質或移除 `.abs()`

---

## 六、改善建議優先序

### 🔴 Phase 5 前必須修復
1. **修復 5 個程式 Bugs**（估計 1-2 小時）→ 重跑 Phase 1~3
2. **精簡共線特徵**：移除 trend_ma_5/10、fund_nopat 等完全冗餘特徵

### 🟡 Phase 5 中可同步進行
3. **D+1 策略調整**：ICIR=0.105 不適合實戰，考慮移除或僅作為輔助信號
4. **Quintile L/S Spread 修復**：D+20 的 27734% 是 annualization bug，需檢查計算邏輯
5. **Bootstrap CI 統計檢定力**：OOS 期太短，後續需累積更多數據

### 🟢 長期改善
6. **特徵覆蓋率提升**：val_ 特徵 33% NaN 主要來自虧損公司，Phase 5 NLP 情緒因子可補充
7. **存活者偏差處理**：加入下市股票的退場機制
8. **D+20 策略深化**：這是核心策略（ICIR=1.789），可投入更多資源優化

---

## 七、結論

**系統架構健全，核心策略（D+20 Ensemble）具備實戰潛力**（Sharpe=2.02, ICIR=1.789, Rank IC=0.15）。但在進入 Phase 5 NLP 擴展之前，**建議先修復 5 個財務計算 bugs 並重跑 Phase 1~3**，預期修復後 fund_ 和 val_ 系列特徵品質將顯著提升，D+5 和 D+20 的 AUC/ICIR 都有上升空間。

修復所需時間估計 1-2 小時，是投入產出比最高的改善動作。
