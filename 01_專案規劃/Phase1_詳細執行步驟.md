# Phase 1 後續工作細項 — 優先執行清單

**本文件用途**: 在 IMPLEMENTATION_ROADMAP.md 的基礎上，提供 Phase 1 各工作項的具體實裝指引
**更新日期**: 2026-04-04
**優先級**: 按執行順序排列，標示 BLOCKING（關鍵路徑）和 OPTIONAL

---

## § 1 決策項（Week 0）— 立即決定

### 1.1 OHLCV 資料來源選擇
**優先級**: BLOCKING | **影響**: 4-6 週特徵工程

**決策事項**:
```
Q: 股票 OHLCV (Open/High/Low/Close/Volume) 資料應從何取得？

A. Yahoo Finance API (yfinance)
   ✓ 優: 免費、覆蓋廣、穩定
   ✗ 劣: 除權息調整可能有延遲、歷史資料有刪改風險

B. TradingView
   ✓ 優: 資料品質高、歷史悠久
   ✗ 劣: API 需付費；可能有反爬蟲

C. 台灣交易所 OPENDATA
   ✓ 優: 官方、可信、免費
   ✗ 劣: API 可能有速率限制；需清理格式

D. 現有本地庫存
   ✓ 優: 最快、避免外部依賴
   ✗ 劣: 需驗證資料品質

E. 不使用（用 closing_price 推導替代）
   ✓ 優: 無額外工作、降低維護成本
   ✗ 劣: 損失 MACD、momentum breakout 等 OHLC 特有指標

建議**:
  - 若工期緊張 → 選 E（可用 close 推導 volatility, MA slope）
  - 若資源充足且注重精度 → 選 A（Yahoo Finance）或 C（交易所）
  - 若已有本地資料 → 選 D（先驗證品質）
```

**決定後的 Action**:
- 若選 A/B/C: 進行 2.1 OHLCV 載入器實裝
- 若選 E: 跳過 2.1，進入 2.2 財報處理（更快啟動）

---

## § 2 Phase 1 工作流程（週序）

### Week 1-2: 財報處理（2.2）— BLOCKING

**文件位置**: `src/data/income_stmt_processor.py`（新建）

#### 2.2.1 累積值 → 單季推導

**輸入**:
- `income_stmt.parquet` 中的欄位:
  - `stock_id`, `quarter` (或 `period`), `revenue`, `gross_profit`, `operating_income`, `net_income` 等

**問題分析**:
```python
# 現狀: 累積值
2024-Q1: revenue = 100
2024-Q2: revenue = 200  # 累積到 Q2
2024-Q3: revenue = 350  # 累積到 Q3

# 目標: 單季值
2024-Q1: revenue_quarter = 100
2024-Q2: revenue_quarter = 100 (200-100)
2024-Q3: revenue_quarter = 150 (350-200)
```

**實裝步驟**:
1. 偵測 `quarter` 欄位並標準化為 `Q1/Q2/Q3/Q4` 格式
2. 按 (stock_id, year) 分組，按 quarter 排序
3. 檢測是否為累積值（通常是）:
   - 預期: Q1 < Q2 < Q3 < Q4（或接近）
   - 若不符 → 可能已是單季，skip 此步驟
4. 計算單季:
   ```python
   def cumulative_to_quarterly(group):
       """group: 單支股票單年度的 12 季資料"""
       quarterly = group.copy()
       for i in range(1, len(group)):
           quarterly.iloc[i, value_cols] = group.iloc[i, value_cols] - group.iloc[i-1, value_cols]
       return quarterly
   ```
5. 驗證邏輯:
   - sum(quarterly) == annual value
   - 各季度 >= 0（負數可能代表特殊調整）
   - 無異常尖峰（通常 Q4 最大）

**輸出**:
- 新欄位: `revenue_quarter`, `operating_income_quarter`, `net_income_quarter`, ...
- 記錄轉換日誌

**複雜度**: M | **工期**: 4-5 天

---

#### 2.2.2 PIT（Point-in-Time）日期推估

