# Phase 5：NLP 文本分析與情緒因子工程 — 架構設計

> **版本**：v1.0  
> **建立日期**：2026-04-08  
> **前置依賴**：Phase 4 完成（59 因子 Feature Store）  
> **預估工期**：2–3 週（含模型微調）

---

## 一、現狀分析與目標

### 1.1 目前文本處理現狀

Phase 1 中的 `text_processor.py` 僅完成基礎清洗：

| 已完成 | 未完成 |
|--------|--------|
| 內容分類（新聞/社群/公告/研報）— 關鍵字規則 | 情緒分析（Sentiment Analysis） |
| MinHash 近似去重 | 主題建模（BERTopic / LDA） |
| HTML / URL 清除 | 關鍵詞萃取（TF-IDF / TextRank） |
| 長度與語言篩選 | 命名實體辨識（NER） |
| `event_news_count_1d/5d`、`event_title_length_avg` | 文字雲視覺化 |

**現有事件因子僅 3 個**，且全為「量」的統計（新聞數量、標題長度），缺乏「質」的分析（情緒正負、主題關聯、語義相似度）。

### 1.2 Phase 5 目標

將 112 萬筆新聞/社群文本轉化為 **12–18 個 NLP 因子**，並整合至 Feature Store：

1. **日度個股情緒分數**（核心因子）
2. **市場整體情緒指標**（系統性風險補充）
3. **主題分布向量**（產業輪動訊號）
4. **關鍵詞異常偵測**（事件驅動因子）
5. **Dashboard 文字雲與情緒儀表板**（視覺化展示）

---

## 二、文本資料概況

```
stock_text_lite.parquet
├── 筆數：1,125,134
├── 欄位：no, id, p_type, s_name, s_area_name, post_time, title, author
├── 內容類型：新聞/PTT/公告/研報（content_type 51.7% NaN — 需重新分類）
├── 文本欄位：title（平均 22 字元）
└── 注意：僅有標題，無全文內容（影響深度 NLP 效果）
```

**資料限制**：本專案的文本僅有 `title`（標題），無 `content`（全文）。這意味著：
- 情緒分析需針對短文本（≤50 字）優化
- BERTopic 的主題辨識精度會受限
- TF-IDF 特徵空間較稀疏

因此架構設計中會針對「標題級」文本做特別處理。

---

## 三、技術選型

### 3.1 分詞器

| 工具 | 優點 | 缺點 | 結論 |
|------|------|------|------|
| **CKIP Transformers** | 繁體中文 SOTA、細粒度 POS、支援 NER | 速度較慢（GPU 建議） | ✅ **主選** |
| Jieba | 快速、易安裝 | 繁體表現差、金融詞彙覆蓋不足 | 備選（快速原型用） |

**安裝**：`pip install ckip-transformers`  
**模型**：`ckiplab/bert-base-chinese-ws`（斷詞）、`ckiplab/bert-base-chinese-pos`（POS）、`ckiplab/bert-base-chinese-ner`（NER）

### 3.2 情緒分析方案

採用**三層遞進架構**，由快到慢、由簡到精：

#### Layer 1：字典法（ANTUSD）— 快速基線
- **ANTUSD**（Academia Sinica Sentiment Dictionary）：26,021 個繁體中文情緒詞
- 每個詞有 CopeOpi 數值分數（正/中/負）
- 來源：中研院 NLP 實驗室（http://academiasinicanlplab.github.io/）
- **優點**：無需 GPU、速度極快、可解釋性高
- **缺點**：金融領域覆蓋率有限、無法處理反諷/否定

```python
# 概念範例
def dict_sentiment(text: str, lexicon: dict) -> float:
    tokens = ckip_tokenize(text)
    scores = [lexicon.get(t, 0.0) for t in tokens]
    return np.mean(scores) if scores else 0.0
```

#### Layer 2：FinBERT 微調 — 核心模型
- **基底模型**：`bert-base-chinese`（Google，~110M 參數）
- **微調策略**：在台灣金融新聞標題上做 3-class 分類（正面/中性/負面）
- **訓練資料**：Layer 1 字典法自動標記 + 人工抽驗校正（semi-supervised）
- **替代方案**：若算力不足，可用 `ckiplab/albert-base-chinese` 替代（體積更小）

**參考文獻**：
- Wang et al. (2025) — BERT + LightGBM 選股，SAGE Journals
- MDPI (2023) — 中文金融新聞分析框架，在 PTT 台股論壇達 90.62% 準確度

#### Layer 3：LLM 增強（選配）
- 使用 Claude API / GPT-4o 對少量高價值新聞做精細分析
- 事件分類：營收公告、法說會、併購、監管處分、產業趨勢
- **成本考量**：僅對研報類和重大新聞使用（約佔 5-10%）

