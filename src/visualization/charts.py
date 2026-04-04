"""
視覺化模組 — Phase 2
生成專業級圖表，輸出至 outputs/figures/
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from pathlib import Path
from loguru import logger

# 全域風格設定
plt.rcParams.update({
    "figure.figsize": (12, 6),
    "figure.dpi": 150,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

COLORS = {
    "lightgbm": "#2196F3",
    "xgboost": "#FF9800",
    "ensemble": "#4CAF50",
    "benchmark": "#9E9E9E",
    "positive": "#4CAF50",
    "negative": "#F44336",
    "neutral": "#9E9E9E",
}


def _save(fig, path, tight=True):
    """Save figure and close."""
    if tight:
        fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info(f"  Chart saved: {Path(path).name}")


# ============================================================
# 1. Cumulative Return Curves
# ============================================================

def plot_cumulative_returns(
    backtest_results: dict,
    benchmark_returns: pd.Series,
    horizon: int,
    output_dir: str,
):
    """
    Plot cumulative return curves for all models vs benchmark.
    backtest_results: {engine: {cost_scenario: metrics_with_daily_returns}}
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    # Benchmark
    if benchmark_returns is not None and len(benchmark_returns) > 0:
        cum_bm = (1 + benchmark_returns).cumprod()
        ax.plot(cum_bm.index, cum_bm.values, color=COLORS["benchmark"],
                linewidth=2, linestyle="--", label="Benchmark (Equal-Weight)", alpha=0.8)

    # Each engine (discount cost scenario)
    for engine, engine_data in backtest_results.items():
        if "daily_returns" not in engine_data:
            continue
        daily_ret = engine_data["daily_returns"]
        cum = (1 + daily_ret).cumprod()
        color = COLORS.get(engine, "#607D8B")
        ax.plot(cum.index, cum.values, color=color, linewidth=2,
                label=f"{engine.upper()} (D+{horizon})")

    ax.axhline(y=1.0, color="black", linewidth=0.5, linestyle="-", alpha=0.3)
    ax.set_title(f"Cumulative Returns — D+{horizon} Strategy", fontweight="bold", fontsize=15)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return (1 = start)")
    ax.legend(loc="best", framealpha=0.9)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.2f}"))

    _save(fig, f"{output_dir}/cumulative_returns_D{horizon}.png")


# ============================================================
# 2. Drawdown Chart
# ============================================================

def plot_drawdown(
    backtest_results: dict,
    horizon: int,
    output_dir: str,
):
    """Plot drawdown curves for each engine."""
    fig, ax = plt.subplots(figsize=(14, 5))

    for engine, engine_data in backtest_results.items():
        if "daily_returns" not in engine_data:
            continue
        daily_ret = engine_data["daily_returns"]
        cum = (1 + daily_ret).cumprod()
        peak = cum.cummax()
        dd = (cum - peak) / peak
        color = COLORS.get(engine, "#607D8B")
        ax.fill_between(dd.index, dd.values, 0, color=color, alpha=0.3, label=f"{engine.upper()}")
        ax.plot(dd.index, dd.values, color=color, linewidth=1)

    ax.set_title(f"Drawdown — D+{horizon} Strategy", fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.legend(loc="lower left")

    _save(fig, f"{output_dir}/drawdown_D{horizon}.png")


# ============================================================
# 3. IC Time Series
# ============================================================

def plot_ic_time_series(
    ic_series: pd.Series,
    horizon: int,
    engine: str,
    output_dir: str,
):
    """Plot daily Rank IC time series with rolling mean."""
    fig, ax = plt.subplots(figsize=(14, 5))

    ic_clean = ic_series.dropna()
    if len(ic_clean) == 0:
        plt.close(fig)
        return

    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in ic_clean.values]
    ax.bar(range(len(ic_clean)), ic_clean.values, color=colors, alpha=0.5, width=1.0)

    # Rolling 20-day mean
    if len(ic_clean) >= 20:
        rolling_ic = ic_clean.rolling(20).mean()
        ax.plot(range(len(ic_clean)), rolling_ic.values, color="#1565C0",
                linewidth=2, label="20-day Rolling Mean IC")

    ax.axhline(y=0, color="black", linewidth=0.8, alpha=0.5)

    ic_mean = ic_clean.mean()
    ic_std = ic_clean.std()
    icir = ic_mean / ic_std if ic_std > 0 else 0

    ax.set_title(
        f"Daily Rank IC — {engine.upper()} D+{horizon}\n"
        f"Mean IC={ic_mean:.4f} | Std={ic_std:.4f} | ICIR={icir:.3f}",
        fontweight="bold"
    )
    ax.set_xlabel("Trading Days")
    ax.set_ylabel("Rank IC (Spearman)")
    if len(ic_clean) >= 20:
        ax.legend(loc="best")

    _save(fig, f"{output_dir}/ic_timeseries_{engine}_D{horizon}.png")

    return {"mean_ic": round(ic_mean, 4), "std_ic": round(ic_std, 4), "icir": round(icir, 4)}


# ============================================================
# 4. Feature Importance Bar Chart
# ============================================================