**背景**:
```
台灣上市公司財報申報期限（IFRS 非金融業）:
  Q1 (1-3月): 5月15日前 → 市場最早可用日期 ≈ 5/15
  Q2 (4-6月): 8月14日前 → 市場最早可用日期 ≈ 8/14
  Q3 (7-9月): 11月14日前 → 市場最早可用日期 ≈ 11/14
  Q4 (10-12月): 隔年3月31日 → 市場最早可用日期 ≈ next_year/3/31

問題: 若某支股票財報資料只標記 "Q1 2024"，無法對應真實市場可用日期
→ 造成前瞻偏差：用 1/31 的股價去預測基於 5/15 才揭露的財報

解決: 計算 pit_date（Point-In-Time Date）
→ 用股價資料時，只能用 pit_date 前的股價
```

**實裝步驟**:
1. 定義申報期限字典:
   ```python
   FILING_DEADLINES = {
       "Q1": (5, 15),   # 月, 日
       "Q2": (8, 14),
       "Q3": (11, 14),
       "Q4": (3, 31),   # 跨年，隔年
   }
   ```
2. 按 (stock_id, year, quarter) 推估 pit_date:
   ```python
   def estimate_pit_date(row):
       year = row['year']
       quarter = row['quarter']
       month, day = FILING_DEADLINES[quarter]

       if quarter == "Q4":
           pit_year = year + 1
       else:
           pit_year = year

       return pd.Timestamp(pit_year, month, day)
   ```
3. 檢查是否有 `announced_date` 欄位 → 若有，用 `min(pit_date, announced_date)` 作為實際可用日期
4. 檢查特殊情況（金融業等，期限不同）

**輸出**:
- 新欄位: `pit_date` (datetime)
- 新欄位: `filing_deadline` (字串，如 "5/15")

**複雜度**: S | **工期**: 2-3 天

---

#### 2.2.3 驗證與品質檢查

**檢查清單**:
```
[ ] 單季轉換: sum(quarterly) ≈ annual (誤差 < 0.5%)
[ ] PIT 日期: 都在合理範圍（5/15, 8/14, 11/14, next_year/3/31 附近）
[ ] 金額邏輯: 無負的營收、毛利、營利（允許淨損）
[ ] 時間順序: pit_date >= quarter_end_date
[ ] 缺值: 記錄哪些股票/期間的財報資料缺失
```

**輸出**: Phase 1 報告中新增 `income_stmt_processing` 章節

**總工期**: Week 1-2 共 5-7 天

---

### Week 2-3: 資料型別統一（2.3）+ 基礎標籤生成（2.4）

#### 2.3 dtype 轉換

**文件位置**: `src/data/dtype_converter.py`（新建）

**實裝策略**:

1. **日期欄位** → `datetime64[ns]`
   - 候選: date, 日期, announcement_date, pit_date, quarter_end_date, filing_date
   - 做法: `pd.to_datetime(col, errors='coerce')`

2. **數值（價格、金額）** → `float32`
   - 候選: closing_price, revenue, operating_income, net_income, high, low, open
   - 特殊: 若金額單位為 thousands，檢查是否需要乘以倍數

3. **數量（股數、成交量）** → `int32/int64`
   - 候選: volume, shares_outstanding, outstanding_shares

4. **比率** → `float32`
   - 候選: margin, roe, roa, beta（通常已是小數或百分比）

5. **分類** → `category`（如果基數 < 1000）
   - 候選: content_type, industry, stock_id（if < 1000 unique values）
   - 好處: 節省記憶體 30-50%

6. **布林** → `bool`
   - 候選: _is_limit_up, _is_limit_down, _limit_type

7. **文字** → `string` 或保留 `object`
   - 候選: company_name, news_content, announcement_title
   - 考量: 記憶體 vs. 操作速度

**實裝**:
```python
def get_dtype_schema(df, config):
    """
    自動推斷每欄應有的 dtype，並返回轉換字典
    """
    dtype_map = {}

    for col in df.columns:
        if col in DATE_KEYWORDS:
            dtype_map[col] = 'datetime64[ns]'
        elif col in PRICE_KEYWORDS:
            dtype_map[col] = 'float32'
        elif col in VOLUME_KEYWORDS:
            dtype_map[col] = 'int32'
        elif df[col].nunique() < 1000 and df[col].dtype == 'object':
            dtype_map[col] = 'category'
        else:
            dtype_map[col] = df[col].dtype

    return dtype_map

# 套用
for table_name, df in data.items():
    dtype_map = get_dtype_schema(df, config)
    for col, dtype in dtype_map.items():
        try:
            df[col] = df[col].astype(dtype)
        except Exception as e:
            logger.warning(f"{table_name}.{col}: {e}")
```