### 3.3 主題建模

| 方案 | 工具 | Embedding | 適用性 |
|------|------|-----------|--------|
| **BERTopic** | `pip install bertopic` | `paraphrase-multilingual-MiniLM-L12-v2` | ✅ 主選（中文原生支援、無需額外預處理） |
| LDA | gensim | Bag-of-Words | 備選（輕量但品質較低） |

BERTopic 在中文金融債券新聞中成功識別 78 個主題，可聚合為 18 個可解釋主題（Li et al. 2024, ScienceDirect）。

### 3.4 關鍵詞萃取

- **TF-IDF**：sklearn 實現，提取每日/每週 top-K 關鍵詞
- **TextRank**：基於圖論的無監督萃取
- **Keyword Surprise**：當日 TF-IDF 與 30 日均值的 KL 散度，偵測異常話題

---

## 四、管線架構設計

### 4.1 整體流程

```
stock_text_lite.parquet (112 萬筆標題)
        │
        ▼
┌─────────────────────────┐
│  Stage 1: 文本前處理      │
│  ├─ CKIP 斷詞 + POS      │
│  ├─ 停用詞過濾             │
│  ├─ 內容類型重分類          │
│  └─ 公司代碼 ↔ 文本關聯     │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Stage 2: 情緒分析        │
│  ├─ Layer 1: ANTUSD 字典  │  → sentiment_dict_score
│  ├─ Layer 2: FinBERT      │  → sentiment_bert_score, sentiment_bert_class
│  └─ 加權融合               │  → sentiment_final
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Stage 3: 主題建模        │
│  ├─ BERTopic 訓練/推論    │  → topic_id, topic_prob
│  ├─ 主題-情緒耦合          │  → topic_sentiment_*
│  └─ 產業主題映射           │  → sector_topic_score
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Stage 4: 因子聚合        │
│  ├─ 日度個股聚合           │  → 指數衰減加權
│  ├─ 市場整體聚合           │  → 全市場情緒均值
│  └─ Feature Store 整合    │  → merge_asof (PIT-safe)
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Stage 5: 視覺化          │
│  ├─ 文字雲生成             │  → Dashboard 頁面
│  ├─ 情緒時序圖             │  → 大盤情緒 vs 加權指數
│  └─ 主題熱力圖             │  → 話題熱度變化
└─────────────────────────┘
```

### 4.2 關鍵設計：新聞 → 日頻因子的時間對齊

新聞發佈時間不規則，需轉換為日頻時序以配合股價。採用**指數衰減聚合**：

```python
def aggregate_daily_sentiment(
    texts_df: pd.DataFrame,   # columns: company_id, post_date, sentiment_score
    target_date: pd.Timestamp,
    decay_lambda: float = 0.15,
    lookback_days: int = 7,
) -> float:
    """
    對 target_date 前 lookback_days 天的新聞做指數衰減加權平均。
    
    weight(t) = exp(-λ * (target_date - post_date).days)
    
    λ=0.15 時：
      - 當日新聞權重 = 1.00
      - 昨日新聞權重 = 0.86
      - 3 天前權重   = 0.64
      - 7 天前權重   = 0.35
    """
    mask = (texts_df["post_date"] <= target_date) & \
           (texts_df["post_date"] > target_date - pd.Timedelta(days=lookback_days))
    window = texts_df.loc[mask].copy()
    
    if len(window) == 0:
        return np.nan
    
    days_ago = (target_date - window["post_date"]).dt.days
    weights = np.exp(-decay_lambda * days_ago)
    
    return np.average(window["sentiment_score"], weights=weights)
```

### 4.3 向量化高效實作

112 萬筆逐一計算效率過低，實際實作改用**向量化 groupby + rolling**：

```python
# 1. 先計算每篇文章的 sentiment_score（批次推論）
# 2. Resample 到日頻
daily = (
    texts_df
    .set_index("post_date")
    .groupby("company_id")["sentiment_score"]
    .resample("1D")
    .agg(["mean", "count", "std"])
    .rename(columns={"mean": "sent_raw", "count": "news_count", "std": "sent_std"})
)

# 3. Exponential weighted moving average（pandas 原生高效）
daily["sent_ewm"] = (
    daily.groupby("company_id")["sent_raw"]
    .transform(lambda x: x.ewm(halflife=3, min_periods=1).mean())
)
```

---

## 五、產出因子清單

### 5.1 個股因子（event_ 前綴）

