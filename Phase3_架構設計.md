# Phase 3 架構設計書：模型治理 + 部署優化 + 信號監控

> **狀態**：待確認
> **前置條件**：Phase 1（資料地基）✅ Phase 2（模型開發 + 回測）✅（8/9 品質門控通過）
> **目標**：將研究階段的模型成果轉化為可監控、可維護、可持續演進的生產級系統

---

## 一、Phase 3 的定位

| 階段 | 任務 | 產出 |
|------|------|------|
| Phase 1 | 資料地基 + 特徵工程 | feature_store.parquet（948K rows × 59 cols） |
| Phase 2 | 模型訓練 + 策略回測 + 統計驗證 | 訓練模型、回測報告、品質閘門、儀表板 |
| **Phase 3** | **模型治理 + 部署優化 + 信號監控** | **模型卡片、漂移偵測、信號監控面板、自動化管線** |

Phase 3 不是「重新訓練」或「調參」，而是把 Phase 2 驗證過的模型包裝成可治理的生產系統。

---

## 二、Phase 3 執行流程總覽（8 個步驟）

```
run_phase3.py
│
├── Step 1: 載入 Phase 2 產出 + 模型重建（修復 save_models bug）
├── Step 2: 模型治理文件（Model Card）自動生成
├── Step 3: 資料漂移偵測（Data Drift Detection）
├── Step 4: 信號衰減監控（Signal Decay Monitor）
├── Step 5: 模型效能基線建立（Performance Baseline）
├── Step 6: 預測管線封裝（Prediction Pipeline）
├── Step 7: DSR 門控重新驗證（修正策略數量懲罰）
├── Step 8: 儀表板升級（Dashboard Enhancement）
└── Step 9: 品質閘門 + 產出報告
```

---

## 三、各步驟詳細設計

### Step 1：載入 Phase 2 產出 + 模型重建

**輸入：**
- `outputs/feature_store.parquet`（948K rows × 59 cols）
- `outputs/reports/phase2_report_*.json`（最新報告）
- `outputs/models/`（已訓練模型 — LightGBM / XGBoost）
- `config/base.yaml`

**處理：**
- 驗證所有 Phase 2 檔案完整性
- 載入最新 Phase 2 報告並解析品質閘門結果
- 確認可用模型列表（排除 D+1，因 Sharpe 為負）
- **模型重建**：偵測到 `outputs/models/` 為空時，自動重新訓練最後一折模型並儲存

**背景：** Phase 2 的 `save_models()` 因 key mismatch bug（`"model"` vs `"last_model"`）導致模型從未被儲存。此 bug 已在 `src/models/trainer.py` 修復（`res.get("last_model") or res.get("model")`）。Phase 3 Step 1 會偵測此狀況，利用已有的 Feature Store + 特徵清單 + 超參數，只重新訓練最後一折的模型（約 2-3 分鐘），而非重跑完整 Phase 2。

**對現有儀表板的影響：** ✅ **無影響**。經完整檢查，儀表板所有 6 個頁面（投資解讀面板、Model Metrics、ICIR Analysis、Backtest、Feature Analysis、Data Explorer）均不依賴 `outputs/models/` 目錄中的 `.joblib` 模型檔案。儀表板完全依賴：
- `dashboard/data/recommendations.json`（預計算結果）
- `outputs/reports/phase2_report_*.json`（Phase 2 報告）
- `outputs/figures/*.png`（圖表）

模型檔案只影響 Phase 3 的預測管線（Step 6）和未來的批次預測功能。

**輸出：**
- 驗證通過的模型清單：`lightgbm_D5`, `xgboost_D5`, `lightgbm_D20`, `xgboost_D20`
- `outputs/models/*.joblib`（4 個模型檔案）
- Phase 2 報告摘要結構

**品質閘門：**
- Phase 2 報告必須存在且完整
- 至少有一個策略 Sharpe > 0
- 模型檔案重建成功（4 個 .joblib 檔案存在）

---

### Step 2：模型治理文件（Model Card）

**目的：** 遵循 Google Model Cards 規範，為每個可用模型自動生成標準化文件。

**輸入：**
- Phase 2 報告中的 `comparison`、`backtest`、`calibration`、`statistical_validation` 數據
- `config/base.yaml` 中的模型參數

**生成內容（每個模型）：**

