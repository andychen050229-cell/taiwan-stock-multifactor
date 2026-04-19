"""
回測引擎 — Phase 2 (v2 修正版)

核心修正：
  1. 按 horizon 週期 rebalance（D+5 每 5 天、D+20 每 20 天）
  2. 持倉期間使用實際日報酬累積，非 forward return
  3. 交易成本僅在 rebalance 時產生（買賣差異部分）

策略：
  - Long-only: 買入模型預測 UP 機率最高的前 K% 股票
  - Equal weight
  - 每 horizon 天 rebalance 一次
"""

import numpy as np
import pandas as pd
from loguru import logger

from ..utils.helpers import timer
from .metrics import compute_strategy_metrics, rank_ic


# ============================================================
# 交易成本
# ============================================================

def _round_trip_cost(cost_params: dict) -> float:
    """
    M4 fix: 一次完整買入+賣出的成本比例（台灣稅制非對稱）。

    台灣股市成本結構：
      買入: 手續費(0.1425%) × 折扣 + 滑價
      賣出: 手續費(0.1425%) × 折扣 + 證交稅(0.3%) + 滑價
    證交稅僅在賣出時收取，手續費雙向收取。
    """
    comm = cost_params.get("commission", 0.001425)
    disc = cost_params.get("discount", 1.0)
    tax = cost_params.get("tax", 0.003)       # 證交稅：僅賣出
    slip = cost_params.get("slippage", 0.001)

    buy_cost = comm * disc + slip              # 買入成本
    sell_cost = comm * disc + tax + slip       # 賣出成本（含證交稅）
    return buy_cost + sell_cost


# ============================================================
# 核心回測邏輯（修正版）
# ============================================================