| 因子名稱 | 計算方式 | 來源 |
|----------|----------|------|
| `event_sentiment_1d` | 當日情緒分數（EWMA, halflife=1） | FinBERT |
| `event_sentiment_5d` | 5 日情緒均值（EWMA, halflife=3） | FinBERT |
| `event_sentiment_std_5d` | 5 日情緒標準差（情緒波動度） | FinBERT |
| `event_sentiment_dict` | 字典法情緒分數（ANTUSD 基線） | ANTUSD |
| `event_sentiment_delta` | 情緒變化量（今日 - 5 日前） | FinBERT |
| `event_news_volume_ratio` | 新聞量比（今日 / 20 日均值） | 統計 |
| `event_positive_ratio` | 正面新聞佔比（7 日窗口） | FinBERT |
| `event_topic_diversity` | 主題多樣性（entropy of topic distribution） | BERTopic |

### 5.2 市場因子（risk_ 前綴）

| 因子名稱 | 計算方式 | 來源 |
|----------|----------|------|
| `risk_market_sentiment` | 全市場日度情緒均值 | FinBERT |
| `risk_sentiment_dispersion` | 個股情緒離散度（cross-sectional std） | FinBERT |
| `risk_fear_index` | 負面新聞佔比（20 日滾動） | FinBERT |
| `risk_keyword_surprise` | 關鍵詞異常度（KL 散度 vs 30 日基線） | TF-IDF |

### 5.3 主題因子（event_ 前綴）

| 因子名稱 | 計算方式 | 來源 |
|----------|----------|------|
| `event_topic_hot` | 該公司最熱主題的當週出現頻率 | BERTopic |
| `event_topic_sentiment` | 最熱主題的加權情緒 | BERTopic × FinBERT |

### 5.4 TF-IDF 因子

| 因子名稱 | 計算方式 | 來源 |
|----------|----------|------|
| `event_tfidf_novelty` | 當日 TF-IDF 向量與 30 日均值的餘弦距離 | TF-IDF |
| `event_keyword_momentum` | 高頻詞出現頻率的 5 日動量 | TF-IDF |

**Phase 5 新增因子：16 個**  
**加上 Phase 4 的 51 個 → 總計約 67 個候選因子**（經 MI → VIF → Stability 三階段篩選後預計保留 25–35 個）

---

## 六、程式碼架構

### 6.1 新增檔案

```
程式碼/
├── src/
│   ├── nlp/                          ← 新增模組
│   │   ├── __init__.py
│   │   ├── tokenizer.py             # CKIP 斷詞 + POS + NER
│   │   ├── sentiment_dict.py        # ANTUSD 字典法情緒
│   │   ├── sentiment_bert.py        # FinBERT 微調 + 推論
│   │   ├── topic_model.py           # BERTopic 主題建模
│   │   ├── tfidf_features.py        # TF-IDF + 關鍵詞異常
│   │   ├── aggregator.py            # 日度因子聚合 + 衰減函數
│   │   └── wordcloud_gen.py         # 文字雲生成
│   └── features/
│       └── engineer.py              # 擴展：整合 NLP 因子
├── 資料抓取/
│   └── 下載情緒字典.py               # 下載 ANTUSD 等資源
├── 儀表板/
│   └── pages/
│       └── 8_📝_NLP_Text_Analysis.py  # 新 Dashboard 頁面
├── 執行Phase5_NLP文本分析.py          ← 新增主執行腳本
└── 測試/
    └── test_nlp.py                   # NLP 單元測試
```

### 6.2 設定檔擴展（base.yaml）

```yaml
nlp:
  tokenizer: "ckip"                    # ckip | jieba
  sentiment:
    dict_path: "選用資料集/lexicon/antusd.json"
    bert_model: "bert-base-chinese"    # HuggingFace model name
    bert_batch_size: 64
    bert_max_length: 64                # 標題最大長度
    num_classes: 3                     # positive / neutral / negative
    decay_lambda: 0.15                 # 指數衰減係數
    lookback_days: 7                   # 情緒窗口
  topic:
    model: "bertopic"
    embedding: "paraphrase-multilingual-MiniLM-L12-v2"
    min_topic_size: 50
    nr_topics: 30                      # auto-reduce to ~30 topics
  tfidf:
    max_features: 5000
    ngram_range: [1, 2]
    novelty_baseline_days: 30
  wordcloud:
    font_path: "選用資料集/fonts/NotoSansCJKtc-Regular.otf"
    max_words: 200
    width: 1200
    height: 600
```

---

## 七、執行步驟

### Step 0：環境準備
```bash
pip install ckip-transformers transformers torch bertopic \
    sentence-transformers jieba wordcloud matplotlib
```

### Step 1：CKIP 斷詞（預計 30–60 分鐘）
- 對 112 萬筆標題進行斷詞、POS 標記
- 產出：`outputs/nlp/tokenized.parquet`

### Step 2：ANTUSD 字典情緒（預計 5 分鐘）
- 基於字典計算每篇文章情緒分數
- 產出：`outputs/nlp/sentiment_dict.parquet`
- 同時作為 FinBERT 微調的弱標籤來源