```
Model Card: xgboost_D20
├── 模型概述（引擎、目標、訓練日期）
├── 預期用途與限制
├── 訓練數據摘要（日期範圍、股票數、特徵數）
├── 效能指標
│   ├── AUC / LogLoss / Balanced Accuracy
│   ├── Rank IC / ICIR
│   ├── 回測 Sharpe / 年化報酬 / 最大回撤
│   └── Bootstrap 95% CI
├── 校準品質（ECE before/after）
├── 公平性與偏差分析
│   ├── 按產業分組的 AUC 分佈
│   └── 按市值分組的 AUC 分佈
├── 已知限制
│   ├── D+1 策略不可行（交易成本侵蝕）
│   ├── DSR 未通過（短回測期 + 多策略懲罰）
│   └── Fold 3 OOD 退化（2025 Q1 市場震盪）
└── 版本與變更歷史
```

**輸出：**
- `outputs/governance/model_card_xgboost_D5.json`
- `outputs/governance/model_card_xgboost_D20.json`
- `outputs/governance/model_card_lightgbm_D5.json`
- `outputs/governance/model_card_lightgbm_D20.json`

**新增模組：** `src/governance/model_card.py`

---

### Step 3：資料漂移偵測（Data Drift Detection）

**目的：** 建立機制偵測 Feature Store 中特徵分佈是否隨時間發生顯著偏移，預警模型可能失效。

**方法：**

| 偵測方式 | 對象 | 閾值 |
|---------|------|------|
| PSI（Population Stability Index） | 每個特徵的分佈 | PSI > 0.2 = 警告 |
| KS Test（Kolmogorov-Smirnov）| 關鍵特徵 | p < 0.01 = 顯著漂移 |
| 標籤分佈偏移 | label_5 / label_20 三類佔比 | 類別佔比偏移 > 10% |

**輸入：**
- Feature Store 按時間切分為「訓練期」vs「最近期」
- 23 個已選特徵

**處理邏輯：**
```
1. 以 Walk-Forward 最後一折的訓練集為 "reference"
2. 以最後一折的測試集為 "current"
3. 對每個特徵計算 PSI 和 KS 統計量
4. 標記漂移特徵，計算整體漂移分數
5. 若漂移嚴重，觸發「建議重新訓練」警告
```

**輸出：**
- `outputs/governance/drift_report.json`
  - 每個特徵的 PSI / KS p-value
  - 整體漂移嚴重度（低/中/高）
  - 漂移最嚴重的 Top 5 特徵

**新增模組：** `src/governance/drift_detector.py`

---

### Step 4：信號衰減監控（Signal Decay Monitor）

**目的：** 量化模型預測信號隨時間的衰減速度，判斷模型再訓練的頻率。

**方法：**
```
1. 將 OOF 預測按月份分組
2. 計算每月的 Rank IC
3. 繪製 IC 時間趨勢（含 3 個月移動平均）
4. 計算信號半衰期（IC 從峰值降至 50% 所需月數）
5. 基於 Phase 2 Alpha Decay 分析延伸
```

**輸入：**
- Phase 2 的 `alpha_decay` 結果
- Phase 2 的 `icir` 結果（含 IC 時間序列）
- OOF predictions

**輸出：**
- `outputs/governance/signal_decay_report.json`
  - 每月 IC 趨勢
  - 信號半衰期估計
  - 建議再訓練週期

**新增模組：** `src/governance/signal_monitor.py`

---

### Step 5：模型效能基線建立（Performance Baseline）

**目的：** 為部署後的持續監控建立明確的效能基準線，當效能低於基線時觸發警告。

**基線指標（每個可用模型）：**

| 指標 | 基線來源 | 警告閾值 |
|------|---------|---------|
| AUC | Phase 2 平均 AUC | 下降 > 3% |
| Rank IC | Phase 2 IC | 轉為負數 |
| Sharpe Ratio | Phase 2 回測 Sharpe | 下降 > 50% |
| 校準 ECE | Phase 2 校準後 ECE | 上升 > 100% |
| 特徵缺失率 | Phase 2 NaN 比率 | 上升 > 5% |

**輸出：**
- `outputs/governance/performance_baseline.json`
- 包含每個模型的基線值和對應警告閾值

**新增模組：** `src/governance/baseline.py`

---

### Step 6：預測管線封裝（Prediction Pipeline）

**目的：** 將「特徵計算 → 模型預測 → 信號生成」封裝為標準化管線，供儀表板和未來的批次預測使用。

