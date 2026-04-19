# 台灣股市多因子預測系統

**Taiwan Stock Multi-Factor Prediction System**

> 大數據與商業分析課程專案 | LightGBM + XGBoost + Ensemble | Purged Walk-Forward CV
>
> **版本**：2026-04-19 終版重跑 ｜ **資料期間**：2023-03 ~ 2025-03 ｜ **1,930 家上市櫃**

## 系統概覽

本系統建構了一套端到端的台灣股市多因子預測管線，涵蓋資料擷取、**九支柱特徵工程**（1,623 因子候選池）、三階段特徵篩選（MI → VIF → 穩定性，輸出 91 features）、Purged Walk-Forward CV 模型訓練（4 folds, embargo=20）、多 horizon 策略回測、模型治理與信號監控，以及互動式 Streamlit 儀表板。

**⚠️ 重要聲明**：本平台為**固定歷史資料集**（2023/03 – 2025/03）下的研究展示系統，非即時投資建議或自動交易系統。所有呈現結果皆為歷史回顧。

### 核心成果（xgboost_D20 為最佳策略）

| 指標 | 數值 |
|------|------|
| 最佳策略 | XGBoost D+20 (月度 Rebalance) |
| OOS AUC | **0.6455** |
| Rank IC | **+0.015** |
| 年化報酬 (Standard 0.583%) | **+13.83%** |
| 年化報酬 (Discount 0.356%) | **+17.77%** |
| 年化報酬 (Conservative 0.732%) | **+11.94%** |
| Sharpe Ratio (Discount) | **0.81** |
| ICIR | **–0.015**（IC 平均接近 0 主導了比值方向，詳見下文「統計可辯護性」）|
| Max Drawdown | **–8.70%** |
| DSR（single-best） | **12.12 → PASS** |

> **為何 Sharpe 比舊版 2.02 低？** 2026-04-19 重跑修復了 5 個 Critical Bugs（Phase 4 交叉檢驗審查報告）並收緊 PIT 邏輯、embargo、Purged K-fold，OOS 樣本從「寬鬆 PIT」轉為「嚴格 PIT」，Rank IC 從 0.15 縮至 0.015。新版是現行交件基準。

## 雙面板設計

本平台提供兩種閱讀模式：

- **投資解讀面板**：將研究結果翻譯成投資人可理解的決策資訊，包含歷史判讀、公司基本面、成本分析與風險提示
- **量化研究工作台**：完整呈現模型指標、回測績效、特徵分析、資料品質與治理監控的專業視角

## 快速開始

### 1. 安裝依賴

```bash
pip install -r 程式碼/requirements_app.txt
```

### 2. 設定環境變數

```bash
cp .env.template .env
# 編輯 .env，填入 FINMIND_TOKEN（若需重新抓取 OHLCV 資料）
```

### 3. 執行預測管線（依序）

```bash
# Phase 1: 資料擷取 → Feature Store
python 程式碼/執行Phase1_資料工程.py

# Phase 5B (文本): 斷詞 → 關鍵字 → 情緒 → 整合 → IC 驗證
python 程式碼/執行Phase5B_文本斷詞.py
python 程式碼/執行Phase5B_關鍵字特徵.py
python 程式碼/執行Phase5B_情緒特徵.py
python 程式碼/執行Phase5B_整合特徵.py
python 程式碼/執行Phase5B_IC驗證.py

# Phase 2: 模型訓練 → 策略回測 → 圖表生成
python 程式碼/執行Phase2_模型訓練.py

# Phase 3: 模型治理、信號監控、擴充分析
python 程式碼/執行Phase3_治理監控.py
python 程式碼/執行Phase3_分析擴充.py

# Phase 5B 補件：文本視覺化（6 張）
python 程式碼/執行Phase5B_文本視覺化.py

# Phase 6 補件：出手率 + 單股深度
python 程式碼/執行Phase6_出手率分析.py
python 程式碼/執行Phase6_單股深度.py
```

### 4. 啟動儀表板

```bash
streamlit run 程式碼/儀表板/app.py
```

## 系統架構

