# Phase 5A 基線對照報告（Scaffold / 草稿）

> **狀態**：待 M6 實測數據回填
> 報告日期：2026-04-18 *(M6 執行完畢後更新)*
> 對照基準：Phase 4 交叉檢驗審查報告（2026-04-09）

---

## 0. 報告摘要（Executive Summary）

本報告對比 Phase 4 基線與 Phase 5A 改進後的效能差異，聚焦三大改進來源：

| 改進項 | 預期影響 | 基線 Phase 4 | Phase 5A | Δ |
|-------|---------|:------------:|:--------:|:--:|
| Bug 修復（5 項 critical） | 估值/基本面因子修正 | _TBD_ | _TBD_ | _TBD_ |
| Phase 5A 新特徵（chip_/mg_/ind_/event_） | 訊號多元化 | 56 特徵 | **_TBD_ 特徵** | _TBD_ |
| 共線前置過濾 | 減少冗餘 | 34 → 28 (VIF 後) | _TBD_ | _TBD_ |

**綜合結論（待填）**：_訊號是否顯著增強？Top-K 組合 IR 是否提升？D+1 horizon 是否從 0.1 脫離？_

---

## 1. Phase 5A 做了什麼？

### 1.1 Bug 修復（M1）

| Bug | 現象 | 修復方式 | 驗證 |
|-----|------|---------|------|
| #1 ROIC equity scalar | implied_shares 錯用 EPS_累計 | 改用 EPS_單季 | `test_phase5a_bugs.py::TestBug1` ✅ |
| #2 NOPAT tax rate | 使用總帳期稅率 → 震盪 | 改用單季有效稅率 + winsorize [10%, 40%] | `TestBug2` ✅ |
| #3 Implied Shares sign | EPS<0 時股數為負 | 使用 `abs(net_income / eps)` | `TestBug3` ✅ |
| #4 EV cash adjustment | BS_TYPE_MAP 缺 cash 對應 → cash_proxy=0 | 新增 6 個 BS_TYPE_MAP 條目 | `TestBug4` ✅ |
| #5 D&A sign handling | FinMind D&A 正負混雜 | 3 分支處理：trusted/flipped/mixed | `TestBug5` ✅ |

詳見 `Phase5A_Bug修復驗證報告.md`。

### 1.2 資料擴充（M2 + M3）

- **三大法人買賣超**：`institutional_investors.parquet`（_TBD 筆_）
  - 外資/投信/自營商 buy/sell/net，加上 `all_inst_net`
- **融資融券**：`margin_trading.parquet`（_TBD 筆_）
  - margin_balance / short_balance，衍生 margin_short_ratio、margin_use_rate
- **產業分類**：`industry.parquet`（1,932 stocks × 44 industries × 2 listing_types）
- **stock_text 切為完整版**：`stock_text.parquet`（1.66 GB 記憶體，含 content）

### 1.3 特徵工程擴充（M4）

原五大支柱 56 個特徵，新增：

| 支柱 | 前綴 | 新特徵 | 說明 |
|-----|------|-------|------|
| 籌碼 | `chip_` | ~10 | foreign/trust/dealer 1d/5d/20d nets, trend, consensus |
| 融資融券 | `mg_` | ~8 | margin/short 昨日值與 5d 變化、散戶情緒 proxy |
| 產業相對 | `ind_` | 4 | return_rel_20d, momentum_rank_20d, vol_rel_60d, member_count |
| 事件質性（強化） | `event_` | 7 | mention_cnt_1d/5d/20d, surge, sent_score_5d, news_ratio, main_ratio |

合計預計 **~85 特徵**（從 56 → 85+，+52%）。

### 1.4 共線精簡（M5）

- **Corr 前置過濾**：|corr| > 0.95 先刪除（字典序較大者）
- **VIF 迭代**：vif_max=10，保底 rfecv_min_features=20
- 預期 VIF 後剩餘 _TBD_ 個特徵（對比 Phase 4 的 28）

---

## 2. Feature Store 對照

### 2.1 基本統計

|  | Phase 4 | Phase 5A | Δ |
|---|:---:|:---:|:---:|
| Rows | 948,976 | _TBD_ | _TBD_ |
| Cols | 72 | _TBD_ | _TBD_ |
| Features (全 8 支柱) | 56 | _TBD_ | _TBD_ |
| Memory MB | ~500 | _TBD_ | _TBD_ |

### 2.2 按支柱分布（Phase 5A）

```
trend_:  25
fund_:   18（含 Phase 4 BS 衍生）
val_:     5（修復後更穩定）
event_:  _TBD_（phase5a 強化）
risk_:    6
chip_:   _TBD_
mg_:     _TBD_
ind_:    _TBD_
──────────────
Total:  _TBD_
```

### 2.3 共線性對照

| 檢測 | Phase 4 | Phase 5A | 說明 |
|------|:-------:|:--------:|------|
| |corr|>0.95 對數 | 53 對 | _TBD_ | Corr prefilter 已前置移除 |
| VIF>10 迭代次數 | N/A | _TBD_ | - |
| 最終保留特徵 | 28 | _TBD_ | - |

---

## 3. 模型效能對照

### 3.1 Walk-Forward CV AUC

Phase 4 來源：`Phase4_交叉檢驗審查報告.md § 3.2`（fold-avg）

