# Phase 5A Bug 修復驗證報告

> **執行日期**：2026-04-18
> **審查來源**：`進度報告/Phase4_交叉檢驗審查報告.md`（第 142–172 行）
> **處理策略**：採用策略 B —— 全面 code review + 針對性重寫 + 完整 unit test 驗證
> **Phase 5A Milestone**：M1 完成

---

## 一、總覽

| # | Bug | 原嚴重度 | 原始狀態 | 本次處理 | 驗證結果 |
|---|-----|----------|----------|----------|----------|
| #1 | ROIC `stockholders_equity` 返回 scalar 0 | 🔴 Critical | 舊 fix 已就位 | 重新 review + 寫 2 個 unit test | ✅ PASS |
| #2 | NOPAT 有效稅率邏輯反轉 | 🔴 Critical | 舊 fix 已就位 | 重新 review + 寫 3 個 unit test | ✅ PASS |
| #3 | Implied Shares `.abs()` 掩蓋虧損公司 | 🟡 Major | 舊 fix 已就位 | 重新 review + 寫 2 個 unit test | ✅ PASS |
| #4 | EV 計算缺少現金調整 | 🟡 Major | **部分修復**（框架有、映射缺）| **補 `BS_TYPE_MAP` 現金科目映射** + 寫 3 個 unit test | ✅ PASS |
| #5 | EBITDA D&A 符號處理過於粗糙 | 🟢 Minor | 弱修復（`.abs()` 範圍過廣）| **細化邏輯（trusted / flipped / mixed→NaN 三分支）** + 寫 3 個 unit test | ✅ PASS |
| 🆕 | 整合 smoke test | — | — | 新增端到端測試 | ✅ PASS |

**Unit Test 總計**：14 / 14 PASS（`測試/test_phase5a_bugs.py`）
**全專案 Regression**：105 / 113 PASS（8 個失敗是 `test_features.py` 既有 `train_idx` 相容性問題，與本次無關）

---

## 二、Bug 個別 Review

### Bug #1：ROIC `stockholders_equity` scalar 回傳

**原始問題**（來源：Phase4 審查報告 line 145–148）
```python
# 原舊程式推論（已不可考）：
equity = df.get("stockholders_equity", 0)   # 欄位缺失時返回 int 0（scalar）
invested_capital = equity + ibd + sbd       # Series + scalar → broadcast，但 ROIC 會受汙染
```

**現況程式**（`balance_sheet_processor.py` line 302–304）
```python
# [H4] equity 缺失時保持 NaN（不用 fillna(0)）
equity = df["stockholders_equity"] if "stockholders_equity" in df.columns \
         else pd.Series(np.nan, index=df.index)
```

✅ **已正確修復**：缺失時是 `pd.Series(np.nan, index=df.index)`，不是 scalar 0。
下游 `invested_capital + ibd + sbd + bonds` 與 `MIN_INVESTED_CAPITAL` threshold 合作，負 equity 公司 ROIC 會變 NaN 或被 clip 到 `[-2, 2]`。

**Unit Test 驗證**：
- `test_equity_missing_returns_series_not_scalar`：建構缺少 equity 的 BS，驗證 ROIC 全為 NaN
- `test_equity_negative_returns_nan`：資不抵債公司（equity<0）ROIC 為合理值或 NaN，不會是 inf

---

### Bug #2：NOPAT 有效稅率邏輯反轉

**原始問題**（來源：Phase4 審查報告 line 150–154）
舊邏輯 `eff_tax = 1 - (net_income / operating_income)` 在 `NI > OI`（業外收入大）時產生**負稅率**，
NOPAT 會被負稅率膨脹。

**現況程式**（`balance_sheet_processor.py` line 284–295）
```python
if "net_income_sq" in df.columns and "operating_income_sq" in df.columns:
    safe_oi = df["operating_income_sq"].replace(0, np.nan)
    tax_expense = df["operating_income_sq"] - df["net_income_sq"]
    eff_tax = (tax_expense / safe_oi)
    # 虧損公司 (OI <= 0) 稅率設為 0
    eff_tax = eff_tax.where(df["operating_income_sq"] > 0, 0.0)
    # clip [0, 0.4]，NaN fallback 用 0.17（台灣中位數）
    eff_tax = eff_tax.clip(*TAX_RATE_CLIP).fillna(TAX_RATE_FALLBACK)
    df["nopat"] = df["operating_income_sq"] * (1 - eff_tax)
```