**驗證**:
```python
# 在 Phase 1 報告中輸出:
dtype_before = ...  # 原始 dtype
dtype_after = ...   # 轉換後 dtype
memory_saved = ...  # 記憶體節省百分比
```

**複雜度**: S | **工期**: 2-3 天

---

#### 2.4 標籤生成（Label Generation）

**文件位置**: `src/features/label_generator.py`（新建）

**核心邏輯**:

```python
class LabelGenerator:
    """
    為各 horizon 生成分類標籤
    """

    def __init__(self, config):
        self.horizons = [1, 5, 20]  # D+1, D+5, D+20
        self.binary_threshold = 0.0  # 0% 以上視為上漲
        self.ternary_thresholds = {
            1: (-0.01, 0.01),   # [-1%, +1%]
            5: (-0.02, 0.02),   # [-2%, +2%]
            20: (-0.03, 0.03),  # [-3%, +3%]
        }

    def generate_returns(self, prices_df):
        """計算 D+1, D+5, D+20 報酬"""
        prices_df = prices_df.sort_values(['stock_id', 'date'])

        for h in self.horizons:
            # 向前 shift: prices[D] / prices[D-h] - 1
            prices_df[f'ret_d{h}'] = (
                prices_df.groupby('stock_id')['closing_price']
                .shift(-h) / prices_df['closing_price'] - 1
            )

        return prices_df

    def create_labels(self, prices_df):
        """Binary + Ternary labels"""

        # 標記需排除的日期（漲跌停、停牌）
        exclude_mask = (
            prices_df['_is_limit_up'] |
            prices_df['_is_limit_down'] |
            (prices_df['volume'] == 0)
        )

        for h in self.horizons:
            ret_col = f'ret_d{h}'

            # Binary: 0/1
            prices_df[f'label_up_d{h}'] = (
                prices_df[ret_col] > 0
            ).astype(int)

            # Ternary: -1/0/+1 (DOWN/FLAT/UP)
            lower, upper = self.ternary_thresholds[h]
            prices_df[f'label_trend_d{h}'] = 0  # FLAT default
            prices_df.loc[prices_df[ret_col] < lower, f'label_trend_d{h}'] = -1  # DOWN
            prices_df.loc[prices_df[ret_col] > upper, f'label_trend_d{h}'] = 1   # UP

            # 標記排除列
            prices_df.loc[exclude_mask, f'label_up_d{h}'] = np.nan
            prices_df.loc[exclude_mask, f'label_trend_d{h}'] = np.nan

        return prices_df

    def validate_labels(self, prices_df):
        """檢查標籤平衡度"""
        report = {}

        for h in [1, 5, 20]:
            binary_col = f'label_up_d{h}'
            ternary_col = f'label_trend_d{h}'

            # 移除 NaN
            valid_binary = prices_df[binary_col].dropna()
            valid_ternary = prices_df[ternary_col].dropna()

            report[f'D+{h}_binary'] = {
                'total': len(valid_binary),
                'up_pct': valid_binary.mean(),
                'down_pct': 1 - valid_binary.mean(),
                'balanced': 0.3 < valid_binary.mean() < 0.7,
            }

            report[f'D+{h}_ternary'] = {
                'total': len(valid_ternary),
                'down': (valid_ternary == -1).sum(),
                'flat': (valid_ternary == 0).sum(),
                'up': (valid_ternary == 1).sum(),
                'max_class_pct': max(
                    (valid_ternary == -1).mean(),
                    (valid_ternary == 0).mean(),
                    (valid_ternary == 1).mean(),
                ),
            }

        return report
```

**檢查項**:
```
標籤平衡度警告:
  ✗ 任何 horizon 的正類比例 < 10% 或 > 90% → WARNING
  ✗ Ternary label 某類佔 > 80% → WARNING
  ✗ 缺值（NaN）> 30% → ERROR
```