| Horizon | Model | Phase 4 AUC | Phase 5A AUC | Δ | 顯著性 |
|--------|-------|:-----------:|:------------:|:--:|:-----:|
| D+1 | LightGBM | 0.617 | _TBD_ | _TBD_ | _TBD_ |
| D+1 | XGBoost  | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| D+5 | LightGBM | 0.641 | _TBD_ | _TBD_ | _TBD_ |
| D+5 | XGBoost  | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| D+20 | LightGBM | 0.649 | _TBD_ | _TBD_ | _TBD_ |
| D+20 | XGBoost  | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

### 3.2 ICIR 對照（關鍵指標）

Phase 4 來源：`Phase4_交叉檢驗審查報告.md § 3.3`

| Horizon | Phase 4 IC | Phase 4 ICIR | Phase 5A IC | Phase 5A ICIR | ΔICIR | 目標 (>0.5) |
|--------|:----------:|:-----------:|:-----------:|:-------------:|:-----:|:-----------:|
| D+1 | 0.020 | 0.105 | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| D+5 | 0.086 | 0.514 | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| D+20 | 0.115 | 1.789 | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

**重點觀察**：D+1 基線 ICIR=0.105 太弱。Phase 5A 新加入的 chip_consensus_5d 與 event_mention_surge 預期能改善短期 horizon。

### 3.3 Bootstrap CI 對照

Phase 4 來源：`Phase4_交叉檢驗審查報告.md § 3.4`（OOS Annualised Return 95% CI）

| Horizon | Phase 4 Ret | Phase 4 CI | Phase 5A Ret | Phase 5A CI | 包含 0？ |
|--------|:-----------:|:----------:|:------------:|:-----------:|:-------:|
| D+1 | -33.0% | [-60.3%, +13.1%] | _TBD_ | _TBD_ | _TBD_ |
| D+5 | +40.0% | [-16.7%, +121.3%] | _TBD_ | _TBD_ | _TBD_ |
| D+20 | +54.6% | [-5.2%, +149.0%] | _TBD_ | _TBD_ | _TBD_ |

- **DSR (Deflated Sharpe)**：Phase 4 D+20 PASS (p=1.0)；Phase 5A = _TBD_

---

## 4. 特徵重要性分析

### 4.1 Top 20 重要特徵（Phase 5A）

| 排名 | 特徵 | 支柱 | Gain | 是否為 Phase 5A 新增？ |
|-----|------|------|-----|:-----:|
| 1 | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| ... | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

**觀察重點**：
- Phase 5A 新特徵（chip_ / mg_ / ind_ / event_phase5a）在 top 20 中佔比？
- 若 >30% 即證明擴充有效；<20% 則需回頭檢查信號設計。

### 4.2 按支柱貢獻度

```
待填：
  趨勢:  _TBD_%
  基本面: _TBD_%
  估值:   _TBD_%
  事件:   _TBD_%
  風險:   _TBD_%
  籌碼:   _TBD_%  ←新
  融資融券:_TBD_%  ←新
  產業相對:_TBD_%  ←新
```

---

## 5. 回測對照（Top-10%策略）

| 指標 | Phase 4 基線 | Phase 5A | Δ |
|------|:-----------:|:--------:|:--:|
| Annualized Return | _TBD_ | _TBD_ | _TBD_ |
| Annualized Vol | _TBD_ | _TBD_ | _TBD_ |
| Sharpe | _TBD_ | _TBD_ | _TBD_ |
| Max Drawdown | _TBD_ | _TBD_ | _TBD_ |
| Turnover | _TBD_ | _TBD_ | _TBD_ |
| Cost-adj Sharpe | _TBD_ | _TBD_ | _TBD_ |

---

## 6. 品質閘門彙整

| Gate | Phase 4 | Phase 5A | 狀態 |
|------|:-------:|:--------:|:----:|
| 除權息還原誤差 <0.5% | PASS | _TBD_ | _TBD_ |
| 文本去重率 15-30% | PASS | _TBD_ | _TBD_ |
| 洩漏偵測 0 warning | PASS | _TBD_ | _TBD_ |
| 標籤一致性 | PASS | _TBD_ | _TBD_ |
| Feature Store 無 Inf | PASS | _TBD_ | _TBD_ |
| AUC > 0.52 | PASS | _TBD_ | _TBD_ |
| ICIR > 0.5（任一 horizon）| PASS (D+20) | _TBD_ | _TBD_ |

---

## 7. 結論與下一步

### 7.1 結論（待填）

_在 M6 實測後填寫：_
- Phase 5A 是否成功提升訊號強度？
- D+1 horizon 是否脫離噪音區（ICIR > 0.3）？
- 新增的籌碼/融資融券/產業相對強弱貢獻是否顯著？

### 7.2 下一步

- **Phase 5B**：進行完整 NLP（CKIP tokenization + ANTUSD + FinBERT + BERTopic）
- **Phase 6**：模型深化（Transformer / Stacking / 風控補全）
- **Phase 7**：投資決策情境分析（靜態情境 + 新手可讀報告）

---

## 附錄：M 節點完成時間

| M | 名稱 | 預計耗時 | 實際耗時 | 狀態 |
|---|-----|:-------:|:-------:|:----:|
| M1 | Bug 修復 + 驗證 | - | - | ✅ |
| M2 | 籌碼/融資融券抓取 | ~13.8h @ free tier | _TBD_ | 🔄 進行中 |
| M3 | 產業分類 + text 切換 | ~1h | <10min | ✅ |
| M4 | 特徵擴充（4 類） | - | - | ✅（程式） |
| M5 | 共線精簡 | - | - | ✅ |
| M6 | Phase 1-3 重跑 + 對照 | ~3-4h | _TBD_ | ⏳ 待 M2 完成 |