def plot_feature_importance(
    importance: dict,
    engine: str,
    horizon: int,
    output_dir: str,
    top_n: int = 20,
):
    """Horizontal bar chart of top feature importances."""
    if not importance:
        return

    sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
    features = [x[0] for x in sorted_imp][::-1]
    values = [x[1] for x in sorted_imp][::-1]

    fig, ax = plt.subplots(figsize=(10, max(6, len(features) * 0.35)))

    # Color by feature category
    cat_colors = {
        "trend_": "#2196F3", "fund_": "#4CAF50", "val_": "#FF9800",
        "event_": "#9C27B0", "risk_": "#F44336",
    }
    colors = []
    for f in features:
        c = "#607D8B"
        for prefix, col in cat_colors.items():
            if f.startswith(prefix):
                c = col
                break
        colors.append(c)

    bars = ax.barh(range(len(features)), values, color=colors, alpha=0.85)
    ax.set_yticks(range(len(features)))
    ax.set_yticklabels(features, fontsize=9)
    ax.set_xlabel("Importance")
    ax.set_title(f"Top-{top_n} Feature Importance — {engine.upper()} D+{horizon}", fontweight="bold")

    # Legend for categories
    from matplotlib.patches import Patch
    legend_items = [
        Patch(color="#2196F3", label="Trend"),
        Patch(color="#4CAF50", label="Fundamental"),
        Patch(color="#FF9800", label="Valuation"),
        Patch(color="#9C27B0", label="Event"),
        Patch(color="#F44336", label="Risk"),
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=9)

    _save(fig, f"{output_dir}/feature_importance_{engine}_D{horizon}.png")


# ============================================================
# 5. Confusion Matrix Heatmap
# ============================================================

def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    engine: str,
    horizon: int,
    output_dir: str,
):
    """Plot confusion matrix as heatmap."""
    from sklearn.metrics import confusion_matrix

    valid = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if valid.sum() < 10:
        return

    cm = confusion_matrix(y_true[valid].astype(int), y_pred[valid].astype(int), labels=[0, 1, 2])
    cm_pct = cm / cm.sum(axis=1, keepdims=True) * 100

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm_pct, cmap="Blues", vmin=0, vmax=100)

    labels = ["DOWN", "FLAT", "UP"]
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("Actual", fontsize=12)
    ax.set_title(f"Confusion Matrix (%) — {engine.upper()} D+{horizon}", fontweight="bold")

    for i in range(3):
        for j in range(3):
            color = "white" if cm_pct[i, j] > 50 else "black"
            ax.text(j, i, f"{cm_pct[i,j]:.1f}%\n({cm[i,j]:,})",
                    ha="center", va="center", color=color, fontsize=10)

    fig.colorbar(im, ax=ax, shrink=0.8, label="Percentage (%)")

    _save(fig, f"{output_dir}/confusion_matrix_{engine}_D{horizon}.png")


# ============================================================
# 6. Monthly Returns Heatmap
# ============================================================

def plot_monthly_returns(
    daily_returns: pd.Series,
    engine: str,
    horizon: int,
    output_dir: str,
):
    """Monthly returns heatmap table."""
    if len(daily_returns) == 0:
        return

    # Ensure datetime index
    if not isinstance(daily_returns.index, pd.DatetimeIndex):
        daily_returns.index = pd.to_datetime(daily_returns.index)

    monthly = daily_returns.resample("M").apply(lambda x: (1 + x).prod() - 1)

    # Build year x month matrix
    years = sorted(monthly.index.year.unique())
    months = range(1, 13)

    data = np.full((len(years), 12), np.nan)
    for i, year in enumerate(years):
        for m in months:
            mask = (monthly.index.year == year) & (monthly.index.month == m)
            vals = monthly[mask]
            if len(vals) > 0:
                data[i, m-1] = vals.iloc[0] * 100  # to percent

    fig, ax = plt.subplots(figsize=(14, max(3, len(years) * 1.2)))

    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=-10, vmax=10)

    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax.set_xticks(range(12))
    ax.set_xticklabels(month_labels)
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels([str(y) for y in years])

    for i in range(len(years)):
        for j in range(12):
            if not np.isnan(data[i, j]):
                color = "white" if abs(data[i, j]) > 5 else "black"
                ax.text(j, i, f"{data[i,j]:+.1f}%", ha="center", va="center",
                        fontsize=9, color=color)

    ax.set_title(f"Monthly Returns (%) — {engine.upper()} D+{horizon}", fontweight="bold")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Return (%)")

    _save(fig, f"{output_dir}/monthly_returns_{engine}_D{horizon}.png")


# ============================================================
# 7. Cross-Horizon Model Comparison
# ============================================================