**複雜度**: M | **工期**: 4-5 天

**總計 Week 2-3**: 8-10 天

---

### Week 4-9: 特徵工程五支柱（2.5）— CRITICAL PATH

#### 2.5.1 趨勢與價格（pillar_01_trend.py）

**需求**:
- 輸入: stock_prices (含 closing_price，若可用則含 OHLCV)
- 輸出: 欄位前綴 `trend_*`，包括:
  - trend_ma5, trend_ma10, trend_ma20 (moving average)
  - trend_ma_slope (MA 變化率)
  - trend_rsi (14-period RSI)
  - trend_volatility (日報酬標準差)
  - trend_momentum (price[t] - price[t-k])
  - trend_price_to_ma (price / MA 比值，衡量偏離度)

**計算邏輯** (pseudocode):
```python
def compute_trend_features(prices_df):
    """
    為每支股票、每個交易日計算趨勢特徵
    """
    result = prices_df.copy()

    # 1. 移動平均
    for window in [5, 10, 20]:
        result[f'trend_ma{window}'] = (
            result.groupby('stock_id')['closing_price']
            .rolling(window).mean()
            .reset_index(drop=True)
        )

        # MA 變化率: (MA[t] - MA[t-1]) / MA[t-1]
        result[f'trend_ma{window}_slope'] = (
            result.groupby('stock_id')[f'trend_ma{window}']
            .pct_change()
        )

    # 2. RSI (14-period)
    result['trend_rsi'] = calculate_rsi(
        result.groupby('stock_id')['closing_price'],
        period=14
    )

    # 3. Volatility (20-day rolling std of returns)
    returns = result.groupby('stock_id')['closing_price'].pct_change()
    result['trend_volatility'] = (
        returns.groupby(result['stock_id'])
        .rolling(20).std()
        .reset_index(drop=True)
    )

    # 4. Momentum (price[t] - price[t-k])
    for lag in [5, 10, 20]:
        result[f'trend_momentum_{lag}d'] = (
            result.groupby('stock_id')['closing_price']
            .diff(lag)
        )

    # 5. Price to MA ratio
    result['trend_price_to_ma20'] = (
        result['closing_price'] / result['trend_ma20']
    )

    return result
```

**標準化**:
- 跨越日期做 percentile rank 或 z-score normalize（同業內）
- 缺值: NaN → forward fill → 0

**複雜度**: M | **工期**: 5-7 天

---

#### 2.5.2 基本面品質（pillar_02_fundamental.py）

**需求**:
- 輸入: income_stmt (已推導單季 + PIT)，stock_prices
- 輸出: 欄位前綴 `fund_*`

**主要特徵**:
```
fund_revenue_growth: YoY revenue change
fund_gross_margin: gross_profit / revenue
fund_operating_margin: operating_income / revenue
fund_net_margin: net_income / revenue
fund_roe: net_income / shareholder_equity
fund_operating_cf_ratio: operating_cf / net_income (獲利品質)
fund_debt_to_equity: total_debt / equity
fund_margin_trend: current_margin - margin_4q_ago
```

**PIT 對齊邏輯** (核心):
```python
def align_income_to_prices(income_df, prices_df):
    """
    核心: 對任何交易日，只能用該日期前最新可用的財報資料
    """

    # prices: (stock_id, trade_date)
    # income: (stock_id, pit_date, revenue, ...)

    # 左連接: 對每個 (stock_id, trade_date)，
    # 找到 pit_date <= trade_date 的最新一筆財報

    merged = pd.merge_asof(
        prices_df.sort_values(['stock_id', 'trade_date']),
        income_df.sort_values(['stock_id', 'pit_date']),
        on=['stock_id'],
        by='trade_date',  # 錯誤！應該用 backward search
        direction='backward'  # 往前找
    )
    # 正確做法: 逐個 stock_id，binary search

    result = []
    for sid in prices_df['stock_id'].unique():
        prices_sid = prices_df[prices_df['stock_id'] == sid].sort_values('trade_date')
        income_sid = income_df[income_df['stock_id'] == sid].sort_values('pit_date')

        merged_sid = pd.merge_asof(
            prices_sid,
            income_sid,
            left_on='trade_date',
            right_on='pit_date',
            direction='backward'  # 往前找最近的
        )
        result.append(merged_sid)

    return pd.concat(result, ignore_index=True)
```

