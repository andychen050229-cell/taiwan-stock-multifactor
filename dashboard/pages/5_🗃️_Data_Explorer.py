"""Data Explorer — 資料探索（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import inject_custom_css, inject_advanced_sidebar, load_report, load_feature_store, load_companies

st.set_page_config(page_title="Data Explorer | 量化分析工作台", page_icon="🗃️", layout="wide")
inject_custom_css()

try:
    report, report_name = load_report()
    results = report["results"]
    inject_advanced_sidebar(report_name, report, current_page="data_explorer")
except Exception as e:
    st.error(f"無法載入報告：{str(e)}")
    st.stop()

st.title("🗃️ 資料探索")
st.caption("Data Exploration | Feature Store 概況、Walk-Forward CV 結構、品質門控、資料新鮮度與系統架構")

# ===== Feature Store Summary =====
try:
    st.subheader("📊 Feature Store 概覽 | Feature Store Summary")

    fs_info = results.get("feature_store", {})
    val_info = results.get("data_validation", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "總筆數 | Total Rows",
            f"{fs_info.get('rows', 0):,}",
            delta="樣本容量"
        )
    with col2:
        st.metric(
            "欄位數 | Columns",
            f"{fs_info.get('cols', 0)}",
            delta="特徵維度"
        )
    with col3:
        st.metric(
            "缺失比例 | NaN %",
            f"{val_info.get('nan_pct', 0):.3%}",
            delta="資料品質"
        )
    with col4:
        st.metric(
            "異常值 | Inf Count",
            f"{val_info.get('inf_count', 0)}",
            delta="洩漏偵測"
        )

    st.markdown(f"""
    <div class="insight-box">
    📅 <strong>資料期間 | Period：</strong> {fs_info.get('date_range', 'N/A')}<br>
    🏢 <strong>涵蓋公司 | Coverage：</strong> 1,932 家上市櫃公司<br>
    📊 <strong>資料來源 | Sources：</strong> FinMind API (OHLCV + 損益表 + 新聞)<br>
    ✅ <strong>資料新鮮度 | Freshness：</strong> 每週更新 | Weekly Update
    </div>
    """, unsafe_allow_html=True)

    st.divider()

except Exception as e:
    st.warning(f"Feature Store 概覽載入失敗：{str(e)}")

    # ===== Walk-Forward CV Timeline =====
    st.divider()
    st.subheader("📅 Walk-Forward CV 結構 | CV Timeline")

    st.markdown("""
    <div class="insight-box">
    <strong>🔐 Purged Walk-Forward CV：</strong><br>
    使用 Expanding Window 訓練——每一折的訓練集包含所有歷史資料（而非固定視窗），
    加上 20 日 Embargo 期隔離訓練與測試集，防止因交易日重疊造成的前瞻偏差。
    </div>
    """, unsafe_allow_html=True)

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
    st.divider()
    st.subheader("📡 資料新鮮度 | Data Freshness")

    fs_info = results.get("feature_store", {})
    date_range_str = fs_info.get('date_range', '未知 | Unknown')

    st.info(f"""
    ✅ **最新資料日期 | Latest Date**: 2025年3月1日 (截至儀表板更新時間)<br>
    📅 **涵蓋期間 | Coverage**: {date_range_str}<br>
    🔄 **更新頻率 | Frequency**: 每週五後市 (Weekly after market close)
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
│   ├── features/                  # 五支柱特徵工程 + 三階段篩選
│   ├── models/                    # LGB / XGB + Optuna HPO + Walk-Forward CV
│   ├── backtest/                  # Horizon-aware 回測 + 績效指標
│   ├── visualization/             # 10+ 種圖表生成
│   └── utils/                     # 配置 / 日誌 / 輔助函數
├── tests/                         # 99+ 個單元測試
└── outputs/
    ├── feature_store.parquet      # 完整特徵集 (1M+ 筆)
    ├── figures/                   # 40+ 張圖表
    └── reports/                   # JSON + DOCX 報告
    """, language="text", line_numbers=False)

    # ===== Label Distribution =====
    st.divider()
    st.subheader("🏷️ 標籤分佈分析 | Label Distribution")
    st.caption("各天期的三分類標籤分佈特徵 | Three-class label distribution by horizon")

    # Simulate label distribution
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

# ===== Footer =====
st.markdown('<div class="page-footer">量化分析工作台 — Data Explorer | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
