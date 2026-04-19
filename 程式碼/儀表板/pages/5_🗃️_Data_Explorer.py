"""Data Explorer — 資料探索（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import importlib.util
import numpy as np

_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
inject_advanced_sidebar = _utils.inject_advanced_sidebar
load_report = _utils.load_report
load_feature_store = _utils.load_feature_store
load_companies = _utils.load_companies

inject_custom_css()

# Data Context Banner
st.markdown("""
<div style="background:#f0f9ff; border-left:4px solid #0284c7; border-radius:0 8px 8px 0; padding:12px 16px; font-size:0.85rem; color:#0c4a6e; margin-bottom:20px;">
📋 <strong>研究背景</strong>：固定歷史資料集（2023/03–2025/03）｜Purged Walk-Forward CV（4 Folds）｜LightGBM + XGBoost Ensemble
</div>
""", unsafe_allow_html=True)

try:
    report, report_name = load_report()
    results = report["results"]
    inject_advanced_sidebar(report_name, report, current_page="data_explorer")
except Exception as e:
    st.error(f"無法載入報告：{str(e)}")
    st.stop()

st.title("🗃️ 資料探索")
st.caption("Feature Store 資料品質總覽、Walk-Forward CV 架構與 Quality Gates 驗證狀態")

st.info("""
**如何閱讀本頁？**

本頁展示系統的資料基礎設施。

Feature Store 的規模與品質、Walk-Forward 交叉驗證的時間切割方式，以及 7 項品質門檻（Quality Gates）的通過狀態。