**複雜度**: M | **工期**: 6-8 天

---

#### 2.5.3 估值（pillar_03_valuation.py）

**需求**:
- 輸入: income_stmt (含 EPS), stock_prices, companies (行業分類)
- 輸出: 欄位前綴 `val_*`

**主要特徵**:
```
val_pe_ratio: closing_price / EPS
val_pe_vs_market: stock_pe / market_avg_pe (同日行業平均)
val_pb_ratio: closing_price / (equity / shares)
val_price_to_sales: market_cap / revenue

行業分位數:
val_pe_percentile: 該股票 PE 在同行業中的百分位
val_pb_percentile: 該股票 PB 在同行業中的百分位
```

**計算** (EPS 推算):
```python
def compute_eps(income_stmt):
    """
    若無 EPS 欄位，則推算:
    EPS = net_income / outstanding_shares
    """
    income_stmt['eps'] = (
        income_stmt['net_income'] / income_stmt['outstanding_shares']
    )
    return income_stmt
```

**行業相對化**:
```python
def normalize_by_industry(merged_df):
    """
    計算行業內的百分位
    """
    for metric in ['pe_ratio', 'pb_ratio']:
        merged_df[f'{metric}_percentile'] = (
            merged_df.groupby(['trade_date', 'industry'])[metric]
            .rank(pct=True)
        )
    return merged_df
```

**複雜度**: M | **工期**: 5-7 天

---

#### 2.5.4 事件與敘事（pillar_04_event.py）— 最複雜

**需求**:
- 輸入: stock_text (已清洗：content_type, title, content)
- 輸出: 欄位前綴 `event_*`

**主要特徵** (優先級排序):

**P0 (簡單)**:
```
event_news_volume: rolling count of articles (5/20 days)
event_announcement_flag: 當日是否有公告 (binary)
event_news_surge: current_volume / avg_volume (異常活動指示)
```

**P1 (中等)**:
```
event_news_sentiment: 簡單規則或預訓練模型
  - 計數正面詞（上漲、強、漲停、利好）
  - 計數負面詞（下跌、弱、跌停、利空）
  - sentiment_score = (positive_count - negative_count) / total_words

event_keyword_presence: 關鍵詞出現 (one-hot)
  - 配息公告
  - 股票分割
  - 增資減資
  - 重大收購
  - 虧損預警
```

**實裝** (Simplified):
```python
def compute_event_features(stock_text, prices):
    """
    stock_text: (stock_id, date, content, content_type, ...)
    prices: (stock_id, date)
    """
    result = prices.copy()

    # 1. News volume
    news_counts = stock_text.groupby(['stock_id', 'date']).size()
    result = result.merge(
        news_counts.rolling(5).sum().rename('event_news_volume_5d'),
        on=['stock_id', 'date'],
        how='left'
    )
    result['event_news_volume_5d'].fillna(0, inplace=True)

    # 2. Announcement flag
    announcements = stock_text[
        stock_text['content_type'] == 'announcement'
    ].groupby(['stock_id', 'date']).size() > 0
    result = result.merge(
        announcements.rename('event_has_announcement'),
        on=['stock_id', 'date'],
        how='left'
    )
    result['event_has_announcement'].fillna(False, inplace=True)

    # 3. 簡單情緒 (規則)
    positive_words = ['上漲', '利好', '強', '增長', '績優']
    negative_words = ['下跌', '利空', '弱', '虧損', '下滑']

    stock_text['sentiment_score'] = 0.0
    for word in positive_words:
        stock_text.loc[
            stock_text['content'].str.contains(word),
            'sentiment_score'
        ] += 1
    for word in negative_words:
        stock_text.loc[
            stock_text['content'].str.contains(word),
            'sentiment_score'
        ] -= 1

    # Aggregate by (stock_id, date)
    daily_sentiment = stock_text.groupby(['stock_id', 'date'])['sentiment_score'].mean()
    result = result.merge(
        daily_sentiment.rename('event_sentiment'),
        on=['stock_id', 'date'],
        how='left'
    )
    result['event_sentiment'].fillna(0, inplace=True)

    return result
```