### Step 3：FinBERT 微調（預計 2–4 小時，需 GPU）
- 用 Step 2 的弱標籤 + 人工抽樣校正（約 500–1,000 筆）訓練 3-class classifier
- 若無 GPU，可用 ANTUSD 字典法作為最終方案（降級模式）
- 產出：`outputs/models/finbert_sentiment/`

### Step 4：FinBERT 批次推論（預計 30–60 分鐘）
- 對全量 112 萬筆標題進行情緒預測
- 產出：`outputs/nlp/sentiment_bert.parquet`

### Step 5：BERTopic 主題建模（預計 20–40 分鐘）
- 訓練 BERTopic 模型，辨識 20–30 個金融主題
- 產出：`outputs/nlp/topics.parquet`、`outputs/models/bertopic/`

### Step 6：TF-IDF 關鍵詞萃取（預計 10 分鐘）
- 計算每日 TF-IDF 向量、keyword surprise 指標
- 產出：`outputs/nlp/tfidf_features.parquet`

### Step 7：因子聚合 + Feature Store 整合（預計 10 分鐘）
- 指數衰減日度聚合、市場整體指標
- 合併至 `feature_store.parquet`
- 產出：更新版 Feature Store（約 67 個候選因子）

### Step 8：文字雲 + Dashboard 頁面
- 生成各時期文字雲圖片
- 新增 Streamlit NLP 分析頁面

### Step 9：重新執行 Phase 2 + Phase 3
- 以擴展後的 Feature Store 重新訓練模型
- 比較 NLP 因子加入前後的模型表現

---

## 八、品質閘門（Quality Gates）

| 檢查項目 | 通過標準 |
|----------|----------|
| 情緒分數覆蓋率 | > 80% 的交易日有情緒分數 |
| 字典 vs BERT 相關性 | Spearman ρ > 0.5（一致性檢查） |
| 情緒因子 IC | Rank IC > 0.02（有預測力） |
| BERTopic 主題一致性 | Coherence Score > 0.4 |
| 無前瞻偏差 | 情緒分數僅使用 post_time ≤ target_date 的文本 |
| Feature Store Inf 檢查 | 0 個 Inf 值 |
| VIF < 10 | NLP 因子與現有因子不嚴重共線 |

---

## 九、風險與備選方案

| 風險 | 影響 | 備選方案 |
|------|------|----------|
| 無 GPU、FinBERT 訓練太慢 | 無法做深度情緒分析 | 僅用 ANTUSD 字典法（降級模式，仍有 60–70% 效果） |
| 標題太短（平均 22 字） | BERTopic 主題品質低 | 改用 LDA + jieba（對短文本更穩健） |
| ANTUSD 取得困難 | 字典法無法使用 | 用 SnowNLP 或自建簡易正負面詞表 |
| NLP 因子與價量因子高度共線 | VIF 篩選後 NLP 因子被刪除 | 使用 PCA 降維後的 NLP 複合因子 |
| 112 萬筆 BERT 推論太慢 | 時間不足 | 僅對近 6 個月 + 研報類文本做 BERT（約 20 萬筆） |

---

## 十、參考文獻

1. Wang et al. (2025). "BERT & LightGBM Stock Selection Framework." *SAGE Journals*.
2. Li et al. (2024). "BERTopic for Corporate Bond Default Prediction." *Finance Research Letters*, ScienceDirect.
3. MDPI (2023). "Chinese Financial News Analysis Framework." *Big Data and Cognitive Computing*, 9(10), 263.
4. Ku & Chen (2007). "ANTUSD: A Large Chinese Sentiment Dictionary." *LREC 2016*, ACL Anthology.
5. CKIP Lab (2020). "CKIP Transformers: Traditional Chinese NLP Toolkit." GitHub/HuggingFace.
6. FinBERT-LSTM (2024). "Stock Prediction Using Sentiment-Enhanced Deep Learning." *ACM Digital Library*.

---

## 十一、預估時程

| 階段 | 工作項目 | 預估時間 |
|------|----------|----------|
| Week 1 | CKIP 斷詞 + ANTUSD 字典情緒 + TF-IDF | 3 天 |
| Week 1 | FinBERT 微調（含資料標記） | 2 天 |
| Week 2 | FinBERT 批次推論 + BERTopic | 2 天 |
| Week 2 | 因子聚合 + Feature Store 整合 | 1 天 |
| Week 2 | Dashboard 文字雲 + 情緒頁面 | 1 天 |
| Week 3 | Phase 2/3 重跑 + 效果比較 | 2 天 |
| Week 3 | 品質報告 + 文件整理 | 1 天 |