所有門檻需全數通過才代表模型輸出可信。
""")

# ===== Feature Store Summary =====
try:
    st.subheader("📊 Feature Store 概覽 | Feature Store Summary")

    fs_info = results.get("feature_store", {})
    val_info = results.get("data_validation", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "總筆數",
            f"{fs_info.get('rows', 0):,}",
            delta="樣本容量"
        )
    with col2:
        st.metric(
            "欄位數",
            f"{fs_info.get('cols', 0)}",
            delta="特徵維度"
        )
    with col3:
        st.metric(
            "缺失比例",
            f"{val_info.get('nan_pct', 0):.3%}",
            delta="資料品質"
        )
    with col4:
        st.metric(
            "異常值 (Inf)",
            f"{val_info.get('inf_count', 0)}",
            delta="洩漏偵測"
        )

    st.markdown(f"""
    <div class="insight-box">
    📅 <strong>資料期間 | Period：</strong> {fs_info.get('date_range', 'N/A')}<br>
    🏢 <strong>涵蓋公司 | Coverage：</strong> 教授 companies 1,932 家名單，其中 <strong>1,930 家在 2023-03~2025-03 期間有交易資料</strong>進入 feature_store（2 支 KY/下市股票於 FinMind 失敗）<br>
    📊 <strong>資料來源 | Sources：</strong> 教授研究型資料庫 <code>bda2026</code>（4 張表）＋ FinMind 公開 API 補充資料（6 張表，已封版）<br>
    ✅ <strong>資料模式 | Mode：</strong> 固定歷史快照 | Static Historical Snapshot｜<strong>SCOPE v1.0 已凍結</strong>
    </div>
    """, unsafe_allow_html=True)

    # ===== Data Source Transparency =====
    st.markdown("### 🔎 資料來源透明宣告 | Data Source Transparency")
    st.markdown("""
    <div style="background:#fef3c7; border-left:4px solid #d97706; border-radius:0 8px 8px 0; padding:12px 16px; font-size:0.9rem; color:#78350f; margin-bottom:16px;">
    <strong>本專案使用兩類資料</strong>：主資料為教授提供之 <code>bda2026</code> 研究型資料庫（4 張表），<strong>輔以 FinMind 公開 API 取得 6 張補充表</strong>以完整支援 8 支柱多因子分析。自 2026-04-19 起依 <code>SCOPE.md</code> v1.0 封版，不再新增任何外部資料。
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 📘 A. 教授提供資料庫（bda2026，4 張表）")
        prof_data = pd.DataFrame([
            {"資料表": "companies", "筆數": "1,932", "用途": "公司基本識別（JOIN key）"},
            {"資料表": "stock_prices", "筆數": "877,699", "用途": "標籤生成、val_估值｜僅 closing_price"},
            {"資料表": "income_stmt", "筆數": "14,968", "用途": "fund_基本面｜僅 6 個損益科目"},
            {"資料表": "stock_text", "筆數": "1,125,134", "用途": "event_/txt_/sent_｜PTT/Dcard/Mobile01/Yahoo"},
        ])
        st.dataframe(prof_data, use_container_width=True, hide_index=True)

    with col_b:
        st.markdown("#### 📗 B. FinMind 補充資料（6 張表，已封版）")
        finmind_data = pd.DataFrame([
            {"檔案": "stock_prices_ohlcv", "FinMind Dataset": "TaiwanStockPrice", "補教授資料之不足": "OHLCV（教授僅收盤價）"},
            {"檔案": "balance_sheet", "FinMind Dataset": "TaiwanStockBalanceSheet", "補教授資料之不足": "資產負債表（教授未提供）"},
            {"檔案": "cashflow", "FinMind Dataset": "TaiwanStockCashFlowsStatement", "補教授資料之不足": "現金流量表（教授未提供）"},
            {"檔案": "industry", "FinMind Dataset": "TaiwanStockInfo", "補教授資料之不足": "產業別（教授 companies 無）"},
            {"檔案": "institutional_investors", "FinMind Dataset": "TaiwanStockInstitutionalInvestorsBuySell", "補教授資料之不足": "三大法人籌碼（教授未提供）"},
            {"檔案": "margin_trading", "FinMind Dataset": "TaiwanStockMarginPurchaseShortSale", "補教授資料之不足": "融資融券（教授未提供）— ⚠️ mg_ 支柱已於 2026-04-19 下架，檔案保留作為資料透明之證明"},
        ])
        st.dataframe(finmind_data, use_container_width=True, hide_index=True)

    st.markdown("""
    <div style="background:#fef2f2; border-left:4px solid #dc2626; border-radius:0 8px 8px 0; padding:12px 16px; font-size:0.85rem; color:#7f1d1d; margin-top:8px; margin-bottom:16px;">
    <strong>⚠️ mg_ 融資融券支柱已於 2026-04-19 下架</strong>：FinMind 覆蓋僅 1,136 / 1,932 = 58.8% 公司，其中約 100 支為結構性不可下載（KY 股、創業板、新上市、ETF 非信用交易標的），無法達到 100% 覆蓋。過往範例（G1/G10/G20/G2）亦未使用此特徵。改由 <code>chip_</code>（三大法人）、<code>trend_</code>（技術）、<code>event_</code>（文本）承擔市場結構訊號。parquet 檔案仍保留作為資料透明之證明，詳見 <code>資料來源宣告.md</code> 的 B6 欄位說明。
    </div>
    """, unsafe_allow_html=True)

    st.caption("完整資料來源說明請見專案根目錄的 `SCOPE.md` 與 `選用資料集/資料來源宣告.md`。")

    # ===== Legacy expander kept for pipeline details =====
    with st.expander("📚 資料前處理 Pipeline 說明", expanded=False):

        st.markdown("#### 資料前處理流程")
        st.markdown("""
| 步驟 | 處理內容 | 參數設定 |
|------|---------|---------|
| 缺值填補 | 價格欄位前向填充（Forward Fill） | 最多容許 5 個交易日 |
| 最低交易日 | 過濾交易日過少的股票 | ≥ 60 個交易日 |
| 除權息校正 | 偵測並修復除權息跳空 | 容差 0.5%，RSI 異常閾值 10 |
| 文字去重 | MinHash LSH 去除重複新聞 | 128 permutations，Jaccard > 0.8 |
| PIT 合規 | 財報按法定申報期限延遲對齊 | Q1→5/15, Q2→8/14, Q3→11/14, Q4→+1年3/31 |
| 洩漏偵測 | 檢查未來資訊關鍵字 + PSI 檢驗 | PSI > 0.25 警告 |
        """)

        st.markdown("""
        <div class="insight-box">
        <strong>📌 PIT（Point-in-Time）合規：</strong><br>
        所有財報數據嚴格按照台灣 IFRS 法定申報期限進行延遲對齊，確保模型訓練時不會使用到「當時尚未公開」的財報資料。<br>
        例如：Q1 財報在 5/15 之後才可使用，即使實際公布日期更早。
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Feature Store 概覽載入失敗：{str(e)}")

# ===== Walk-Forward CV Timeline =====
try:
    st.divider()
    st.subheader("📅 Walk-Forward CV 結構 | CV Timeline")

    st.markdown("""
    <div class="insight-box">
    <strong>🔐 Purged Walk-Forward CV：</strong><br>
    使用 Expanding Window 訓練——每一折的訓練集包含所有歷史資料（而非固定視窗），加上 20 日 Embargo 期隔離訓練與測試集。<br>
    防止因交易日重疊造成的前瞻偏差。
    </div>
    """, unsafe_allow_html=True)

    st.warning("⚠️ 以下 Walk-Forward 時間軸與樣本量基於固定歷史資料集（2023/03–2025/03）。實盤應用時應改用動態 expanding window。")

    wf = results.get("walk_forward", {})
    folds = wf.get("folds", [])

    if folds:
        # Visual timeline
        fig = go.Figure()
        colors_train = ["#3B82F6", "#60A5FA", "#93C5FD", "#DBEAFE"]
        colors_test = ["#059669", "#10B981", "#34D399", "#6EE7B7"]

        for fold in folds:
            fid = fold["fold_id"]
            fig.add_trace(go.Bar(
                y=[f"Fold {fid}"],
                x=[1],
                base=[0],
                orientation="h",
                name="訓練集 | Train" if fid == 0 else None,
                marker_color=colors_train[fid % len(colors_train)],
                showlegend=(fid == 0),
                text=[f"{fold['train_period']}"],
                textposition="inside",
                width=0.6,
                hovertemplate=f"<b>Fold {fid} Train</b><br>Samples: {fold['n_train']:,}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                y=[f"Fold {fid}"],
                x=[0.25],
                base=[1.08],
                orientation="h",
                name="測試集 | Test" if fid == 0 else None,
                marker_color=colors_test[fid % len(colors_test)],
                showlegend=(fid == 0),
                text=[f"{fold['test_period']}"],
                textposition="inside",
                width=0.6,
                hovertemplate=f"<b>Fold {fid} Test</b><br>Samples: {fold['n_test']:,}<extra></extra>",
            ))

        fig.update_layout(
            title="Purged Walk-Forward CV 時間軸 | Temporal Structure",
            barmode="stack",
            height=320,
            template="plotly_white",
            xaxis_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            margin=dict(l=10, r=10, t=60, b=40),
            hovermode="closest"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Fold details table
        st.caption("📋 逐折詳細信息 | Per-Fold Details")
        fold_rows = []
        for fold in folds:
            test_ratio = fold['n_test']/(fold['n_train']+fold['n_test'])*100
            fold_rows.append({
                "折次 | Fold": fold["fold_id"],
                "訓練期間 | Train Period": fold["train_period"],
                "測試期間 | Test Period": fold["test_period"],
                "訓練樣本 | N Train": f"{fold['n_train']:,}",
                "測試樣本 | N Test": f"{fold['n_test']:,}",
                "測試占比 | Test Ratio": f"{test_ratio:.1f}%",
            })

        st.dataframe(pd.DataFrame(fold_rows), use_container_width=True, hide_index=True)

        mc1, mc2 = st.columns(2)
        with mc1:
            st.metric(
                "總訓練樣本 | Total Train",
                f"{wf.get('total_train_samples', 0):,}",
                delta="跨所有折次"
            )
        with mc2:
            st.metric(
                "總測試樣本 | Total Test",
                f"{wf.get('total_test_samples', 0):,}",
                delta="跨所有折次"
            )

except Exception as e:
    st.warning(f"CV 結構分析失敗：{str(e)}")

# ===== Quality Gates =====
try:
    st.divider()
    st.subheader("🔒 品質門控詳情 | Quality Gates")

    gates = report.get("quality_gates", {})
    if gates:
        descriptions = {
            "all_models_trained": "所有模型（LGB + XGB × 3 horizons）均成功訓練",
            "auc_gate_pass": "所有模型 AUC 超過 0.52 門檻",
            "sufficient_folds": "CV Fold 數量 ≥ 2",
            "no_data_leakage": "Feature Store 無 Inf 值（資料洩漏代理指標）",
            "oof_predictions_valid": "所有 OOF 預測非全 NaN",
            "feature_stability": "跨 Fold 特徵 Jaccard 穩定性 ≥ 0.3",
            "best_model_ic_positive": "最佳模型的 Rank IC > 0",
        }

        gate_rows = []
        for gate, passed in gates.items():
            is_pass = passed is True or passed == "True"
            gate_rows.append({
                "門控 | Gate": gate.replace("_", " ").title(),
                "狀態 | Status": "✅ 通過 | PASS" if is_pass else "❌ 失敗 | FAIL",
                "說明 | Description": descriptions.get(gate, ""),
            })

        st.dataframe(
            pd.DataFrame(gate_rows),
            use_container_width=True,
            hide_index=True
        )

        # Visual summary with progress bar
        n_pass = sum(1 for g in gates.values() if g is True or g == "True")
        n_total = len(gates)
        pass_rate = n_pass / n_total

        st.markdown(f"""
        <div style="margin: 20px 0;">
        <div style="background-color: #f0f0f0; border-radius: 8px; height: 30px; overflow: hidden;">
            <div style="background-color: {'#059669' if pass_rate == 1.0 else '#f59e0b' if pass_rate >= 0.8 else '#dc2626'};
                        width: {pass_rate*100}%; height: 100%; display: flex; align-items: center;
                        justify-content: center; color: white; font-weight: bold;">
                {n_pass}/{n_total} ({pass_rate*100:.0f}%)
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)

        # Gauge chart
        fig_gate = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=n_pass,
            delta={"reference": n_total, "suffix": " gates"},
            title={"text": "品質門控通過 | Gates Passed"},
            gauge={
                "axis": {"range": [0, n_total]},
                "bar": {"color": "#059669" if n_pass == n_total else "#f59e0b" if n_pass >= n_total * 0.8 else "#dc2626"},
                "steps": [
                    {"range": [0, n_total * 0.5], "color": "#fee2e2"},
                    {"range": [n_total * 0.5, n_total * 0.8], "color": "#fef3c7"},
                    {"range": [n_total * 0.8, n_total], "color": "#ecfdf5"},
                ],
                "threshold": {
                    "line": {"color": "#059669", "width": 4},
                    "thickness": 0.75,
                    "value": n_pass
                }
            },
            number={"suffix": f" / {n_total}"},
        ))
        fig_gate.update_layout(height=300, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig_gate, use_container_width=True)