```
├── README.md
├── SCOPE.md                        # 專案紅線（資料來源 / 功能 / 時間 / 資源）
├── 程式碼/
│   ├── 執行Phase1_資料工程.py       # Phase 1 入口
│   ├── 執行Phase2_模型訓練.py        # Phase 2 入口
│   ├── 執行Phase3_治理監控.py        # Phase 3 治理入口
│   ├── 執行Phase3_分析擴充.py        # Phase 3 擴充分析
│   ├── 執行Phase5B_文本斷詞.py       # Stage 2.1 斷詞
│   ├── 執行Phase5B_關鍵字特徵.py     # Stage 2.2 txt_*
│   ├── 執行Phase5B_情緒特徵.py       # Stage 2.3 sent_*
│   ├── 執行Phase5B_整合特徵.py       # Stage 2.4 合併入 feature_store_final
│   ├── 執行Phase5B_IC驗證.py         # Stage 2.5 feature IC/ICIR 檢證
│   ├── 執行Phase5B_文本視覺化.py     # 文本圖表（6 張）
│   ├── 執行Phase6_出手率分析.py      # threshold sweep
│   ├── 執行Phase6_單股深度.py        # 聯發科 2454 深度案例
│   ├── src/
│   │   ├── data/                    # PIT 合併 / BS & CF / 斷詞
│   │   ├── features/                # 九支柱特徵（含 txt_/sent_）+ 篩選
│   │   ├── models/                  # LGB / XGB + Optuna + Calibration
│   │   ├── backtest/                # 成本情境回測 + Bootstrap + DSR
│   │   ├── governance/              # Model Card / Drift / Baseline
│   │   └── visualization/           # 圖表生成
│   └── 儀表板/                      # Streamlit 10 頁
│       ├── app.py                   # st.navigation router
│       ├── utils.py                 # 共用載入器
│       └── pages/
│           ├── home.py                     # 首頁
│           ├── 0_🌱_投資解讀面板.py         # 投資解讀
│           ├── 1_📊_Model_Metrics.py       # 模型指標
│           ├── 2_📈_ICIR_Analysis.py       # ICIR
│           ├── 3_💰_Backtest.py            # 回測
│           ├── 4_🔬_Feature_Analysis.py    # 特徵分析
│           ├── 5_🗃️_Data_Explorer.py       # 資料品質
│           ├── 6_🛡️_Model_Governance.py    # 治理
│           ├── 7_📡_Signal_Monitor.py      # 信號監控
│           ├── 8_🎯_Extended_Analytics.py  # 擴充分析
│           └── 9_📝_Text_Analysis.py       # 文本分析（wordcloud / keyword / sent）
├── outputs/
│   ├── feature_store_final.parquet  # 948,976 rows × 1,623 cols
│   ├── figures/                     # 55+ PNG（Phase 2 + 3 + 5B 文本 + 6 補件）
│   ├── reports/                     # phase1/2/3 JSON + phase3_analytics JSON
│   ├── governance/                  # model_card_*.json + drift / baseline
│   └── models/                      # LGB/XGB joblib（D1/D5/D20）
├── 進度報告/
│   ├── Phase4_終版綜合報告.md       # 交件主文件
│   └── Phase4_交叉檢驗審查報告.md   # 04-09 歷史快照
└── 選用資料集/
    ├── bda2026_backup_20260326.sql  # 教授 A 4 表
    └── parquet/                     # FinMind 補充 6 表
```

## 九支柱特徵體系

| 支柱 | 特徵數 | 說明 |
|---|---|---|
| `trend_` | 25 | MA/EMA/ATR/BB/RSI/MACD/KDJ/OBV 等技術面 |
| `fund_` | 18 | ROE/ROA/ROIC/NOPAT/毛利率/YoY 成長 |
| `val_` | 5 | P/B、P/S、EV/EBITDA、earning yield |
| `event_` | 7 | 新聞提及次數、比率、事件情緒 |
| `risk_` | 6 | 歷史波動、regime composite |
| `chip_` | 10 | 外資/投信/自營買賣超、持股比例 |
| `ind_` | 4 | 產業相對強弱、產業中性化因子 |
| `txt_` | **1,521** | 500 keyword × 3 rolling window + 21 volume |
| `sent_` | **11** | polarity / pos_ratio / neg_ratio / spread / volatility / reversal |

**總候選池 1,623 → MI/VIF/Stability 篩至 91 features（Phase 2 訓練用）**

## 三階段方法論

### Phase 1 — 資料工程
Point-in-Time (PIT) 財報合併（`merge_asof(direction="backward")`）、九支柱特徵工程、洩漏偵測、品質閘門

### Phase 2 — 模型開發與回測
Purged Walk-Forward CV（4 folds, embargo=20）、LightGBM/XGBoost + Optuna HPO、ICIR 信號穩定性、三成本情境回測（0.356% / 0.583% / 0.732%）、Bootstrap 信賴區間、Permutation Test、Deflated Sharpe Ratio

### Phase 3 — 模型治理與監控 + 擴充分析
Model Card 生成、PSI + KS 資料漂移、信號衰減分析、績效基線建立、DSR 重驗證；補充成本敏感度熱圖、跨 horizon 比較、支柱貢獻、龍頭個股命中率

### Phase 5B — 文本 × 情緒因子
斷詞（jieba 財經詞典 + 停用詞）、Chi² + MI + Lift 三重關鍵字篩選（9,655 → 500）、SnowNLP 極性 + 辭典輔助情緒打分、PIT 時間對齊

### Phase 4 — 深度基本面擴充
資產負債表 + 現金流量表整合、ROE/ROA/ROIC/NOPAT/EBITDA 衍生指標、P/B/P/S/EV-EBITDA 估值因子、市場寬度/波動率期限結構/複合機制指標

## 統計可辯護性（重要）

- **Rank IC 0.015 vs 舊版 0.15**：2026-04-19 收緊 PIT 後縮水，但 AUC 仍維持 0.64~0.65，屬「分類可辨、排序微弱」的合理樣態
- **Bootstrap 95% CI 全部含 0**：OOS 僅 ~12 個月，樣本量不足以證明統計顯著；報告中所有績效皆附 CI
- **DSR（Deflated Sharpe Ratio）**：xgboost_D20 單一策略下的 DSR stat=12.12，**PASS**；若以 9 策略多重比較會 FAIL，我們僅宣稱 single-best

## 資料來源

- [FinMind 開放金融資料](https://finmindtrade.com/) — OHLCV + 損益表 + 資產負債表 + 現金流量表 + 產業 + 籌碼
- 教授資料庫 `bda2026_backup_20260326.sql` — `companies` / `stock_prices` / `income_stmt` / `stock_text`（1.12M 篇文章）

> 詳見 [`SCOPE.md`](./SCOPE.md) — 本專案「資料來源紅線」，自 2026-04-19 起封版。

## 技術棧

Python 3.10+ | LightGBM | XGBoost | Optuna | scikit-learn | SHAP | jieba | SnowNLP | wordcloud | Streamlit | Plotly | pandas | matplotlib

## Streamlit Cloud 部署

1. Push 至 GitHub repository
2. 前往 [share.streamlit.io](https://share.streamlit.io)
3. 選擇 repo，設定 Main file path 為 `程式碼/儀表板/app.py`
4. 部署完成

## License

MIT License — 僅供學術研究用途