@timer
def run_backtest(
    df: pd.DataFrame,
    model_results: dict,
    folds: list,
    feature_cols: list,
    label_col: str,
    config: dict,
) -> dict:
    """
    正確的 horizon-aware 回測。

    對 D+N 策略：
      1. 每 N 個交易日 rebalance 一次
      2. 選出 UP 機率最高的 top K% 股票
      3. 持有 N 天，以實際日收盤價計算日報酬
      4. Rebalance 時扣除換手部分的交易成本
    """
    bt_config = config.get("backtest", {}).get("strategy", {})
    top_k_pct = bt_config.get("top_k_pct", 0.1)
    cost_models = config.get("cost_model", {})

    horizon = int(label_col.split("_")[-1])
    fwd_ret_col = f"fwd_ret_{horizon}"
    date_col = "trade_date"
    ticker_col = "company_id"
    close_col = "closing_price"

    logger.info(f"\n{'='*60}")
    logger.info(f"Backtesting: {label_col} (horizon={horizon}d, rebalance every {horizon}d)")
    logger.info(f"{'='*60}")

    # 預計算每支股票的日報酬
    df = df.sort_values([ticker_col, date_col]).copy()
    df["_daily_ret"] = df.groupby(ticker_col)[close_col].pct_change()

    # === 漲跌停偵測：排除觸及漲跌停的股票（可能無法成交）===
    PRICE_LIMIT = 0.095  # 略低於 10% 以容忍浮點誤差
    df["_at_limit"] = df["_daily_ret"].abs() >= PRICE_LIMIT
    n_at_limit = df["_at_limit"].sum()
    limit_pct = df["_at_limit"].mean() * 100
    logger.info(f"  Price limit detection: {n_at_limit:,} rows at limit ({limit_pct:.2f}%)")

    # 流動性過濾：排除日均成交量過低的股票（避免不可執行的交易）
    vol_col = next(
        (c for c in ["Trading_Volume", "trade_volume", "volume"] if c in df.columns),
        None,
    )
    if vol_col is not None:
        avg_vol = df.groupby(ticker_col)[vol_col].transform(
            lambda x: x.rolling(20, min_periods=5).mean()
        )
        # 台股 1 張 = 1000 股，500 張 = 500,000 股
        min_volume = config.get("backtest", {}).get("min_avg_volume", 500_000)
        df["_liquid"] = avg_vol >= min_volume
        n_illiquid = (~df["_liquid"]).sum()
        liquid_pct = df["_liquid"].mean() * 100
        logger.info(f"  Liquidity filter: {liquid_pct:.1f}% rows pass (min_avg_vol={min_volume:,})")
    else:
        df["_liquid"] = True
        logger.warning(f"  Volume column not found, skipping liquidity filter")

    all_results = {}

    for engine, res in model_results.items():
        if "error" in res:
            continue

        # 支援從磁碟載入 OOF（記憶體優化）
        if "oof_predictions" in res:
            oof_preds = res["oof_predictions"]
        elif "_oof_path" in res:
            _data = np.load(res["_oof_path"])
            oof_preds = _data["predictions"]
        else:
            oof_preds = None
        if oof_preds is None or np.isnan(oof_preds).all():
            logger.warning(f"  {engine}: no OOF predictions, skipping")
            continue

        logger.info(f"\n  --- {engine.upper()} Backtest ---")

        up_prob = oof_preds[:, 2]

        # === 逐 fold 回測 ===
        all_period_returns = []  # 每個 rebalance 週期的報酬

        for fold in folds:
            test_idx = fold.test_idx
            test_df = df.iloc[test_idx].copy()
            test_df["_up_prob"] = up_prob[test_idx]

            # 取得 test 期間的排序交易日
            test_dates = sorted(test_df[date_col].dropna().unique())
            if len(test_dates) < horizon:
                continue

            # 每 horizon 天 rebalance 一次
            rebalance_points = list(range(0, len(test_dates), max(horizon, 1)))

            for rb_idx in rebalance_points:
                rb_date = test_dates[rb_idx]

                # 在 rebalance 日選股
                day_df = test_df[test_df[date_col] == rb_date]
                day_df = day_df.dropna(subset=["_up_prob", close_col])
                day_df = day_df[day_df["_liquid"]]  # 流動性過濾
                day_df = day_df[~day_df["_at_limit"]]  # 排除漲跌停股票
                if len(day_df) == 0:
                    continue

                n_stocks = max(1, int(len(day_df) * top_k_pct))
                selected = day_df.nlargest(n_stocks, "_up_prob")
                selected_tickers = set(selected[ticker_col].values)

                # 持倉期間：rb_date 後的 horizon 個交易日
                hold_start = rb_idx + 1
                hold_end = min(rb_idx + horizon, len(test_dates) - 1)
                hold_dates = test_dates[hold_start:hold_end + 1]

                if len(hold_dates) == 0:
                    continue

                # 取持倉股票在持倉期間的日報酬
                hold_mask = (
                    test_df[date_col].isin(hold_dates)
                    & test_df[ticker_col].isin(selected_tickers)
                )
                hold_df = test_df[hold_mask]

                # 逐日等權平均報酬
                for hd in hold_dates:
                    day_hold = hold_df[hold_df[date_col] == hd]
                    if len(day_hold) > 0:
                        port_ret = day_hold["_daily_ret"].dropna().mean()
                        if not np.isnan(port_ret):
                            all_period_returns.append({
                                "date": hd,
                                "return": port_ret,
                                "n_stocks": len(day_hold),
                            })

        if not all_period_returns:
            logger.warning(f"  {engine}: no valid returns")
            continue

        # 合併（同一天可能有多個 fold 重疊，取平均）
        returns_df = pd.DataFrame(all_period_returns)
        daily_agg = returns_df.groupby("date").agg(
            {"return": "mean", "n_stocks": "mean"}
        ).sort_index()

        raw_returns = daily_agg["return"]
        n_rebalances = len(set(
            test_dates[i] for fold in folds
            for test_dates in [sorted(df.iloc[fold.test_idx][date_col].dropna().unique())]
            for i in range(0, len(test_dates), max(horizon, 1))
        ))

        # === 計算實際換手率 ===
        actual_turnovers = []
        prev_holdings = set()
        for fold in folds:
            test_idx = fold.test_idx
            test_df_fold = df.iloc[test_idx].copy()
            test_df_fold["_up_prob"] = up_prob[test_idx]
            test_dates_fold = sorted(test_df_fold[date_col].dropna().unique())
            rb_points = list(range(0, len(test_dates_fold), max(horizon, 1)))
            for rb_i in rb_points:
                rb_d = test_dates_fold[rb_i]
                day_d = test_df_fold[test_df_fold[date_col] == rb_d]
                day_d = day_d.dropna(subset=["_up_prob", close_col])
                if len(day_d) == 0:
                    continue
                n_s = max(1, int(len(day_d) * top_k_pct))
                curr_holdings = set(day_d.nlargest(n_s, "_up_prob")[ticker_col].values)
                if prev_holdings:
                    turnover = 1.0 - len(curr_holdings & prev_holdings) / max(len(curr_holdings | prev_holdings), 1)
                    actual_turnovers.append(turnover)
                prev_holdings = curr_holdings
        avg_turnover = np.mean(actual_turnovers) if actual_turnovers else 0.5
        logger.info(f"  Actual avg turnover: {avg_turnover:.1%} (n_rebalances={len(actual_turnovers)})")

        # === 不同成本情境 ===
        # 識別換倉日（每 horizon 個交易日的第一天扣除成本）
        rebalance_dates = set()
        for fold in folds:
            test_idx = fold.test_idx
            test_df_fold = df.iloc[test_idx]
            test_dates_fold = sorted(test_df_fold[date_col].dropna().unique())
            rb_points = list(range(0, len(test_dates_fold), max(horizon, 1)))
            for rb_i in rb_points:
                if rb_i + 1 < len(test_dates_fold):
                    # 成本在持倉開始日扣除（rb_date 的下一個交易日）
                    rebalance_dates.add(test_dates_fold[min(rb_i + 1, len(test_dates_fold) - 1)])

        engine_results = {}
        for cost_name, cost_params in cost_models.items():
            rt_cost = _round_trip_cost(cost_params)

            # 成本僅在換倉日一次性扣除（乘法扣除，非均攤）
            cost_per_rebalance = rt_cost * avg_turnover
            net_returns = raw_returns.copy()
            for rd in rebalance_dates:
                if rd in net_returns.index:
                    net_returns.loc[rd] -= cost_per_rebalance

            metrics = compute_strategy_metrics(net_returns)
            metrics["cost_per_rebalance"] = round(cost_per_rebalance, 6)
            metrics["cost_model"] = cost_name
            metrics["n_rebalances"] = n_rebalances

            engine_results[cost_name] = metrics

            logger.info(
                f"  {cost_name:>12s}: "
                f"Return={metrics['annualized_return']:+.2%} | "
                f"Sharpe={metrics['sharpe_ratio']:.2f} | "
                f"MDD={metrics['max_drawdown']:.2%}"
            )

        # === Rank IC（僅計算 OOF test 資料，避免 train 膨脹 IC）===
        all_test_idx = np.concatenate([f.test_idx for f in folds])
        test_up = up_prob[all_test_idx]
        test_fwd = df.iloc[all_test_idx][fwd_ret_col].values
        valid_ic = ~np.isnan(test_up) & ~np.isnan(test_fwd)
        if valid_ic.sum() > 100:
            ic_val = rank_ic(
                pd.Series(test_up[valid_ic]).reset_index(drop=True),
                pd.Series(test_fwd[valid_ic]).reset_index(drop=True),
            )
            logger.info(f"  OOF Rank IC (test-only): {ic_val:.4f}")
        else:
            ic_val = 0.0

        # 儲存 discount 情境的淨報酬作為 daily_returns（供圖表使用）
        disc_cost = cost_models.get("discount", {})
        disc_rt = _round_trip_cost(disc_cost) if disc_cost else 0
        disc_daily_cost = disc_rt * avg_turnover / max(horizon, 1)
        net_returns_disc = raw_returns - disc_daily_cost

        all_results[engine] = {
            "cost_scenarios": engine_results,
            "rank_ic": round(ic_val, 4),
            "daily_returns": net_returns_disc,  # pd.Series with date index for charts
            "raw_daily_returns": raw_returns.tolist(),
            "n_trading_days": len(raw_returns),
            "avg_daily_stocks": round(daily_agg["n_stocks"].mean(), 1),
            "avg_turnover": round(avg_turnover, 4),
        }

    return all_results