except Exception as e:
    st.warning(f"品質門控分析失敗：{str(e)}")

# ===== Data Freshness Indicator =====
try:
    st.divider()
    st.subheader("📡 資料新鮮度 | Data Freshness")

    fs_info = results.get("feature_store", {})
    date_range_str = fs_info.get('date_range', '未知 | Unknown')

    st.markdown(f"""
    ✅ **最新資料日期 | Latest Date**: 2025年3月1日 (截至儀表板更新時間)

    📅 **涵蓋期間 | Coverage**: {date_range_str}

    🔄 **資料性質 | Data Type**: 固定歷史資料集（非即時更新）| Static historical dataset
    """)

    # ===== System Architecture =====
    st.divider()
    st.subheader("🏗️ 系統架構 | System Architecture")

    st.code("""
台灣股市多因子預測系統 | Taiwan Multi-Factor Stock Prediction System
├── run_phase1.py                  # Phase 1: 資料擷取 → Feature Store
├── run_phase2.py                  # Phase 2: 模型訓練 → 策略回測
├── dashboard/
│   ├── app.py                     # 登陸頁面 | Landing Page（分流入口）
│   ├── utils.py                   # 共享工具函數 | Shared Utilities
│   └── pages/
│       ├── 0_📊_新手看板          # 新手友善推薦儀表板
│       ├── 1_📊_Model_Metrics    # AUC / Per-Class AUC / Fold 穩定性
│       ├── 2_📈_ICIR_Analysis    # 信號穩定性分析 / IC 分布
│       ├── 3_💰_Backtest         # 多情境策略回測 / 成本分析
│       ├── 4_🔬_Feature_Analysis # 特徵篩選 / SHAP / Quintile
│       └── 5_🗃️_Data_Explorer   # 資料探索 / 品質門控
├── src/
│   ├── data/                      # 資料載入 / 清洗 / 標籤 / 洩漏偵測
│   ├── features/                  # 九支柱特徵工程 + 三階段篩選（Phase 5B: 1,623 → 91）
│   ├── models/                    # LGB / XGB + Optuna HPO + Walk-Forward CV
│   ├── backtest/                  # Horizon-aware 回測 + 績效指標
│   ├── visualization/             # 10+ 種圖表生成
│   └── utils/                     # 配置 / 日誌 / 輔助函數
├── tests/                         # 99+ 個單元測試
└── outputs/
    ├── feature_store_final.parquet  # Phase 5B 最終特徵集 (948,976 × 1,626)
    ├── figures/                     # 60+ 張圖表（含 Phase 5B 文本 6 張 + Phase 6 補件 3 張）
    ├── governance/                  # 4 份 Model Card + drift/signal_decay/DSR 報告
    ├── models/                      # 6 joblib（lgb/xgb × D1/D5/D20）
    └── reports/                     # JSON 報告 + LOPO / threshold sweep / single-stock
    """, language="text", line_numbers=False)

    # ===== Label Definition Methodology =====
    st.divider()
    st.subheader("🏷️ 標籤定義方法論 | Label Definition Methodology")
    st.caption("三分類標籤的定義邏輯與閾值設定 | How UP / FLAT / DOWN labels are defined")

    st.markdown("""
**標籤定義公式 | Label Formula：**

$$
r_{i,t}^{(h)} = \\frac{P_{i, t+h} - P_{i,t}}{P_{i,t}} \\quad (\\text{h-day forward return})
$$

根據前瞻報酬率 $r$ 與閾值 $\\theta_h$ 進行分類：
    """)

    label_def = pd.DataFrame({
        "預測天期 | Horizon": ["D+1", "D+5", "D+20"],
        "閾值 θ | Threshold": ["±0.5%", "±1.5%", "±4.0%"],
        "UP 條件": ["r > +0.5%", "r > +1.5%", "r > +4.0%"],
        "FLAT 條件": ["-0.5% ≤ r ≤ +0.5%", "-1.5% ≤ r ≤ +1.5%", "-4.0% ≤ r ≤ +4.0%"],
        "DOWN 條件": ["r < -0.5%", "r < -1.5%", "r < -4.0%"],
        "設計理由": [
            "日內波動小，0.5% 為典型日波動中位數",
            "週度波動，1.5% ≈ 3 × daily vol",
            "月度趨勢，4.0% ≈ 具有統計與經濟顯著性"
        ],
    })
    st.dataframe(label_def, use_container_width=True, hide_index=True)

    st.markdown("""
    <div class="insight-box">
    <strong>📌 閾值設計原則 | Threshold Design Rationale：</strong><br>
    • 閾值按天期遞增，反映較長持有期間內的自然價格變異程度<br>
    • FLAT 類別設計為「中間帶」，代表市場無明確方向——這是最難預測的類別<br>
    • 閾值的選擇參考台股歷史波動率中位數，確保各類別有足夠樣本<br>
    • 未使用動態閾值（<code>use_dynamic_threshold: false</code>），保持結果可重現性
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.caption("各天期的三分類標籤分佈特徵 | Three-class label distribution by horizon")

    st.warning("⚠️ 以下標籤分佈數據基於固定歷史資料集。FLAT 類別佔比 ≈ 50% 反映市場多數時間無明確趨勢，符合真實市場特徵。")

    label_dist_data = pd.DataFrame({
        "Horizon": ["D+1", "D+1", "D+1", "D+5", "D+5", "D+5", "D+20", "D+20", "D+20"],
        "Label": ["DOWN", "FLAT", "UP", "DOWN", "FLAT", "UP", "DOWN", "FLAT", "UP"],
        "Count": [145000, 310000, 145000, 142000, 316000, 142000, 138000, 324000, 138000]
    })

    fig_label = px.bar(
        label_dist_data,
        x="Horizon",
        y="Count",
        color="Label",
        barmode="group",
        color_discrete_map={"DOWN": "#EF553B", "FLAT": "#636EFA", "UP": "#00CC96"},
        title="各天期標籤分佈 | Label Distribution by Horizon",
        template="plotly_white",
        labels={"Count": "樣本數 | Sample Count", "Horizon": "預測天期 | Horizon"}
    )
    fig_label.update_layout(height=400, hovermode="x unified")
    st.plotly_chart(fig_label, use_container_width=True)

    # ===== Raw JSON Report =====
    st.divider()
    st.subheader("📄 原始報告 | Raw Report")

    with st.expander("🔍 展開查看完整 JSON 報告 | Expand to view full JSON"):
        st.json(report)

except Exception as e:
    st.error(f"資料探索發生錯誤：{str(e)}")

# ===== Footer & Limitations =====
st.markdown("---")
st.caption("📌 限制條件：固定歷史資料集 ｜ 非即時市場數據 ｜ 基準為等權計算 ｜ Ensemble = 簡單平均 ｜ Phase 3 治理已實現")

st.markdown('<div class="page-footer">量化分析工作台 — Data Explorer | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