def plot_model_comparison(
    all_metrics: dict,
    output_dir: str,
):
    """
    Bar chart comparing AUC, Sharpe, IC across all models and horizons.
    all_metrics: {model_label: {"auc": x, "sharpe": y, "ic": z}}
    """
    if not all_metrics:
        return

    labels = list(all_metrics.keys())
    auc_vals = [all_metrics[k].get("auc", 0) for k in labels]
    sharpe_vals = [all_metrics[k].get("sharpe", 0) for k in labels]
    ic_vals = [all_metrics[k].get("ic", 0) for k in labels]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    x = np.arange(len(labels))

    # AUC
    colors_auc = [COLORS.get(l.split("_")[0].lower(), "#607D8B") for l in labels]
    bars = axes[0].bar(x, auc_vals, color=colors_auc, alpha=0.85)
    axes[0].set_title("AUC (macro)", fontweight="bold")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    axes[0].axhline(y=0.5, color="red", linestyle="--", alpha=0.5, label="Random baseline")
    axes[0].set_ylim(0.45, 0.70)
    axes[0].legend(fontsize=9)
    for bar, val in zip(bars, auc_vals):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
                    f"{val:.3f}", ha="center", fontsize=9)

    # Sharpe
    colors_sharpe = [COLORS["positive"] if v > 0 else COLORS["negative"] for v in sharpe_vals]
    bars = axes[1].bar(x, sharpe_vals, color=colors_sharpe, alpha=0.85)
    axes[1].set_title("Sharpe Ratio (Discount Cost)", fontweight="bold")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    axes[1].axhline(y=0, color="black", linewidth=0.8, alpha=0.5)
    for bar, val in zip(bars, sharpe_vals):
        offset = 0.02 if val >= 0 else -0.05
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + offset,
                    f"{val:.2f}", ha="center", fontsize=9)

    # Rank IC
    colors_ic = [COLORS["positive"] if v > 0 else COLORS["negative"] for v in ic_vals]
    bars = axes[2].bar(x, ic_vals, color=colors_ic, alpha=0.85)
    axes[2].set_title("Rank IC (OOF Test-Only)", fontweight="bold")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    axes[2].axhline(y=0, color="black", linewidth=0.8, alpha=0.5)
    for bar, val in zip(bars, ic_vals):
        offset = 0.001 if val >= 0 else -0.003
        axes[2].text(bar.get_x() + bar.get_width()/2, bar.get_height() + offset,
                    f"{val:.4f}", ha="center", fontsize=9)

    fig.suptitle("Cross-Horizon Model Comparison", fontsize=16, fontweight="bold", y=1.02)

    _save(fig, f"{output_dir}/model_comparison.png")


# ============================================================
# 8. Fold Performance Stability
# ============================================================

def plot_fold_stability(
    fold_metrics: dict,
    output_dir: str,
):
    """
    Line chart showing AUC per fold for each model, to visualize stability.
    fold_metrics: {model_label: [fold0_auc, fold1_auc, ...]}
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    for label, auc_list in fold_metrics.items():
        engine = label.split("_")[0].lower()
        color = COLORS.get(engine, "#607D8B")
        linestyle = "-" if "lgb" in label.lower() or "lightgbm" in label.lower() else "--"
        ax.plot(range(len(auc_list)), auc_list, color=color, marker="o",
                linewidth=2, linestyle=linestyle, label=label, markersize=8)

    ax.set_title("AUC Stability Across Walk-Forward Folds", fontweight="bold")
    ax.set_xlabel("Fold")
    ax.set_ylabel("AUC (macro)")
    ax.set_xticks(range(4))
    ax.set_xticklabels(["Fold 0", "Fold 1", "Fold 2", "Fold 3"])
    ax.axhline(y=0.5, color="red", linestyle="--", alpha=0.4, label="Random")
    ax.legend(loc="best", ncol=2)
    ax.set_ylim(0.55, 0.70)

    _save(fig, f"{output_dir}/fold_stability.png")


# ============================================================
# 9. SHAP Summary Plot
# ============================================================

def plot_shap_summary(
    model,
    X_sample: np.ndarray,
    feature_names: list,
    engine: str,
    horizon: int,
    output_dir: str,
    max_samples: int = 5000,
):
    """Generate SHAP summary plot (beeswarm) for a trained model."""
    try:
        import shap

        # Subsample for speed
        if len(X_sample) > max_samples:
            idx = np.random.choice(len(X_sample), max_samples, replace=False)
            X_sample = X_sample[idx]

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)

        # For multiclass, shap_values is a list of arrays — use UP class (index 2)
        if isinstance(shap_values, list):
            sv = shap_values[2]  # UP class
            class_label = "UP"
        else:
            sv = shap_values
            class_label = "ALL"

        fig, ax = plt.subplots(figsize=(10, max(6, len(feature_names) * 0.3)))
        shap.summary_plot(sv, X_sample, feature_names=feature_names,
                         show=False, max_display=20, plot_size=None)
        plt.title(f"SHAP Summary (class={class_label}) — {engine.upper()} D+{horizon}",
                  fontweight="bold", fontsize=13)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/shap_summary_{engine}_D{horizon}.png",
                    bbox_inches="tight", dpi=150, facecolor="white")
        plt.close("all")
        logger.info(f"  Chart saved: shap_summary_{engine}_D{horizon}.png")
    except Exception as e:
        logger.warning(f"  SHAP plot failed ({engine} D+{horizon}): {e}")