**後期優化** (Phase 2+ 可做):
- BERT/RoBERTa 中文情緒分類
- TF-IDF 自動抽取高頻詞
- Topic modeling (LDA / NMF)

**複雜度**: L | **工期**: 8-10 天

---

#### 2.5.5 風險與機制（pillar_05_risk.py）

**需求**:
- 輸入: stock_prices (closing_price + 可選 volume), income_stmt (debt, equity)
- 輸出: 欄位前綴 `risk_*`

**主要特徵**:

```
risk_volatility_20d: 20 日報酬標準差
risk_volatility_regime: LOW / MED / HIGH (GMM 分群)
risk_max_drawdown_20d: max(cumulative_max - current) / cumulative_max
risk_downside_volatility: std(negative returns only)

風險分層:
risk_high_vol_flag: volatility > 75th percentile
risk_distress_flag: debt_to_equity > 100% (財務風險)
risk_illiquidity_flag: volume < 25th percentile (流動性風險)
```

**計算示例**:
```python
def compute_risk_features(prices_df, income_df):
    """主要風險特徵"""

    result = prices_df.copy()

    # 1. 波動率 (20 日滾動)
    returns = result.groupby('stock_id')['closing_price'].pct_change()
    result['risk_volatility_20d'] = (
        returns.groupby(result['stock_id'])
        .rolling(20).std()
        .reset_index(drop=True) * 100  # convert to %
    )

    # 2. Volatility regime (簡化: 低/中/高)
    vol_percentiles = result.groupby('stock_id')['risk_volatility_20d'].quantile([0.33, 0.67])

    def assign_vol_regime(row):
        vol = row['risk_volatility_20d']
        sid = row['stock_id']
        low_thresh = vol_percentiles.loc[sid, 0.33]
        high_thresh = vol_percentiles.loc[sid, 0.67]

        if vol <= low_thresh:
            return 'LOW'
        elif vol <= high_thresh:
            return 'MED'
        else:
            return 'HIGH'

    result['risk_volatility_regime'] = result.apply(assign_vol_regime, axis=1)

    # 3. Max drawdown (20 日)
    def compute_drawdown(prices):
        cummax = prices.expanding().max()
        drawdown = (prices - cummax) / cummax
        return drawdown.rolling(20).min()

    result['risk_max_drawdown_20d'] = (
        result.groupby('stock_id')['closing_price']
        .transform(compute_drawdown) * 100
    )

    # 4. 合併財務風險
    # debt_to_equity 接合 (via PIT)
    merged = align_income_to_prices(income_df, prices_df)  # reuse from pillar 2
    merged['risk_distress_flag'] = merged['debt_to_equity'] > 1.0

    return merged
```

**複雜度**: M | **工期**: 5-7 天

**總計 Week 4-9**: 5-6 週，共 30-40 天

---

### Week 10-11: 共線性去重（2.6）+ Feature Store（2.7）

#### 2.6 共線性去重 (feature_dedup.py + mi_filter.py)

**層 1: Correlation clustering**
```python
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist, squareform

def cluster_correlated_features(features_df, threshold=0.85):
    """
    用 agglomerative clustering 聚集高相關特徵
    """
    corr_matrix = features_df.corr().abs()
    linkage_matrix = linkage(
        squareform(1 - corr_matrix),  # 轉為距離
        method='average'
    )

    # 取 cluster 代表（每個 cluster 保留 1 個）
    clusters = fcluster(linkage_matrix, threshold, criterion='distance')

    selected_features = []
    for cluster_id in np.unique(clusters):
        cluster_features = [
            f for f, c in zip(features_df.columns, clusters)
            if c == cluster_id
        ]
        # 保留與目標最相關的那個
        correlations = [
            features_df[f].corr(target) for f in cluster_features
        ]
        best = cluster_features[np.argmax(correlations)]
        selected_features.append(best)

    return selected_features
```

