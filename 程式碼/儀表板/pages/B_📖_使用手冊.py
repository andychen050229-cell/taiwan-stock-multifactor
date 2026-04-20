"""
使用手冊 — 白話版系統解說

設計目標：
  非技術人士（投資新手 / 學術審閱者 / 一般使用者）在 5 分鐘內搞懂：
    · 這系統在做什麼
    · 9 大面向是什麼
    · 術語對照（專業詞 → 白話）
    · 品質保證（為什麼可信）
    · 使用流程（該從哪看起）
    · 限制與免責（這不是投資建議）
"""

from pathlib import Path
import importlib.util
import streamlit as st

# ---- Shared utils ----
_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
render_hero = _utils.render_hero
render_topbar = _utils.render_topbar

inject_custom_css()

# ============================================================================
# Manual-specific local CSS
# ============================================================================
st.markdown("""
<style>
.mn-hero-card {
    background: linear-gradient(135deg, #ffffff 0%, #f0fafe 50%, #eef2ff 100%);
    border: 1px solid rgba(6,182,212,0.18);
    border-left: 4px solid #06b6d4;
    border-radius: 16px;
    padding: 26px 30px;
    margin: 14px 0 24px 0;
    box-shadow: 0 4px 18px rgba(15,23,42,0.04);
}
.mn-hero-card h2 { margin: 0 0 12px 0 !important; padding-left: 0 !important; color: #0f172a !important; }
.mn-hero-card h2::before { display: none !important; }
.mn-hero-card p { color: #334155 !important; font-size: 1.02rem !important; line-height: 1.85 !important; margin: 0 0 8px 0 !important; }

.mn-tile {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 18px 20px 16px 20px;
    height: 100%;
    transition: all .22s ease;
    position: relative;
    overflow: hidden;
}
.mn-tile::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #06b6d4, #2563eb);
    opacity: 0.85;
}
.mn-tile:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(6,182,212,0.12);
    border-color: rgba(6,182,212,0.45);
}
.mn-tile-head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
}
.mn-tile-icon {
    width: 34px; height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    font-size: 1.05rem;
    background: linear-gradient(135deg, rgba(6,182,212,0.14), rgba(37,99,235,0.1));
    color: #2563eb;
    border: 1px solid rgba(6,182,212,0.28);
}
.mn-tile-title {
    font-family: 'Inter', 'Microsoft JhengHei', sans-serif;
    font-size: 1.02rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.005em;
}
.mn-tile-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    color: #06b6d4;
    letter-spacing: 0.16em;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.mn-tile-body {
    font-size: 0.92rem;
    color: #475569;
    line-height: 1.72;
}
.mn-tile-body strong { color: #0f172a; }
.mn-tile-example {
    margin-top: 12px;
    padding: 10px 12px;
    background: #f8fafc;
    border-left: 2px solid #06b6d4;
    border-radius: 6px;
    font-size: 0.84rem;
    color: #334155;
    line-height: 1.6;
}

.mn-jargon {
    width: 100%;
    border-collapse: collapse;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(15,23,42,.04);
}
.mn-jargon th {
    text-align: left;
    padding: 12px 16px;
    background: #f1f5f9;
    color: #0f172a;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-bottom: 1px solid #e2e8f0;
}
.mn-jargon td {
    padding: 12px 16px;
    border-bottom: 1px solid #f1f5f9;
    color: #334155;
    font-size: 0.92rem;
    line-height: 1.6;
}
.mn-jargon tr:last-child td { border-bottom: none; }
.mn-jargon tr:hover td { background: #f8fafc; }
.mn-jargon .j-term { font-family: 'JetBrains Mono', monospace; color: #2563eb; font-weight: 700; font-size: 0.88rem; white-space: nowrap; }
.mn-jargon .j-plain { color: #0f172a; font-weight: 600; }

.mn-flow {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 18px 0;
}
@media (max-width: 900px) { .mn-flow { grid-template-columns: 1fr 1fr; } }
.mn-flow-step {
    background: linear-gradient(135deg, #ffffff 0%, #f0fafe 100%);
    border: 1px solid rgba(6,182,212,0.22);
    border-radius: 12px;
    padding: 14px 16px;
    position: relative;
}
.mn-flow-step::before {
    content: attr(data-num);
    position: absolute;
    top: -12px;
    left: 14px;
    width: 26px; height: 26px;
    border-radius: 50%;
    background: linear-gradient(135deg, #06b6d4, #2563eb);
    color: #ffffff;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 0.82rem;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(6,182,212,0.35);
}
.mn-flow-step-title {
    font-weight: 700;
    color: #0f172a;
    font-size: 0.96rem;
    margin: 8px 0 6px 0;
}
.mn-flow-step-desc {
    font-size: 0.84rem;
    color: #475569;
    line-height: 1.6;
}

.mn-callout {
    padding: 14px 18px;
    border-radius: 12px;
    margin: 14px 0;
    font-size: 0.94rem;
    line-height: 1.7;
}
.mn-callout.ok {
    background: linear-gradient(135deg, #ecfdf5 0%, #f0fdfa 100%);
    border: 1px solid rgba(16,185,129,0.25);
    border-left: 3px solid #10b981;
    color: #064e3b;
}
.mn-callout.warn {
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    border: 1px solid rgba(245,158,11,0.3);
    border-left: 3px solid #f59e0b;
    color: #713f12;
}
.mn-callout.info {
    background: linear-gradient(135deg, #f0fafe 0%, #eff6ff 100%);
    border: 1px solid rgba(6,182,212,0.25);
    border-left: 3px solid #06b6d4;
    color: #0c4a6e;
}
.mn-callout strong { color: #0f172a; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Topbar
# ============================================================================
render_topbar(
    crumb_left="股票預測系統",
    crumb_current="使用手冊",
    chips=[("READ ME FIRST", "pri"), ("白話版", "vio"), ("5 分鐘讀完", "ok")],
    show_clock=True,
)

# ============================================================================
# Hero — what this system does
# ============================================================================
render_hero(
    eyebrow="MANUAL · 使用手冊",
    title_html='讀完這一頁，你就懂<span class="gl-hero-accent">　整個系統</span>',
    subtitle=(
        "這不是一份投資建議 APP —— 它是把<strong>「一檔股票值不值得關注」</strong>這件事，<br>"
        "拆成 9 個面向、用 <strong>94.8 萬筆歷史資料</strong>訓練出來的<strong>研究展示</strong>。<br>"
        "下面用大白話一次說清楚：<em>它在看什麼、怎麼看、你能怎麼用</em>。"
    ),
    meta_chips=[
        ("學術研究用途", "default"),
        ("非投資建議", "warn"),
        ("2023/03 – 2025/03", "ok"),
    ],
    show_orbit=False,
)

# ============================================================================
# § 1. 一頁看懂：這系統在做什麼
# ============================================================================
st.markdown("## 1. 一頁看懂：這系統在做什麼")

st.markdown("""
<div class="mn-hero-card">
<h2>一句話：把「研究一檔股票」這件事變成<span style="color:#2563eb;">可量化、可驗證、可回看</span>的流程。</h2>
<p>傳統看盤：看技術線型、聽新聞、讀財報 —— <strong>仰賴經驗與直覺</strong>。</p>
<p>這套系統：同時對 <strong>1,930 檔台股</strong>、同一套 <strong>91 個指標</strong>、跑 <strong>2 年 × 每個交易日</strong>，產出一個「這檔股票未來 20 天相對大盤會不會跑贏」的<strong>機率分數</strong>。</p>
<p>它不預測股價數字，而是<strong>排序</strong> —— 把今天的 1,930 檔由最看好排到最不看好，研究者可以專注看前 10% 的標的。</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="mn-callout info">
<strong>一句關鍵：</strong>機率高 ≠ 一定會漲。它的意思是<strong>「在同樣的歷史情境下，這類股票平均表現比大盤好」</strong>。就像氣象預報「70% 降雨機率」—— 不是一定下雨，但你最好帶傘。
</div>
""", unsafe_allow_html=True)

# ============================================================================
# § 2. 9 大面向（白話版）
# ============================================================================
st.markdown("## 2. 九大面向：系統用哪些角度看股票")
st.markdown(
    '<p style="color:#475569;font-size:0.96rem;line-height:1.7;margin-top:-8px;">'
    "判斷一檔股票時，人類會同時想很多事 —— 趨勢好不好？賺不賺錢？貴不貴？有沒有利多新聞？"
    "系統把這些整理成 <strong>9 個獨立面向</strong>，每個面向背後有一群量化指標。"
    "這樣做的好處是：你可以<strong>逐一追問</strong>「是誰把機率推高的」。"
    '</p>',
    unsafe_allow_html=True,
)

PILLARS = [
    ("趨勢面", "TREND", "📈",
     "股價過去幾天 / 幾週是上升、下降還是盤整。",
     "像爬山：前 10 天一直往上的股票，接下來一週繼續上走的機率比較高（除非過熱反轉）。"),
    ("基本面", "FUND", "💼",
     "公司本身賺不賺錢、負債高不高、營運效率如何。",
     "ROE 15%、負債比 30%，就比 ROE 5%、負債比 80% 的公司體質好 —— 系統會量化這些數字。"),
    ("估值面", "VAL", "💎",
     "現在股價相對公司價值是偏貴還是偏便宜。",
     "同樣賺 10 元的公司，股價 100 元（本益比 10）比 300 元（本益比 30）便宜。"),
    ("事件面", "EVENT", "📢",
     "除權息、發布新品、併購、法說會等<strong>重要日期</strong>前後的影響。",
     "法說會隔天，股價平均會反應一次 —— 系統記住「事件前後 5 天」的歷史行為。"),
    ("風險面", "RISK", "🎯",
     "股價波動多大、跌起來有多兇、跟大盤連動性如何（系統性風險）。",
     "同樣預期報酬 10%，波動度 5% 的股票比 30% 的好 —— 夏普值高代表「報酬/風險」比優。"),
    ("籌碼面", "CHIP", "🏦",
     "誰在買、誰在賣 —— 外資、投信、大戶、散戶的持股變化。",
     "外資連 5 天買超 + 投信同步買，通常是機構看好的訊號；反之則要留意。"),
    ("產業面", "IND", "🏭",
     "個股在<strong>所屬產業</strong>中的相對表現（超額報酬、排名）。",
     "AI 題材火熱時，即使是半導體最弱的一檔，漲幅可能也贏過金融股最強的一檔。"),
    ("文字面", "TXT", "📝",
     "新聞標題、公告摘要裡出現<strong>哪些關鍵字</strong>、頻率多高。",
     "「訂單能見度高」「毛利率創新高」這類字眼出現時，未來 20 天的機率會往上。"),
    ("情緒面", "SENT", "🔥",
     "新聞、社群、公告的<strong>情緒傾向</strong>（正面 / 中立 / 負面）。",
     "短期情緒極熱（+極端正面）反而是<strong>反指標</strong> —— 散戶過熱時常常在高點追進。"),
]

# Render 9 pillars as 3×3 grid
for row_start in (0, 3, 6):
    cols = st.columns(3, gap="medium")
    for i, col in enumerate(cols):
        pn = row_start + i
        if pn >= len(PILLARS):
            break
        zh, en, icon, desc, example = PILLARS[pn]
        with col:
            st.markdown(f"""
<div class="mn-tile">
  <div class="mn-tile-eyebrow">{en} · 面向 {pn+1}</div>
  <div class="mn-tile-head">
    <div class="mn-tile-icon">{icon}</div>
    <div class="mn-tile-title">{zh}</div>
  </div>
  <div class="mn-tile-body">{desc}</div>
  <div class="mn-tile-example"><strong>舉例：</strong>{example}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# § 3. 專有名詞白話對照
# ============================================================================
st.markdown("## 3. 專有名詞對照：你會看到這些縮寫")

st.markdown("""
<table class="mn-jargon">
<thead>
<tr><th style="width:180px;">縮寫 / 術語</th><th style="width:200px;">中文白話名稱</th><th>它在衡量什麼（口語版）</th></tr>
</thead>
<tbody>
<tr><td class="j-term">AUC</td><td class="j-plain">預測正確率</td>
    <td>0.5 = 亂猜，1.0 = 神準。我們系統 <strong>0.65</strong> 表示「比亂猜好 30%」，以金融資料來說算不錯。</td></tr>
<tr><td class="j-term">IC</td><td class="j-plain">訊號相關性</td>
    <td>系統打的分數，跟實際未來報酬的一致程度。<strong>正值越大越好</strong>，0.05 在金融領域就算有實用價值。</td></tr>
<tr><td class="j-term">ICIR</td><td class="j-plain">訊號穩定度</td>
    <td>IC 是平均，ICIR 看「這個相關性穩不穩」。<strong>高 ICIR = 訊號可靠度高，不是靠運氣</strong>。</td></tr>
<tr><td class="j-term">DSR</td><td class="j-plain">膨脹調整後夏普值</td>
    <td>傳統夏普值會被「多次嘗試」膨脹。DSR 扣除這個偏誤，<strong>DSR > 1 才算真有效</strong>。我們系統 12.12 代表極穩健。</td></tr>
<tr><td class="j-term">Walk-Forward CV</td><td class="j-plain">時序交叉驗證</td>
    <td>用 2023 上半年資料訓練 → 測 2023 下半 → 用 2023 全年訓練 → 測 2024 上半… <strong>絕不偷看未來</strong>。</td></tr>
<tr><td class="j-term">LOPO</td><td class="j-plain">拔掉一面向測試</td>
    <td>把 9 個面向輪流拿掉一個，看模型表現掉多少。<strong>掉越多表示這個面向越重要</strong>。</td></tr>
<tr><td class="j-term">Threshold Sweep</td><td class="j-plain">門檻敏感度掃描</td>
    <td>「機率大於幾才出手」測試。門檻 0.6 跟 0.8 誰更划算？結果顯示最佳門檻約 <strong>0.62</strong>。</td></tr>
<tr><td class="j-term">D+20 / D+5 / D+1</td><td class="j-plain">預測期限</td>
    <td>D+20 = 預測未來 20 個交易日（約一個月）。D+5 ≈ 一週、D+1 = 下一交易日。<strong>D+20 最準、D+1 最隨機</strong>。</td></tr>
<tr><td class="j-term">Feature Store</td><td class="j-plain">特徵倉庫</td>
    <td>所有指標算好、對齊時間、存成同一張大表。<strong>948,976 列 × 1,623 欄</strong> 就是 2 年 × 每日 × 每檔股票 × 每個指標。</td></tr>
<tr><td class="j-term">Quality Gate</td><td class="j-plain">品質閘門</td>
    <td>9 項自動檢查（資料完整性、無穿越、樣本外無污染等）。<strong>必須 9/9 全通過才算可信</strong>。</td></tr>
<tr><td class="j-term">Model Card</td><td class="j-plain">模型身分證</td>
    <td>每個模型都有一張「身分證」：訓練時間、資料範圍、表現、限制。<strong>像藥品仿單一樣透明</strong>。</td></tr>
<tr><td class="j-term">Data Drift</td><td class="j-plain">資料漂移</td>
    <td>市場情況變了，模型還能不能用？系統會自動偵測「今天的資料分布是否跟訓練時不同」並示警。</td></tr>
</tbody>
</table>
""", unsafe_allow_html=True)

# ============================================================================
# § 4. 使用流程
# ============================================================================
st.markdown("## 4. 怎麼逛這個網站？4 步驟建議路線")

st.markdown("""
<div class="mn-flow">
<div class="mn-flow-step" data-num="1">
  <div class="mn-flow-step-title">🧭 情境主控台</div>
  <div class="mn-flow-step-desc">首頁。看今天的<strong>系統總體健康度</strong>、9 大面向誰最強、熱門股票快照。</div>
</div>
<div class="mn-flow-step" data-num="2">
  <div class="mn-flow-step-title">🌱 投資觀察台</div>
  <div class="mn-flow-step-desc">白話版的「今天值得關注什麼」。推薦清單 + 為什麼推 + 注意事項。<strong>一般使用者從這裡</strong>。</div>
</div>
<div class="mn-flow-step" data-num="3">
  <div class="mn-flow-step-title">🔬 研究工作站</div>
  <div class="mn-flow-step-desc">技術細節。回測成果、特徵重要度、信號穩定度等。<strong>分析師進階用</strong>。</div>
</div>
<div class="mn-flow-step" data-num="4">
  <div class="mn-flow-step-title">🛡️ 治理監控</div>
  <div class="mn-flow-step-desc">模型是否還可信？Model Card、資料漂移警示、品質閘門狀態。<strong>透明度保證</strong>。</div>
</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="mn-callout ok">
<strong>新手建議路線：</strong>① 情境主控台（30 秒總覽）→ ② 投資觀察台（5 分鐘細看）→ ④ 治理監控（確認系統可信度）。想深入研究再看 ③ 研究工作站。
</div>
""", unsafe_allow_html=True)

# ============================================================================
# § 5. 品質保證：為什麼這套系統可信
# ============================================================================
st.markdown("## 5. 品質保證：為什麼這套系統的結果<em style='color:#2563eb;'>不是亂講</em>")

qg_col1, qg_col2 = st.columns(2, gap="medium")
with qg_col1:
    st.markdown("""
<div class="mn-tile">
<div class="mn-tile-eyebrow">QUALITY GATE · 9/9 PASS</div>
<div class="mn-tile-head"><div class="mn-tile-icon">✓</div><div class="mn-tile-title">9 項自動檢查全通過</div></div>
<div class="mn-tile-body">
  每次資料更新，系統自動跑 9 項檢查：資料完整性、<strong>無未來資訊穿越</strong>、樣本外乾淨、
  特徵工程一致、模型可重現、回測合理、風險指標達標、文字日期未錯位、情緒分數分布合理。<br><br>
  <strong>任何一項不過，整個結果就不上架</strong>。
</div>
</div>
""", unsafe_allow_html=True)
with qg_col2:
    st.markdown("""
<div class="mn-tile">
<div class="mn-tile-eyebrow">DSR · 12.12</div>
<div class="mn-tile-head"><div class="mn-tile-icon">🎯</div><div class="mn-tile-title">膨脹調整後夏普值極高</div></div>
<div class="mn-tile-body">
  學術文獻規定：做回測<strong>嘗試越多次，能偶然得到好結果的機率越高</strong>（過度擬合）。
  DSR 扣除這個偏誤後仍有 12.12，表示這套策略的績效<strong>不是靠運氣湊出來的</strong>。<br><br>
  一般 DSR > 1 就算有效，>3 就是學術等級。
</div>
</div>
""", unsafe_allow_html=True)

qg_col3, qg_col4 = st.columns(2, gap="medium")
with qg_col3:
    st.markdown("""
<div class="mn-tile">
<div class="mn-tile-eyebrow">WALK-FORWARD · EMBARGO=20</div>
<div class="mn-tile-head"><div class="mn-tile-icon">⏱️</div><div class="mn-tile-title">時序交叉驗證，嚴禁偷看未來</div></div>
<div class="mn-tile-body">
  模型只能看「今天以前」的資料來預測，<strong>embargo=20</strong> 意思是訓練與測試之間留 20 天空窗，
  避免「訓練集最後一天」跟「測試集第一天」的資訊互相汙染。<br><br>
  金融學界的<strong>最嚴謹驗證標準</strong>。
</div>
</div>
""", unsafe_allow_html=True)
with qg_col4:
    st.markdown("""
<div class="mn-tile">
<div class="mn-tile-eyebrow">MODEL CARD · 透明揭露</div>
<div class="mn-tile-head"><div class="mn-tile-icon">🛡️</div><div class="mn-tile-title">每個模型都有身分證</div></div>
<div class="mn-tile-body">
  像藥品仿單一樣，每個模型公開：<br>
  · 使用資料範圍（2023/03–2025/03）<br>
  · AUC / IC / DSR 指標<br>
  · 已知限制（例如：極端市場下可能失效）<br><br>
  <strong>治理監控頁可逐一查看</strong>。
</div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# § 6. 限制與免責
# ============================================================================
st.markdown("## 6. 重要限制與免責聲明")

st.markdown("""
<div class="mn-callout warn">
<strong>⚠️ 本系統是學術研究展示平台，不是投資建議。</strong><br><br>

<strong>已知限制：</strong><br>
· 訓練資料僅涵蓋 <strong>2023/03 – 2025/03</strong> 約 2 年台股市場。極端事件（金融海嘯、疫情暴跌）不在訓練集內，遇到時表現未知。<br>
· 預測的是「相對大盤表現」—— 大盤大跌時，被推薦的股票可能只是<strong>跌得比較少</strong>，不代表會漲。<br>
· 模型<strong>不考慮流動性限制</strong> —— 冷門小型股即使分數高，實務也可能買不到那麼多量。<br>
· 不包含<strong>個人稅務、手續費、融資成本</strong>等實際交易因素（「標準成本情境」雖已含基礎交易成本，但個人費率會有差異）。<br><br>

<strong>任何投資決定由使用者自行負責。</strong>本系統作者、貢獻者不對任何損失負責。
</div>
""", unsafe_allow_html=True)

# ============================================================================
# § 7. 資料來源與時間範圍
# ============================================================================
st.markdown("## 7. 資料來源與時間範圍")

st.markdown("""
<table class="mn-jargon">
<thead>
<tr><th>項目</th><th>內容</th></tr>
</thead>
<tbody>
<tr><td class="j-plain">時間範圍</td><td>2023/03/01 – 2025/03/31 (2 年，含 504 個交易日)</td></tr>
<tr><td class="j-plain">股票池</td><td>台股上市櫃 <strong>1,930 檔</strong>（排除金融、ETF 等特殊類別）</td></tr>
<tr><td class="j-plain">原始資料集</td><td>日 K、財報、法人買賣超、融資融券（已下架 2025/06）、新聞文字</td></tr>
<tr><td class="j-plain">Feature Store 規模</td><td><strong>948,976 列</strong> × 1,623 欄（每日每檔每指標一個點）</td></tr>
<tr><td class="j-plain">正式使用特徵數</td><td><strong>91 個</strong>（經時序穩定度 + 相關性篩選後的最終子集）</td></tr>
<tr><td class="j-plain">最近一次驗證</td><td><strong>2026-04-20 14:24</strong>（9/9 quality gates 全通過）</td></tr>
<tr><td class="j-plain">更新頻率</td><td>目前為凍結版（學術研究快照）。每次變動都會更新 Model Card 與版本時間戳</td></tr>
</tbody>
</table>
""", unsafe_allow_html=True)

st.markdown("""
<div class="mn-callout info" style="margin-top:22px;">
<strong>📖 看完這一頁，你已經比 95% 使用者更懂這系統。</strong><br>
接下來建議先到 <strong>🌱 投資觀察台</strong> 看白話版推薦，再回 <strong>🧭 情境主控台</strong> 看整體總覽。
任何時候想回來複習術語，從側邊欄的 <strong>❓ 手冊</strong> 按鈕一鍵回到這頁。
</div>
""", unsafe_allow_html=True)