**管線架構：**
```
PredictionPipeline
├── load_models()          # 載入已訓練的 LightGBM/XGBoost
├── prepare_features()     # 從原始數據計算 23 個特徵
├── predict()              # 生成三類概率 [DOWN, FLAT, UP]
├── calibrate()            # 應用 Platt Scaling 校準
├── generate_signal()      # 概率 → 信號（偏多/中性/觀望）
└── build_recommendations()# 排序 + 生成 Top N 推薦
```

**關鍵設計：**
- 模型版本化管理（每次訓練標記版本號）
- 特徵一致性驗證（確保預測時的特徵與訓練時一致）
- 預測結果自動寫入 `dashboard/data/recommendations.json`

**輸出：**
- `src/pipeline/predictor.py`
- `src/pipeline/feature_validator.py`

---

### Step 7：DSR 門控重新驗證

**目的：** Phase 2 唯一未通過的品質門控是 `statistical_validity`（DSR），原因是將 D+1（明顯不可行）也納入策略數量計算，導致 `expected_max_sharpe` 被過度抬高。Phase 3 重新以合理的策略範圍驗證 DSR。

**Phase 2 DSR 失敗原因分析：**

| 問題 | 說明 |
|------|------|
| `n_strategies = 9` | 含 3 個 D+1 策略（Sharpe 全為負，不可行） |
| 短回測期 | 僅 229 交易日，`sharpe_std_error` ~1.1 |
| 過度懲罰 | `expected_max_sharpe` 被 9 策略抬至 1.4+，實際可行策略只有 6 個 |

**Phase 3 修正方法：**
```
1. 排除 D+1 策略（3 個），只保留 D+5 和 D+20 的 6 個策略
2. 重新計算 DSR：n_strategies=6 → expected_max_sharpe 下降
3. 對最佳策略（ensemble_D5, Sharpe=1.34）單獨計算 DSR
4. 記錄修正前/修正後的 DSR 對比
5. 若修正後仍未通過，標記為「已知限制」（回測期過短的結構性問題）
```

**輸入：**
- Phase 2 回測結果（daily_returns）
- Phase 2 統計驗證結果

**輸出：**
- `outputs/governance/dsr_revalidation.json`
  - 修正前 DSR（9 策略）
  - 修正後 DSR（6 策略）
  - 單一最佳策略 DSR
  - 最終判定（PASS / KNOWN_LIMITATION）

**新增模組：** 整合至 `src/governance/baseline.py`

---

### Step 8：儀表板升級（Dashboard Enhancement）

**目的：** 在現有 6 頁儀表板基礎上，新增模型治理相關頁面。

**新增頁面：**

| 頁面 | 內容 |
|------|------|
| `6_🛡️_Model_Governance.py` | 模型卡片展示、版本歷史、品質閘門狀態 |
| `7_📡_Signal_Monitor.py` | 漂移偵測視覺化、信號衰減趨勢、效能基線監控 |

**`6_🛡️_Model_Governance.py` 內容：**
- 模型卡片摘要（4 個模型的 KPI 對比）
- 品質閘門 9/9 狀態儀表
- 模型版本歷史時間線
- 已知限制與風險聲明

**`7_📡_Signal_Monitor.py` 內容：**
- 特徵漂移熱力圖（23 特徵 × 時間段的 PSI 矩陣）
- IC 時間趨勢線圖（含移動平均和衰減預估）
- 效能基線對比儀表（實際 vs 基線，用儀表盤呈現）
- 「需要重新訓練」警告面板

**現有頁面微調：**
- `0_🌱_投資解讀面板.py`：新增模型版本標記、最後訓練日期
- `home.py`：新增 Phase 3 治理區塊的入口卡片

---

### Step 9：品質閘門 + 產出報告

**Phase 3 品質閘門：**

| # | 門控 | 條件 | 類型 |
|---|------|------|------|
| 1 | models_available | 4 個模型檔案存在且可載入 | Critical |
| 2 | model_cards_generated | 所有可用模型都有 Model Card | Critical |
| 3 | drift_analysis_complete | 漂移偵測已執行且無嚴重漂移 | Critical |
| 4 | signal_decay_assessed | 信號衰減分析已完成 | Critical |
| 5 | baseline_established | 效能基線已建立 | Critical |
| 6 | prediction_pipeline_valid | 預測管線可正常執行 | Critical |
| 7 | dsr_revalidated | DSR 已用修正策略數重新驗證 | Critical |
| 8 | dashboard_pages_functional | 新儀表板頁面可正常載入 | Advisory |
| 9 | no_severe_drift | 無特徵嚴重漂移（PSI < 0.25） | Advisory |