**層 2: MI 初步篩選**
```python
from sklearn.feature_selection import mutual_info_classif

def mi_filter(X, y, threshold_percentile=25):
    """
    計算所有特徵與標籤的 MI，保留 > 25 百分位的
    """
    mi_scores = mutual_info_classif(X, y, random_state=42)
    threshold = np.percentile(mi_scores, threshold_percentile)

    selected_idx = np.where(mi_scores >= threshold)[0]
    selected_features = X.columns[selected_idx].tolist()

    return selected_features, mi_scores
```

**複雜度**: M | **工期**: 3-4 天

#### 2.7 Feature Store (feature_store.py)

```python
class FeatureStore:
    """
    統一的特徵讀寫層
    """

    def __init__(self, parquet_path):
        self.path = parquet_path
        self._cache = {}

    def save_features(self, df, version='v1'):
        """
        df: (stock_id, date, horizon, feature_name, value)
        """
        output_path = f"feature_store_{version}_{datetime.now().strftime('%Y%m%d')}.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved {len(df):,} feature rows to {output_path}")

    def load_features(self, stock_ids=None, dates=None, horizon=1):
        """
        讀取指定股票、日期、時間軸的特徵
        """
        if self.path in self._cache:
            df = self._cache[self.path]
        else:
            df = pd.read_parquet(self.path)
            self._cache[self.path] = df

        # 過濾
        if stock_ids is not None:
            df = df[df['stock_id'].isin(stock_ids)]
        if dates is not None:
            df = df[df['date'].isin(dates)]
        df = df[df['horizon'] == horizon]

        return df

    def get_feature_list(self, horizon=1):
        """列出該 horizon 的所有特徵"""
        pass
```

**複雜度**: S | **工期**: 2-3 天

**總計 Week 10-11**: 5-7 天

---

### Week 12: Phase 1 報告整合

#### 2.8 Phase 1 報告

**擴展現有 run_phase1.py**:

新增章節:
```python
report['results']['features'] = {
    'total_features': len(all_features),
    'per_pillar': {
        'trend': len(trend_features),
        'fundamental': len(fund_features),
        'valuation': len(val_features),
        'event': len(event_features),
        'risk': len(risk_features),
    },
    'after_dedup': {
        'retained': len(retained_features),
        'removed': removed_count,
    },
    'null_rates': {
        f: df[f].isnull().mean() for f in retained_features
    }
}

report['results']['labels'] = {
    'd1': {
        'total': len(labels_d1),
        'up_pct': labels_d1.mean(),
        'balanced': 0.3 < labels_d1.mean() < 0.7,
    },
    'd5': {...},
    'd20': {...},
}

report['quality_gates'] = {
    'ex_dividend_pass': True,
    'leakage_check1_pass': True,
    'label_balance_pass': True,  # NEW
    'feature_quality_pass': True,  # NEW
}
```

**視覺化**:
- Heatmap: 特徵間相關性
- Bar chart: 各支柱特徵數
- Pie chart: 標籤分佈

**複雜度**: S | **工期**: 2-3 天

---

## § 3 並行工作機會

如有額外資源（2+ 人團隊）:

```
Team A (Person 1):
  Week 1-3: 財報 (2.2) + dtype (2.3)
  Week 4-5: trend pillar (2.5.1) + risk pillar (2.5.5)

Team B (Person 2):
  Week 1-3: label generation (2.4)
  Week 4-7: fundamental (2.5.2) + valuation (2.5.3)

Team C (Person 3):
  Week 4-9: event pillar (2.5.4) — 最複雜，需專注
  Week 10-11: feature dedup (2.6) + feature store (2.7)

Team lead / QA:
  Week 12: 整合與報告 (2.8)
```

**依存關係須遵守**:
- Team A 的 2.2, 2.3 必須在 Team B 2.4 前完成
- 各團隊的 pillar 特徵可並行，但 2.6 (dedup) 需在所有 pillar 完成後

---

## § 4 里程碑與檢查點