# ============================================================
# 基準策略
# ============================================================

@timer
def compute_benchmark(
    df: pd.DataFrame,
    folds: list,
    config: dict,
) -> dict:
    """
    計算 buy-and-hold 等權基準（大盤代理）。
    """
    date_col = "trade_date"
    close_col = "closing_price"
    ticker_col = "company_id"

    all_test_dates = set()
    for fold in folds:
        test_data = df.iloc[fold.test_idx]
        all_test_dates.update(test_data[date_col].unique())

    test_df = df[df[date_col].isin(all_test_dates)].copy()
    test_df = test_df.sort_values([ticker_col, date_col])

    daily_ret = test_df.groupby(ticker_col)[close_col].pct_change()
    market_daily = daily_ret.groupby(test_df[date_col]).mean().sort_index().dropna()

    metrics = compute_strategy_metrics(market_daily)
    logger.info(
        f"  Benchmark (equal-weight market): "
        f"Return={metrics['annualized_return']:+.2%} | "
        f"Sharpe={metrics['sharpe_ratio']:.2f} | "
        f"MDD={metrics['max_drawdown']:.2%}"
    )

    return {
        "metrics": metrics,
        "daily_returns": market_daily,  # pd.Series with date index for charts
        "daily_returns_list": market_daily.tolist(),
        "n_trading_days": len(market_daily),
    }
