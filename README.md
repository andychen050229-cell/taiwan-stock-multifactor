# 台灣股市多因子預測系統

**Taiwan Stock Multi-Factor Prediction System**

> 大數據與商業分析課程專案 | LightGBM + XGBoost + Ensemble | Purged Walk-Forward CV

## 系統概覽

本系統建構了一套端到端的台灣股市多因子預測管線，涵蓋資料擷取、五支柱特徵工程（43 因子）、三階段特徵篩選（MI → VIF → 穩定性）、Purged Walk-Forward CV 模型訓練、多 horizon 策略回測，以及互動式 Streamlit 儀表板。

### 核心成果

| 指標 | 數值 |
|------|------|
| 最佳策略 | XGBoost D+20 (月度 Rebalance) |
| 年化報酬 (Discount) | +13.92% |
| Sharpe Ratio | 0.72 |
| ICIR (信號穩定性) | 0.77 |
| 基準超額報酬 | +16.35% |
| 單元測試 | 99 個 (全數通過) |
| 12 人團隊評分 | 9.56 / 10 |

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements_app.txt
```

### 2. 執行預測管線

```bash
# Phase 1: 資料擷取 → Feature Store
python run_phase1.py

# Phase 2: 模型訓練 → 策略回測 → 圖表生成
python run_phase2.py
```

### 3. 啟動儀表板

```bash
streamlit run dashboard/app.py
```

### 4. 執行單元測試

```bash
pytest tests/ -v
```

## 系統架構

```
├── run_phase1.py              # Phase 1 管線入口
├── run_phase2.py              # Phase 2 管線入口
├── dashboard/
│   ├── app.py                 # Streamlit 主頁 (Overview)
│   └── pages/
│       ├── 1_📊_Model_Metrics.py    # 模型指標分析
│       ├── 2_📈_ICIR_Analysis.py    # ICIR 信號穩定性
│       ├── 3_💰_Backtest.py         # 策略回測分析
│       ├── 4_🔬_Feature_Analysis.py # 特徵工程分析
│       └── 5_🗃️_Data_Explorer.py    # 資料探索
├── src/
│   ├── data/                  # 資料載入/清洗/標籤/PIT處理
│   ├── features/              # 五支柱特徵工程 + 三階段篩選
│   ├── models/                # LGB/XGB + Optuna HPO + 序列化
│   ├── backtest/              # 回測引擎 + 績效指標 + 進階分析
│   ├── visualization/         # 9 種專業圖表
│   └── utils/                 # Config/Logger/Helpers
├── tests/                     # 99 個 pytest 單元測試
├── outputs/
│   ├── figures/               # 33 張 PNG 圖表
│   ├── reports/               # JSON + DOCX 報告
│   └── models/                # 序列化模型 (joblib)
└── src/config/base.yaml       # 系統配置
```

## 方法論亮點

- **Point-in-Time (PIT)** 財報合併：使用 `merge_asof` 確保僅使用歷史已公開資訊
- **Purged Walk-Forward CV**：Expanding window + 20 天 embargo 防止資訊洩漏
- **ICIR 信號穩定性分析**：D+20 ICIR 達 0.74–0.77，證明月度 alpha 穩定
- **實際換手率計算**：追蹤持倉變動而非固定假設
- **漲跌停偵測**：排除觸及台股 10% 漲跌停限制的股票
- **Bootstrap 信賴區間**：提供報酬與 Sharpe 的 95% CI
- **Quintile 因子分組**：驗證 alpha 信號在分位間的單調性
- **SHAP 可解釋性**：TreeExplainer 揭示模型決策邏輯

## 資料來源

- [FinMind 開放金融資料](https://finmindtrade.com/) — OHLCV + 財務報表
- 課程 MySQL 備份 — 公司基本資料、新聞文本

## 技術棧

Python 3.10+ | LightGBM | XGBoost | Optuna | scikit-learn | SHAP | Streamlit | Plotly | pandas | matplotlib

## Streamlit Cloud 部署

1. Push 至 GitHub repository
2. 前往 [share.streamlit.io](https://share.streamlit.io)
3. 選擇 repo，設定 Main file path 為 `dashboard/app.py`
4. 部署完成

## License

MIT License — 僅供學術研究用途