✅ **已正確修復**：
- 公式改為 `(OI - NI) / OI`（正確的「有效稅率」概念）
- clip 到 `[0, 0.4]` 防止負稅率與超高稅率
- 虧損公司 `OI <= 0` 強制 `eff_tax = 0`
- NaN fallback 用 17%（台灣上市公司中位數）

**Unit Test 驗證**：
- `test_normal_case_positive_tax_rate`：NI=8e8, OI=1e9（20% 稅率）→ NOPAT ≈ 8e8 ✅
- `test_ni_greater_than_oi_eff_tax_floored_at_zero`：NI=1.5e9 > OI=1e9 → eff_tax clip 到 0 → NOPAT = OI = 1e9 ✅
- `test_oi_negative_eff_tax_zero`：OI=-1.5e8（虧損）→ eff_tax=0 → NOPAT = OI = -1.5e8 ✅

---

### Bug #3：Implied Shares `.abs()` 掩蓋資料異常

**原始問題**（來源：Phase4 審查報告 line 156–160）
舊邏輯 `implied_shares = (net_income / eps).abs()` 會：
- 把 `NI<0, EPS<0` 的虧損公司變成正確的正股數（但 `.abs()` 是副作用，不是正確邏輯）
- 把 `NI>0, EPS<0`（資料異常）靜默產生正股數，汙染 P/B、P/S、EV/EBITDA

**現況程式**（`engineer.py` line 397–421）
```python
def _calc_implied_shares(df_ref, net_inc_col_ref, eps_col_ref):
    safe_eps = df_ref[eps_col_ref].replace(0, np.nan)
    raw_shares = df_ref[net_inc_col_ref] / safe_eps
    implied = raw_shares.where(raw_shares > 0, np.nan)  # 必須正數

    # 單位校驗：median shares < 1000 → 自動 ×1000 校正
    median_shares = implied.median()
    if pd.notna(median_shares) and median_shares < 1000:
        implied = implied * 1000

    # 🔴2 fix: 異號強制 NaN
    sign_mismatch = (
        ((df_ref[net_inc_col_ref] > 0) & (df_ref[eps_col_ref] < 0)) |
        ((df_ref[net_inc_col_ref] < 0) & (df_ref[eps_col_ref] > 0))
    )
    implied = implied.where(~sign_mismatch, np.nan)
    return implied
```

✅ **已正確修復**：
- 不再用 `.abs()`，改用 `.where(raw_shares > 0, np.nan)`（數學上等價於「同號才算」）
- 加入 sign mismatch 偵測（NI/EPS 反號 → 強制 NaN）
- 加入單位自動校驗

**Unit Test 驗證**：
- `test_loss_company_returns_valid_shares`：NI=-1e8, EPS=-1.0 → shares=1e8（合法，虧損公司有股數）→ val_pb 可計算 ✅
- `test_sign_mismatch_returns_nan`：NI=1e8（正）+ EPS=-1.0（負）→ shares=NaN → val_pb 全 NaN ✅

---

### Bug #4：EV 計算缺少現金調整 🔴 **本次實質修補**

**原始問題**（來源：Phase4 審查報告 line 162–166）
`EV = market_cap + total_debt - cash_proxy`，但 `BS_TYPE_MAP` 未映射現金科目，
導致 `df["cash_and_equivalents"]` 欄位根本不存在，`cash_proxy` 永遠為 0，EV 系統性偏高。

**根本原因**（本次發現）
審查報告只講「EV 公式缺現金」，但程式早期的 fix 只加了「**如果**有 `cash_and_equivalents` 欄位就用它」的 if 分支，
卻沒有在 `BS_TYPE_MAP` 中實際註冊現金科目。檢視原始資料：

```
選用資料集/parquet/balance_sheet.parquet 的 type 分佈：
CashAndCashEquivalents         17,033 筆  ← 資料是有的
CashAndCashEquivalents_per     17,033 筆
```

資料存在但 pivot 後沒有欄位 → `cash_proxy = 0` 永久生效。

**本次修補**（`balance_sheet_processor.py` line 78–88）
```python
# === Phase 5A Bug #4 fix: 加入現金科目（原本未映射，導致 cash_proxy=0）===
"現金及約當現金": "cash_and_equivalents",
"CashAndCashEquivalents": "cash_and_equivalents",
# === Phase 5A 追加：股本/保留盈餘/資本公積，供未來使用 ===
"OrdinaryShare": "ordinary_share",         # 股本金額（元），÷面額=股數
"CapitalStock": "capital_stock",
"RetainedEarnings": "retained_earnings",
"CapitalSurplus": "capital_surplus",
"PropertyPlantAndEquipment": "ppe",
```

