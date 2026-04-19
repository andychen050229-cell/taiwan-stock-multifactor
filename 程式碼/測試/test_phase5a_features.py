"""
Phase 5A 特徵擴充 smoke test
===========================
驗證四類新特徵（chip_, mg_, ind_, event_phase5a）在 toy data 上能正確運作。

執行：
    pytest 程式碼/測試/test_phase5a_features.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# 確保 src 可被 import
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.features.engineer_phase5a import (  # noqa: E402
    build_chip_features,
    build_margin_features,
    build_industry_features,
    build_event_features_phase5a,
)


# ============================================================
# Fixtures
# ============================================================

def make_prices(n_days: int = 30, stocks: list[str] = None) -> pd.DataFrame:
    stocks = stocks or ["2330", "2454", "1101"]
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    rows = []
    rng = np.random.default_rng(42)
    for sid in stocks:
        base = 100 + rng.uniform(-10, 10)
        for d in dates:
            base *= 1 + rng.normal(0, 0.01)
            rows.append(
                {
                    "company_id": sid,
                    "trade_date": d,
                    "closing_price": base,
                }
            )
    return pd.DataFrame(rows)


def make_inst(prices: pd.DataFrame) -> pd.DataFrame:
    """fake institutional data matching prices"""
    rng = np.random.default_rng(7)
    df = prices[["company_id", "trade_date"]].copy()
    df["foreign_net"] = rng.normal(0, 500, len(df)).astype(int)
    df["trust_net"] = rng.normal(0, 100, len(df)).astype(int)
    df["dealer_net"] = rng.normal(0, 50, len(df)).astype(int)
    df["all_inst_net"] = df["foreign_net"] + df["trust_net"] + df["dealer_net"]
    return df


def make_margin(prices: pd.DataFrame) -> pd.DataFrame:
    """fake margin trading data"""
    rng = np.random.default_rng(11)
    df = prices[["company_id", "trade_date"]].copy()
    df["margin_balance"] = (rng.uniform(1000, 5000, len(df))).astype(int)
    df["margin_change"] = rng.normal(0, 200, len(df)).astype(int)
    df["short_balance"] = (rng.uniform(100, 500, len(df))).astype(int)
    df["short_change"] = rng.normal(0, 30, len(df)).astype(int)
    df["margin_short_ratio"] = df["margin_balance"] / df["short_balance"].replace(0, 1)
    df["margin_use_rate"] = rng.uniform(0.1, 0.8, len(df))
    return df


def make_industry(stocks: list[str] = None) -> pd.DataFrame:
    stocks = stocks or ["2330", "2454", "1101"]
    mapping = {"2330": "半導體", "2454": "半導體", "1101": "水泥"}
    names = {"2330": "台積電", "2454": "聯發科", "1101": "台泥"}
    return pd.DataFrame(
        [
            {
                "company_id": s,
                "stock_name": names[s],
                "industry_category": mapping[s],
                "industry_code": 1 if mapping[s] == "半導體" else 2,
                "listing_type": "twse",
                "info_date": pd.Timestamp("2020-01-01"),
            }
            for s in stocks
        ]
    )


def make_text(industry: pd.DataFrame, n: int = 200) -> pd.DataFrame:
    """fake text with embedded stock names"""
    rng = np.random.default_rng(29)
    names = industry["stock_name"].tolist()
    dates = pd.date_range("2023-12-01", "2024-02-15", freq="D")
    rows = []
    for _ in range(n):
        nm = rng.choice(names)
        sent_word = rng.choice(["大漲", "利多", "看好", "大跌", "利空", "衰退"])
        title = f"{nm} 近期 {sent_word}，投資人關注"
        content = f"{title} 根據記者報導，{nm} 今日表現 {sent_word}..."
        rows.append(
            {
                "post_time": rng.choice(dates),
                "title": title,
                "content": content,
                "p_type": rng.choice(["news", "forum", "bbs"]),
                "content_type": rng.choice(["main", "reply"]),
            }
        )
    return pd.DataFrame(rows)


# ============================================================
# Tests
# ============================================================

class TestChipFeatures:
    def test_basic(self):
        prices = make_prices()
        inst = make_inst(prices)
        out = build_chip_features(prices, inst, {})

        for col in [
            "chip_foreign_net_1d", "chip_foreign_net_5d", "chip_foreign_net_20d",
            "chip_trust_net_5d", "chip_dealer_net_5d",
            "chip_all_inst_net_5d", "chip_all_inst_net_20d",
            "chip_foreign_trend_20d", "chip_consensus_5d",
        ]:
            assert col in out.columns, f"missing {col}"

        # chip_foreign_net_1d should be shifted (T-1 value)
        # For each stock, first row should be NaN
        for sid in out["company_id"].unique():
            sub = out[out["company_id"] == sid].sort_values("trade_date")
            assert pd.isna(sub["chip_foreign_net_1d"].iloc[0]), (
                f"{sid}: shift(1) should make first row NaN"
            )

    def test_empty_inst(self):
        prices = make_prices()
        out = build_chip_features(prices, pd.DataFrame(), {})
        # 應該優雅地返回 prices 原樣
        assert "chip_foreign_net_1d" not in out.columns
        assert len(out) == len(prices)

    def test_consensus_values(self):
        prices = make_prices(n_days=60)
        inst = make_inst(prices)
        out = build_chip_features(prices, inst, {})
        # 一致性只能是 {-1, 0, 1}
        valid = out["chip_consensus_5d"].dropna().unique()
        for v in valid:
            assert v in [-1, 0, 1]


class TestMarginFeatures:
    def test_basic(self):
        prices = make_prices()
        mg = make_margin(prices)
        out = build_margin_features(prices, mg, {})

        for col in [
            "mg_margin_balance_1d",
            "mg_margin_balance_chg_5d",
            "mg_short_balance_chg_5d",
            "mg_margin_short_ratio_1d",
            "mg_margin_use_rate_1d",
            "mg_retail_sentiment_5d",
        ]:
            assert col in out.columns, f"missing {col}"

    def test_empty_mg(self):
        prices = make_prices()
        out = build_margin_features(prices, pd.DataFrame(), {})
        assert not any(c.startswith("mg_") for c in out.columns)


class TestIndustryFeatures:
    def test_basic(self):
        prices = make_prices(n_days=60)
        industry = make_industry()
        out = build_industry_features(prices, industry, {})

        for col in [
            "ind_return_rel_20d",
            "ind_momentum_rank_20d",
            "ind_volatility_rel_60d",
            "ind_member_count",
        ]:
            assert col in out.columns, f"missing {col}"

        # 同產業兩檔的 pct-rank：n=2 時 ranks 為 0.5 與 1.0，sum = 1.5
        sub = out.dropna(subset=["ind_momentum_rank_20d"])
        sc_grp = sub[sub["company_id"].isin(["2330", "2454"])].groupby("trade_date")["ind_momentum_rank_20d"]
        sums = sc_grp.sum()
        assert ((sums > 1.4) & (sums < 1.6)).all(), f"expected ~1.5 for 2-stock industry, got {sums.describe()}"

        # 每個時點 rank 應該在 [0, 1] 範圍內
        rank_vals = out["ind_momentum_rank_20d"].dropna()
        assert (rank_vals >= 0).all() and (rank_vals <= 1).all()

        # 不同產業的 ind_member_count 應該不同
        mc = out.groupby("company_id")["ind_member_count"].first()
        assert mc["2330"] == 2  # 半導體 2 檔
        assert mc["1101"] == 1  # 水泥 1 檔


class TestEventFeaturesPhase5A:
    def test_basic(self):
        prices = make_prices(n_days=40)
        industry = make_industry()
        text = make_text(industry, n=500)
        out = build_event_features_phase5a(prices, text, industry, {})

        expected = [
            "event_mention_cnt_1d",
            "event_mention_cnt_5d",
            "event_mention_cnt_20d",
            "event_mention_surge",
            "event_sent_score_5d",
            "event_news_ratio_5d",
            "event_post_main_ratio_5d",
        ]
        for c in expected:
            assert c in out.columns, f"missing {c}"

        # 提及量應該是非負
        for c in ["event_mention_cnt_1d", "event_mention_cnt_5d", "event_mention_cnt_20d"]:
            vals = out[c].dropna()
            assert (vals >= 0).all(), f"{c} contains negatives"

    def test_per_stock_different(self):
        """各股票的 mention 應該不同（不像舊版全部一樣）"""
        prices = make_prices(n_days=40)
        industry = make_industry()
        text = make_text(industry, n=1000)
        out = build_event_features_phase5a(prices, text, industry, {})

        # 至少在某個 trade_date 上，2330 和 1101 的 mention_cnt_5d 應該不同
        piv = out.pivot_table(
            index="trade_date",
            columns="company_id",
            values="event_mention_cnt_5d",
            aggfunc="first",
        )
        # 找出兩檔值不完全一樣的日子
        if "2330" in piv.columns and "1101" in piv.columns:
            diff = (piv["2330"] - piv["1101"]).abs().fillna(0)
            assert (diff > 0).sum() > 0, "phase5a should have per-stock variation"

    def test_empty_text(self):
        prices = make_prices()
        industry = make_industry()
        out = build_event_features_phase5a(prices, pd.DataFrame(), industry, {})
        assert not any(
            c.startswith("event_mention") or c.startswith("event_sent")
            for c in out.columns
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