| Week | Milestone | Gate | 進度 |
|------|-----------|------|------|
| 1 | 決定 OHLCV 來源 | 必須 | 0% |
| 2 | 財報單季推導完成 + 驗證 | PASS | 15% |
| 3 | 標籤生成完成 + 平衡度檢查 | PASS | 25% |
| 4 | 5 個特徵欄位各有 ≥ 1 個指標 | PASS | 35% |
| 5 | 所有 5 支柱 ≥ 5 個指標 | PASS | 55% |
| 9 | 特徵工程全部完成 (50-100 特徵) | PASS | 75% |
| 10 | 共線性去重 + Feature Store | PASS | 85% |
| 12 | Phase 1 報告生成 + 品質閘門 4/4 PASS | CRITICAL | 100% |

**若任何里程碑 FAIL**: 立即暫停，回溯修正

---

## § 5 測試與驗證

### 單元測試
```python
# test_label_generator.py
def test_label_binary():
    prices = pd.DataFrame({
        'stock_id': [1, 1, 1],
        'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'closing_price': [100, 105, 103]
    })
    lg = LabelGenerator()
    result = lg.create_labels(prices)
    assert result['label_up_d1'][1] == 1  # 105 > 100
    assert result['label_up_d1'][2] == 0  # 103 < 105

# test_feature_store.py
def test_feature_store_save_load():
    fs = FeatureStore('test.parquet')
    features = pd.DataFrame({
        'stock_id': [1, 1, 2],
        'date': ['2024-01-01', '2024-01-02', '2024-01-01'],
        'horizon': [1, 1, 1],
        'feature_name': ['trend_ma5', 'trend_ma5', 'trend_ma5'],
        'value': [100.5, 101.2, 95.3]
    })
    fs.save_features(features)
    loaded = fs.load_features(stock_ids=[1], dates=['2024-01-01'])
    assert len(loaded) == 1
    assert loaded['value'].iloc[0] == 100.5
```

### 整合測試
```python
# test_phase1_pipeline.py
def test_full_phase1():
    config = load_config()
    data = DataLoader(config).load_all()

    # 跑完整 pipeline
    data['stock_prices'] = handle_missing_prices(data['stock_prices'], config)
    data['income_stmt'] = process_income_stmt(data['income_stmt'])

    labels = LabelGenerator(config).create_labels(data['stock_prices'])
    features = build_all_features(data, labels)

    # 檢查
    assert len(features) > 0
    assert features.isnull().mean().max() < 0.3  # 缺值 < 30%
    assert len(features.columns) > 50  # 特徵數夠
```

---

## § 6 關鍵檔案列表與存檔位置

| 檔案 | 位置 | 優先級 | 預計完成週 |
|------|------|--------|----------|
| income_stmt_processor.py | src/data/ | P0 | Week 2 |
| dtype_converter.py | src/data/ | P1 | Week 3 |
| label_generator.py | src/features/ | P0 | Week 3 |
| pillar_01_trend.py | src/features/ | P0 | Week 5 |
| pillar_02_fundamental.py | src/features/ | P0 | Week 6 |
| pillar_03_valuation.py | src/features/ | P0 | Week 7 |
| pillar_04_event.py | src/features/ | P0 | Week 9 |
| pillar_05_risk.py | src/features/ | P0 | Week 8 |
| feature_dedup.py | src/features/ | P1 | Week 10 |
| mi_filter.py | src/features/ | P1 | Week 10 |
| feature_store.py | src/features/ | P1 | Week 11 |
| run_phase1_final.py | 專案根目錄 | P0 | Week 12 |
| PHASE1_REPORT.json | outputs/reports/ | P0 | Week 12 |

---

## § 7 手冊與參考資料

**需要查閱的資源**:
1. 台灣上市公司財報申報期限: 5/15, 8/14, 11/14, next_year/3/31
2. IFRS 與 GAAP 差異（若資料混合）
3. pandas rolling operations 文件
4. scikit-learn feature_selection 文件
5. 設計文件: `股市趨勢預測導向決策輔助系統_完整設計總綱.md`

**建議的快速參考**:
```bash
# 查看現有 configs
cat src/config/base.yaml

# 檢查 Parquet 結構
python -c "import pandas as pd; df = pd.read_parquet('xxx.parquet'); print(df.info())"

# 快速特性檢查
python -c "from src.data.loader import quick_profile; ..."
```

---

**文檔版本**: v1.0 | **最後更新**: 2026-04-04
**下一步**: 確認 OHLCV 來源決策，啟動 Week 1 工作