✅ **完成修復**：補上映射後，`pivot_financial_statement` 輸出將包含 `cash_and_equivalents` 欄位，
`engineer.py` 的 EV 計算會自動走「使用 `cash_and_equivalents` 作為 cash proxy」分支。

**副效益**：同時註冊 `OrdinaryShare`（股本金額），未來 Phase 5B 可考慮用真實股本 ÷ 面額 取代 `implied_shares`，
進一步提升估值因子準確度。

**Unit Test 驗證**：
- `test_bs_type_map_contains_cash`：assert `"CashAndCashEquivalents" in BS_TYPE_MAP` ✅
- `test_pivot_produces_cash_column`：模擬 FinMind 長格式 → pivot 後有 `cash_and_equivalents` 欄位 ✅
- `test_ev_subtracts_cash`：構造有 5e11 現金的公司 → `val_ev_ebitda` 可計算（走 cash_proxy > 0 分支）✅

---

### Bug #5：EBITDA D&A 符號處理 🟢 **本次實質細化**

**原始問題**（來源：Phase4 審查報告 line 168–171）
舊邏輯在 per-company 層級判斷：
```python
if neg_pct > 0.7:     # 明顯負慣例
    da_series.loc[grp_idx] = company_da.abs()
elif neg_pct > 0.3:   # 混合符號
    da_series.loc[grp_idx] = company_da.abs()   # ← 問題：仍 .abs()
```

混合符號（30%~70% 負值）的公司應該是「資料品質問題」，但舊邏輯仍一律取 `.abs()`，
可能把真實的資料錯誤遮蓋，產生不正確的 EBITDA。

**本次細化**（`balance_sheet_processor.py` line 339–386）
改為三分支邏輯：

| neg_pct 區間 | 處理 | 意義 |
|--------------|------|------|
| `< 5%` | 信任原值，不動 | 純正值慣例（FinMind 新格式） |
| `>= 70%` | 整欄 `.abs()` | 明顯負值慣例（FinMind 舊格式） |
| `[5%, 70%)` | 負值 row 個別設為 NaN | 混合＝資料品質問題，不該統一處理 |

這樣可保留正值 row 計算 EBITDA，負值可疑 row 設 NaN 讓後續流程自然處理。

**Unit Test 驗證**：
- `test_pure_positive_da_unchanged`：全正 D&A → 信任 → EBITDA = OI + D&A ✅
- `test_all_negative_da_flipped_to_abs`：全負 D&A → `.abs()` → EBITDA 正常 ✅
- `test_mixed_sign_da_negative_set_to_nan`：5 正 5 負 → 負 row NaN，正 row 正常 → 5 valid + 5 NaN ✅

---

## 三、整合 Smoke Test

`TestIntegration_AllBugsCombined::test_full_pipeline_smoke`：
- 輸入 FinMind 長格式 BS（含現金科目）+ CF（含 D&A）+ 已處理的 Income Statement
- 輸出應包含 `roe, roa, roic, debt_equity, current_ratio, nopat, ebitda, cash_and_equivalents`
- ROIC 驗證：NOPAT=2e11（20% 稅率）, IC=1.55e12 → ROIC ≈ 0.129 ✅（落在期望區間 [0.10, 0.16]）

---

## 四、檔案修改清單

| 檔案 | 修改內容 | 行數 |
|------|----------|------|
| `程式碼/src/data/balance_sheet_processor.py` | Bug #4 補 `BS_TYPE_MAP` 現金 + 其他映射 | +10 |
| `程式碼/src/data/balance_sheet_processor.py` | Bug #5 細化 D&A 三分支邏輯 | +20 / -15 |
| `程式碼/測試/test_phase5a_bugs.py` | **新增**：14 個 unit tests | +420（新檔）|

---

## 五、後續動作

M1 完成，進入 M2：法人籌碼 + 融資融券資料抓取。

Phase 5A Bug 修復已達成「確保 NLP 因子加入前，既有因子計算正確」的目標。
後續 M2-M6 不再回頭動這些 bug 相關邏輯，除非 M6 重跑 Phase 1-3 時發現新問題。

---

## 六、驗證指令（供未來重現）

```bash
# 執行 Phase 5A bug tests
cd "大數據與商業分析專案/程式碼"
python -m pytest 測試/test_phase5a_bugs.py -v

# 預期輸出：14 passed in ~2s
```

---

**Phase 5A M1 完成確認**：✅