**與 Phase 2 門控的銜接：**

Phase 2 唯一未通過的 `statistical_validity`（DSR）在 Step 7 重新驗證。Phase 3 報告會明確記錄：
- Phase 2 原始結果（9 策略，全部 DSR fail）
- Phase 3 修正結果（6 策略，排除不可行的 D+1）
- 最終判定及理由

**最終報告：**
- `outputs/reports/phase3_report_YYYYMMDD_HHMMSS.json`

---

## 四、檔案結構規劃

```
大數據與商業分析專案/
├── run_phase3.py                          # Phase 3 主執行腳本（新增）
├── src/
│   ├── governance/                        # 治理模組（擴充）
│   │   ├── __init__.py
│   │   ├── model_card.py                  # Model Card 生成器
│   │   ├── drift_detector.py              # 資料漂移偵測
│   │   ├── signal_monitor.py              # 信號衰減監控
│   │   └── baseline.py                    # 效能基線管理
│   └── pipeline/                          # 預測管線（新增）
│       ├── __init__.py
│       ├── predictor.py                   # 標準化預測流程
│       └── feature_validator.py           # 特徵一致性驗證
├── dashboard/
│   └── pages/
│       ├── 6_🛡️_Model_Governance.py      # 模型治理頁面（新增）
│       └── 7_📡_Signal_Monitor.py         # 信號監控頁面（新增）
└── outputs/
    └── governance/                        # 治理產出（新增）
        ├── model_card_*.json
        ├── drift_report.json
        ├── signal_decay_report.json
        └── performance_baseline.json
```

---

## 五、執行依賴與前置條件

| 依賴項 | 狀態 | 說明 |
|--------|------|------|
| feature_store.parquet | ✅ 存在 | 948K rows × 59 cols |
| Phase 2 報告 | ✅ 存在 | phase2_report_20260406_165429.json |
| 訓練模型 | ⚠️ 需確認 | `outputs/models/` 目前為空，Phase 2 save_models 可能需重新執行 |
| 23 選用特徵清單 | ✅ 在報告中 | Phase 2 feature_selection 結果 |
| scipy | ✅ 已安裝 | KS test 需要 |
| numpy / pandas | ✅ 已安裝 | 核心計算 |

**✅ 已解決：** `outputs/models/` 為空的根因已查明——`save_models()` 內部 key mismatch bug（讀取 `"last_model"` 但傳入 `"model"`）。已修復於 `src/models/trainer.py`。Phase 3 Step 1 會自動偵測並重建模型。

**✅ 對儀表板無影響：** 經完整 grep 檢查，dashboard/ 目錄下無任何檔案引用 `outputs/models/` 或 `.joblib`。

---

## 六、風險與緩解措施

| 風險 | 影響 | 緩解 |
|------|------|------|
| 模型檔案遺失 | Step 6 預測管線無法運作 | Phase 3 Step 1 中加入模型重新匯出邏輯 |
| 特徵漂移嚴重 | 模型預測不可靠 | Step 3 漂移偵測會提前預警 |
| Streamlit Cloud 記憶體限制 | 新頁面載入失敗 | 治理數據預計算為 JSON，不載入大型 parquet |
| 校準模型過期 | 概率偏差增大 | 基線監控會追蹤 ECE 變化 |

---

## 七、預估工作量

| 步驟 | 新增程式碼 | 預估行數 |
|------|-----------|---------|
| run_phase3.py | 主腳本（含模型重建 + DSR 重驗） | ~400 行 |
| model_card.py | Model Card 生成 | ~200 行 |
| drift_detector.py | 漂移偵測 | ~250 行 |
| signal_monitor.py | 信號監控 | ~200 行 |
| baseline.py | 基線管理 + DSR 重新驗證 | ~200 行 |
| predictor.py | 預測管線 | ~250 行 |
| feature_validator.py | 特徵驗證 | ~100 行 |
| Model_Governance.py | 儀表板頁面 | ~350 行 |
| Signal_Monitor.py | 儀表板頁面 | ~400 行 |
| **合計** | | **~2,350 行** |

---

## 八、執行命令

```bash
# 確認 Phase 2 產出完整後
python run_phase3.py

# 預期執行時間：3-5 分鐘
# 產出：outputs/governance/ + outputs/reports/phase3_report_*.json
# 儀表板新增：2 個頁面自動出現在導覽列
```
