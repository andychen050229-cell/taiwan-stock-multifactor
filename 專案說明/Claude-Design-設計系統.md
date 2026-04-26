# Claude Design 設計系統手冊 — 台股多因子預測系統

> **版本**：1.0 · **日期**：2026-04-20
> **範圍**：`claude-design-bundle/` 完整設計交付包的內容、理念、Token、元件、頁面、實作對應
> **用途**：一份 Markdown 讓任何設計師 / 前端 / 研究員都能完整吃下 Claude Design 的所有產出

---

## 目錄

0. [什麼是 Claude Design？](#0-什麼是-claude-design)
1. [交付包結構](#1-交付包結構)
2. [設計哲學與定位](#2-設計哲學與定位)
3. [完整設計 Token 規格](#3-完整設計-token-規格)
4. [文本與內容原則](#4-文本與內容原則)
5. [視覺基礎](#5-視覺基礎)
6. [六大科技感設計手法](#6-六大科技感設計手法)
7. [八大核心元件規格](#7-八大核心元件規格)
8. [九支柱色彩系統](#8-九支柱色彩系統)
9. [資訊架構與導覽](#9-資訊架構與導覽)
10. [11 頁儀表板職責矩陣](#10-11-頁儀表板職責矩陣)
11. [圖表設計原則](#11-圖表設計原則)
12. [從 HTML Prototype 到 Streamlit 的映射](#12-從-html-prototype-到-streamlit-的映射)
13. [無障礙與響應式](#13-無障礙與響應式)
14. [反模式（Anti-Patterns）](#14-反模式anti-patterns)
15. [檔案索引](#15-檔案索引)

---

## 0. 什麼是 Claude Design？

**Claude Design（claude.ai/design）** 是 Anthropic 提供的 AI 設計工具，允許使用者在對話中與 AI 設計助理協作，產出 HTML/CSS/JS 原型。當設計定稿後，Claude Design 可把整個設計脈絡匯出為一個 **handoff bundle（交付包）**，讓另一個 coding agent（或真人前端）據此在目標程式棧上實作。

### 交付包的角色

```
┌─────────────────────┐       ┌──────────────────┐       ┌─────────────────────┐
│  Claude Design      │       │  Handoff Bundle  │       │  Target Codebase    │
│  (claude.ai/design) │  →→→  │  (HTML + chats)  │  →→→  │  (Streamlit + CSS)  │
│                     │       │                  │       │                     │
│  設計原型迭代        │       │  凍結設計意圖     │       │  像素級再現         │
└─────────────────────┘       └──────────────────┘       └─────────────────────┘
```

### 交付包的指導原則（來自 `design-system/README.md`）

> 1. **優先讀 chat transcripts** — 原型是結果，chat 是意圖所在。
> 2. **讀主設計檔案 + 順著 import 讀所有依賴**。
> 3. **不確定時先問使用者**，比做錯重做便宜。
> 4. **不要只看 HTML 外觀**，所有 dimensions / colors / layout rules 都在原始碼裡。
> 5. **實作技術自由** — HTML/CSS 只是媒介，React / Vue / Streamlit 都可以，重點是 **visual output 像素對齊**。

---

## 1. 交付包結構

完整目錄樹：

```
claude-design-bundle/
└── design-system/
    ├── README.md                                    ← Coding agent 須先讀
    ├── chats/
    │   └── chat1.md                                 ← 使用者與 AI 設計助理的對話紀錄
    └── project/
        ├── README.md                                ← Design system 主規格（反向工程自 codebase）
        ├── colors_and_type.css                      ← 權威 Design Tokens（CSS 變數）
        ├── uploads/
        │   └── 系統設計手冊.md                       ← 使用者上傳的原始設計手冊（1,182 行）
        ├── preview/                                  ← Design-System-tab 卡片預覽
        │   ├── _base.css                            ← Preview 頁共用 CSS
        │   ├── boxes.html                           ← 四種 insight-box 樣式
        │   ├── buttons.html                         ← 主/次/圖示按鈕
        │   ├── cards.html                           ← 標準 + hover + 六欄內容卡
        │   ├── chips.html                           ← 中性 / 強調 / 支柱三種 chip
        │   ├── colors_core.html                     ← 核心調色盤
        │   ├── colors_pillars.html                  ← 九支柱調色盤
        │   ├── colors_semantic.html                 ← 語意色（成功/警示/失敗/資料）
        │   ├── hero_preview.html                    ← Hero 區塊完整預覽
        │   ├── kpi.html                             ← KPI 卡完整預覽
        │   ├── live_indicator.html                  ← 脈動 LIVE 點
        │   ├── radii.html                           ← 圓角尺寸示範
        │   ├── shadows.html                         ← 四層陰影示範
        │   ├── spacing.html                         ← 4-pt grid 間距示範
        │   ├── type_body.html                       ← Body 字體階層
        │   ├── type_display.html                    ← Display 字體階層
        │   └── type_mono.html                       ← Mono 字體階層
        ├── ui_kits/
        │   └── dashboard/
        │       ├── README.md                        ← UI Kit 使用指引
        │       ├── index.html                       ← Dashboard 首頁 HTML 原型
        │       └── terminal.html                    ← Terminal 版（深色研究員視圖）
        ├── 台股多因子預測系統 - Dashboard.html       ← 完整 Dashboard HTML 原型
        └── 台股多因子預測系統 - Terminal.html        ← Terminal 版 HTML 原型
```

### 各資料夾的角色

| 資料夾 | 內容 | 讀取優先級 |
|---|---|---|
| `chats/` | 使用者與設計助理的對話逐字稿 | **P0**（先讀） |
| `project/README.md` | 反向工程自 codebase 的完整規格 | **P0** |
| `project/colors_and_type.css` | CSS 變數權威來源 | **P0** |
| `project/uploads/系統設計手冊.md` | 使用者自行撰寫的 1,182 行詳盡設計手冊 | **P1** |
| `project/preview/*.html` | 視覺化卡片預覽（Design System Tab） | **P2**（視覺參考） |
| `project/ui_kits/dashboard/` | Dashboard 的完整 HTML 原型 | **P2**（像素對齊） |
| `project/*.html`（根層兩份） | Dashboard + Terminal 雙版本原型 | **P2** |

---

## 2. 設計哲學與定位

### 2.1 產品定位（一句話）

> **台股多因子預測系統 · Taiwan Stock Multi-Factor Prediction System** 是一套 *data-dense, research-grade* 的 Streamlit 儀表板，將 948,976 筆樣本 × 1,623 候選因子，透過「九支柱 + 三階段篩選 + 雙引擎 ML + 嚴格驗證」，壓縮成月頻可交易的 Alpha 訊號。
>
> 它**不是即時交易產品**，而是 **historical snapshot interactive research terminal**（2023/03–2025/03 歷史快照研究終端機）。

### 2.2 三條設計軸

```
    科技感                     資料密度                   易讀性
       │                           │                          │
       │  Bloomberg Terminal        │  Notion / Linear         │  Apple HIG
       │  glint.trade               │  Superhuman              │  Material 3
       │                           │                          │
       └── 我們的定位點：「亮色版的 glint.trade · 中等資料密度 · 高易讀性」──┘
```

### 2.3 參考對標表

| 來源 | 我們借用 | 我們捨棄 |
|---|---|---|
| **glint.trade / terminal** | 等寬數字、grid overlay、instant feel | 深色、資訊過密、只給專業交易員 |
| **Bloomberg Terminal** | 資訊層級、脈動 LIVE 點、單色 accent | 深色黑底黃字、學習曲線太陡 |
| **財報狗 / 玩股網** | 「投資解讀面板」的敘事性 | 資訊擁擠、過度廣告 |
| **Stripe Dashboard** | 亮色 + 紫藍漸層 + 大方留白 | 商務 SaaS 氣質（我們是金融研究） |
| **Apple HIG** | 層級節奏、字體可讀性、圓角一致 | 太克制、缺少科技感 |
| **Refactoring UI** | 亮色設計系統教科書 — | — |

### 2.4 雙面板分流策略

一組資料、兩種敘事 — 同一視覺語言下的 **dual-reader experience**：

| 模式 | 對象 | 語氣 | 視覺特徵 |
|---|---|---|---|
| 🌱 **投資解讀面板** (Investor Interpretation) | 散戶、商業讀者、行銷、一般受眾 | 白話中文、左側暖色 accent 卡、免責聲明前置 | 溫暖、敘事導向 |
| ⚙️ **量化研究工作台** (Quant Research Bench) | 教授、評審、量化研究員 | 密集 KPI、圖表、表格、Mono 數字、Bloomberg 感 | 密集、術語豐富 |

團隊內部稱這種融合為 **「glint-light」** — 靈感來自 Bloomberg Terminal / glint.trade / 財報狗，但以亮色 + tech-grid 呈現。

### 2.5 五大設計價值主張

1. **Instant comprehension（立即理解）** — 每個數字都附 context（前期比較 / 基線 / 閾值）。
2. **Progressive disclosure（漸進揭露）** — 首頁只給結論，深度細節放子頁 Tab。
3. **Trust through transparency（透明即信任）** — 所有 KPI 可追溯到 JSON 原始檔。
4. **Dual-track experience（雙軌體驗）** — 散戶看敘事、研究員看公式。
5. **Tech as a signal of rigor（科技感作為嚴謹度訊號）** — `JetBrains Mono` 數字 + grid background = 暗示「這是嚴格驗證的結果，不是隨便猜的」。

### 2.6 招牌動作（Signature Moves）

| 動作 | 描述 |
|---|---|
| **Hero gradient title** | 三段 `slate → blue → violet` 的 `-webkit-background-clip: text` |
| **Tech grid canvas** | 40×40 px、`rgba(37,99,235,0.025)` 極淡藍色方格線，`fixed-attach` 貼在每頁背後 |
| **Left-accent insight boxes** | 4px 左邊框 + 柔和漸層填充；依語意（info/warn/ok/danger）著色 |
| **KPI tiles** | Off-white 卡、3px 彩色上邊框、`JetBrains Mono` + `tabular-nums` 數值、`UPPERCASE 0.76rem letter-spacing 0.06em` 標籤 |
| **Pillar badges** | 九色 factor-family pills（`trend / fund / val / event / risk / chip / ind / txt / sent`） |
| **Live chip** | 脈動綠點（`gl-pulse` keyframe 2s cubic-bezier infinite） |

---

## 3. 完整設計 Token 規格

> 權威來源：[colors_and_type.css](claude-design-bundle/design-system/project/colors_and_type.css)
> 所有 Token 以 `--gl-*`（glint-light）為前綴，在 CSS 內部透過 `var(--gl-*)` 引用。

### 3.1 中性色階（Canvas / Borders / Text）

| Token | HEX | 用途 |
|---|---|---|
| `--gl-bg` | `#fafbfc` | 主畫布（off-white，避免純白刺眼） |
| `--gl-surface` | `#ffffff` | 卡片 / 面板底色 |
| `--gl-subtle` | `#f1f5f9` | 表頭、Tag 底色 |
| `--gl-tint` | `#f8fafc` | Zebra 斑馬列、hover 微變 |
| `--gl-overlay` | `rgba(255,255,255,0.72)` | 玻璃擬態覆蓋層 |
| `--gl-border` | `#e2e8f0` | 常規分隔線 |
| `--gl-border-str` | `#cbd5e1` | 強調邊框（表頭、聚焦） |
| `--gl-text` | `#0f172a` | 主文字（near-black，不用純黑） |
| `--gl-text-2` | `#475569` | 次要文字、說明 |
| `--gl-text-3` | `#94a3b8` | 第三層 footnote、timestamp |

### 3.2 Sidebar（深色專業區）

| Token | HEX | 用途 |
|---|---|---|
| `--gl-sidebar-1` | `#0f1419` | Sidebar 漸層起點 |
| `--gl-sidebar-2` | `#1a2332` | Sidebar 漸層終點 |
| `--gl-sidebar-fg` | `#c8d6e5` | Sidebar 主文字 |
| `--gl-sidebar-mut` | `#8899aa` | Sidebar 次要文字 |

> **Sidebar 公式**：`linear-gradient(180deg, #0f1419 0%, #1a2332 100%)` — Bloomberg Terminal 的深色 DNA，只用在 sidebar（恆常顯示的導覽）。

### 3.3 強調色（Signal Palette）

| Token | HEX | 語意 | 使用情境 |
|---|---|---|---|
| `--gl-blue` | `#2563eb` | 主品牌色 | 主 CTA、連結、關鍵數字強調 |
| `--gl-violet` | `#7c3aed` | 副品牌色 | 漸層終點、次要強調 |
| `--gl-cyan` | `#06b6d4` | 科技感 | Tech-gradient 中段、資料視覺 |
| `--gl-emerald` | `#10b981` | 成功 / 正向 | PASS 閘門、正報酬、命中 |
| `--gl-amber` | `#f59e0b` | 警示 / 注意 | WARN、舊資料提示 |
| `--gl-rose` | `#f43f5e` | 失敗 / 負向 | FAIL、負報酬、Drawdown |
| `--gl-indigo` | `#4f46e5` | 備用 accent | 特定 Tag |
| `--gl-streamlit` | `#636EFA` | Streamlit 主題色 | 與內建 Plotly theme 相容 |

### 3.4 漸層系統

| Token | 定義 | 用途 |
|---|---|---|
| `--gl-grad-pri` | `linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)` | Hero 標題、左側條紋 |
| `--gl-grad-tech` | `linear-gradient(135deg, #06b6d4 0%, #2563eb 50%, #7c3aed 100%)` | Metric hover、頁首 accent bar |
| `--gl-grad-ok` | `linear-gradient(135deg, #10b981 0%, #06b6d4 100%)` | 成功面板 |
| `--gl-grad-warm` | `linear-gradient(135deg, #f59e0b 0%, #f43f5e 100%)` | 警示 / 風險面板 |
| `--gl-grad-hero-title` | `linear-gradient(135deg, #0f172a 0%, #2563eb 55%, #7c3aed 100%)` | Hero Title 專用（三段：slate → blue → violet） |

> **原則**：Blue → Violet 必須是**漸層**，不要以兩色分別出現。這是品牌的第一識別。

### 3.5 字體系統（Typography）

```css
--gl-font-sans: 'Inter', 'Noto Sans TC', -apple-system, BlinkMacSystemFont,
                'Segoe UI', 'Microsoft JhengHei', 'PingFang TC', sans-serif;
--gl-font-mono: 'JetBrains Mono', 'Noto Sans TC', 'SF Mono', 'Consolas',
                'Liberation Mono', monospace;
```

**Type Scale**

| Token | Size | 用途 |
|---|---|---|
| `--gl-fs-hero` | `2.6rem` | Hero 大標 |
| `--gl-fs-h1` | `2.1rem` | 一級標題 |
| `--gl-fs-h2` | `1.5rem` | 段落標題（左側漸層條） |
| `--gl-fs-h3` | `1.15rem` | 子段落 |
| `--gl-fs-body` | `0.95rem` | 內文 |
| `--gl-fs-caption` | `0.82rem` | 說明 / 副標 |
| `--gl-fs-micro` | `0.72rem` | KPI 標籤、eyebrow |
| `--gl-fs-kpi` | `2.0rem` | 自訂 KPI 數值 |
| `--gl-fs-metric` | `1.7rem` | Streamlit `st.metric` 數值 |

**Line-height / Letter-spacing**

| Token | 值 | 用途 |
|---|---|---|
| `--gl-lh-tight` | `1.1` | 標題 |
| `--gl-lh-body` | `1.6` | 內文 |
| `--gl-ls-tight` | `-0.03em` | Hero（壓縮字距） |
| `--gl-ls-h` | `-0.01em` | 一般標題 |
| `--gl-ls-label` | `0.06em` | KPI 大寫標籤 |
| `--gl-ls-eyebrow` | `0.10em` | 頂級 ALL-CAPS eyebrow |

**原則**
- 所有**數字** → Mono（tabular-nums）；所有**文字** → Inter + JhengHei fallback。
- Hero 標題用漸層 clip-text；其他標題用純 `--gl-text`，保可讀性。
- `text-transform: uppercase` 僅限 eyebrow / KPI label / 專有名詞縮寫。

### 3.6 圓角（Radii）

| Token | 值 | 用途 |
|---|---|---|
| `--gl-r-pill` | `999px` | Pill / Chip / 圓按鈕 |
| `--gl-r-xs` | `6px` | Tooltip、小輸入框 |
| `--gl-r-sm` | `8px` | 次級按鈕 |
| `--gl-r-md` | `10px` | 一般 box、按鈕 |
| `--gl-r-lg` | `14px` | 卡片 / 面板 |
| `--gl-r-xl` | `18px` | Hero |

> Left-accent insight boxes 使用**非對稱**圓角 `0 10px 10px 0`，讓 4px 左邊框像一面小旗。

### 3.7 間距（Spacing — 4pt grid）

| Token | 值 | 用途 |
|---|---|---|
| `--gl-space-1` | `4px` | 極小內邊距、圖示間距 |
| `--gl-space-2` | `8px` | 小間距 |
| `--gl-space-3` | `12px` | Tag 內邊距 |
| `--gl-space-4` | `16px` | 一般內邊距 |
| `--gl-space-5` | `20px` | 卡片 gap |
| `--gl-space-6` | `24px` | 面板 padding |
| `--gl-space-8` | `32px` | Section 間距 |
| `--gl-space-10` | `40px` | Hero padding、Section 大間距 |

### 3.8 陰影（Elevation）

| Level | Token | 定義 | 用途 |
|---|---|---|---|
| 0 | — | 無陰影 | 區塊底色 |
| 1 | `--gl-shadow-sm` | `0 1px 2px rgba(15,23,42,.04), 0 1px 3px rgba(15,23,42,.06)` | 卡片預設 |
| 2 | `--gl-shadow-md` | `0 4px 6px rgba(15,23,42,.04), 0 10px 15px rgba(15,23,42,.06)` | 面板 |
| 3 | `--gl-shadow-lg` | `0 10px 15px rgba(15,23,42,.06), 0 20px 25px rgba(15,23,42,.08)` | Modal / Tooltip |
| 4 | `--gl-shadow-glow` | `0 0 0 1px rgba(37,99,235,.08), 0 8px 30px rgba(37,99,235,.12)` | Hover focus glow（品牌藍） |

### 3.9 動效（Motion）

| Token | 值 | 說明 |
|---|---|---|
| `--gl-ease` | `cubic-bezier(.4,0,.2,1)` | 通用緩和 |
| `--gl-dur` | `.25s` | 通用過場 |

| 動效 | Duration | Easing | 觸發 |
|---|---|---|---|
| Card hover | 250 ms | `ease` | 滑鼠進入 |
| Button press | 150 ms | `ease-out` | 點擊 |
| Fade-in | 400 ms | `ease-in-out` | 頁面載入 |
| `gl-pulse`（LIVE 點） | 2 s loop | `cubic-bezier(0.4,0,0.6,1)` | 恆動 |
| Gradient scan（頁首） | 6 s loop | linear | 恆動 |

> **只用一個 keyframe `gl-pulse`**。嚴禁彈跳、視差、頁面載入動畫、旋轉星光。

### 3.10 Tech Grid Background

| Token | 值 | 用途 |
|---|---|---|
| `--gl-grid-size` | `40px` | 方格邊長 |
| `--gl-grid-color` | `rgba(37,99,235,0.025)` | 極淡藍格線 |

注入方式：

```css
body::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(var(--gl-grid-color) 1px, transparent 1px),
        linear-gradient(90deg, var(--gl-grid-color) 1px, transparent 1px);
    background-size: var(--gl-grid-size) var(--gl-grid-size);
    pointer-events: none;
    z-index: 0;
}
body > * { position: relative; z-index: 1; }
```

---

## 4. 文本與內容原則

### 4.1 語言混用（Code-switching）

- **繁體中文（zh-TW）為主**，技術詞彙自由混入英文（`AUC`, `ICIR`, `Purged Walk-Forward CV`, `Feature Store`, `Bootstrap`）。
- **Pipe-分隔雙語標題**常見於頁首：*「模型指標分析 | Model Metrics」*、*「選擇 Horizon | Select Horizon」*。
- **台式金融術語直接保留**：*出手率 / 籌碼 / 支柱 / 回測*。

### 4.2 語氣（Voice & Tone）

- **Confident but hedged（自信但謙遜）**。本系統是 *研究* 平台，不是投資建議。每個 headline metric 後必定跟著 caveat（Bootstrap CI、DSR、樣本提醒）。
- **研究員對同儕（Researcher-to-peer），非廠商對使用者**。預設讀者具備統計素養；散戶面板則「翻譯下去」，用類比與敘事。
- **第三人稱自稱**：*「本平台 / 本系統 / 本專案」*。幾乎不用 *你 / 您 / 我們*。
- **No marketing adjectives**。取而代之：*嚴謹 · 可回看 · 可解釋 · 可治理*。

### 4.3 大小寫（Casing）

- 中文：自然寫法，不花俏。
- 英文 **ALL-CAPS + letter-spacing 0.06–0.10em**：保留給 KPI 標籤（`SAMPLES`, `FEATURES`, `QUALITY`）與 eyebrow（`TAIWAN STOCK · MULTI-FACTOR PREDICTION`）。
- Monospace chip 採**小寫**：`xgboost_D20`, `initial_train=252`, `embargo=20`。

### 4.4 Emoji 使用規範

- **有，但是結構化的，不是裝飾性的**。
- 每個頁面 tab 有且僅有一個 section-defining emoji：🌱 📊 📈 💰 🔬 🗃️ 🛡️ 📡 🎯 📝 🔭。
- Box 用 📋 ⚠️ 📅 🎯 ✅ ❌ 作為狀態標記。
- **禁用情境**：
  - 兩個 emoji 連續
  - 當 bullet 點使用
  - 出現在 body copy 中
- **九支柱用色彩 badge，不用 emoji**。

### 4.5 數字格式

| 類型 | 規則 | 範例 |
|---|---|---|
| 百分比 | 2 位小數 + 符號（performance delta 時） | `+13.83%`、`−8.70%` |
| Basis points | 整數 + `bps` | `+1.5bps`、`12.12 → PASS` |
| 比率 / Metric | 3–4 位小數 | `AUC 0.6455`、`IC 0.015` |
| 大數字 | 千位逗號 | `948,976 rows`、`1,930 家上市櫃` |
| 百分號 | ASCII `%`，不用全形 `％` | — |

**所有金額與統計值必須使用** `font-family: JetBrains Mono` **搭配** `font-variant-numeric: tabular-nums`。

### 4.6 範例文案（直接引用）

> 以 **2023/03 – 2025/03** 台股歷史資料為基礎，整合 **9 支柱 1,623 候選因子**、**LightGBM + XGBoost 雙引擎**、**Purged Walk-Forward CV** 與 **LOPO 深度驗證**，提供可回看、可解釋、可治理的研究展示平台。

> ⚠️ **免責聲明**：本系統為課程專案成果，不構成任何投資建議。所有顯示結果均為歷史回測數據。

> 近期回撤僅 1%，價格走勢相對穩定；目前處於高波動環境，短期價格變動可能較劇烈。

---

## 5. 視覺基礎

### 5.1 背景三層堆疊

```
┌───────────────────────────────────────────────────┐
│ Layer 1  radial-gradient top-left  (藍色 5%)       │  ← 品牌氛圍
│ Layer 2  radial-gradient top-right (紫色 5%)       │  ← 品牌氛圍
│ Layer 3  linear-gradient 180deg to #fff at 400px  │  ← 畫面上輕、下白
└───────────────────────────────────────────────────┘
   + body::before tech-grid overlay (40px, 0.025 opacity, fixed)
```

CSS 實作：

```css
html, body {
    background:
        radial-gradient(ellipse at top left,  rgba(37,99,235,0.05) 0%, transparent 50%),
        radial-gradient(ellipse at top right, rgba(124,58,237,0.05) 0%, transparent 50%),
        linear-gradient(180deg, var(--gl-bg) 0%, #ffffff 400px);
    background-attachment: fixed;
}
```

### 5.2 Hover / Press 狀態

- **Card hover**：
  - `border: #e2e8f0 → rgba(37,99,235,0.35)`
  - `box-shadow → var(--gl-shadow-glow)`
  - `transform: translateY(-1px)`
  - 可選：頂部 `::before` 漸層 bar `opacity 0 → 1`

- **Primary Button**：
  - rest: `box-shadow: 0 4px 14px rgba(37,99,235,0.25)`
  - hover: `box-shadow: 0 6px 20px rgba(37,99,235,0.35)`

### 5.3 邊框系統

- `--gl-border: #e2e8f0` — 通用分隔線
- `--gl-border-str: #cbd5e1` — 聚焦 / 強調
- Accent bar 尺寸：**3px**（KPI card 上方）、**4px**（insight box 左側 / h2 左側）

### 5.4 透明度與模糊

- `rgba(255,255,255,0.72)` — 玻璃擬態 overlay 專用
- `filter: blur(40px)` — Hero 角落 glow disc
- **不要**在其他地方濫用 `backdrop-filter`（效能與風格都會崩）

### 5.5 無影像素材

- **無照片、無插畫、無手繪**。
- **圖表即 imagery** — Plotly 本身就是主要視覺語言。
- 若 docs / 行銷頁需要 icon，選用 **Lucide**（`stroke-width: 1.5; color: currentColor`），此為 **substitution**（原 codebase 無任何 icon library）。

---

## 6. 六大科技感設計手法

> 這是「讓資料看起來像專業系統而非 Excel」的核心技法清單。

### 6.1 Glass-morphism（玻璃擬態面板）

```css
.gl-panel {
    background: var(--gl-overlay);           /* rgba(255,255,255,0.72) */
    backdrop-filter: blur(12px);
    border: 1px solid var(--gl-border);
    border-radius: 20px;
    padding: 20px 24px;
    box-shadow: var(--gl-shadow-md);
}
```

**為什麼**：半透明 + 模糊讓面板「浮起」於 canvas 之上，視覺深度增加，同時保留背景網格可見，暗示「可疊加」的資訊層。

### 6.2 Tech-grid Background（科技網格）

見 [§3.10](#310-tech-grid-background)。

**為什麼**：40×40 px、opacity 0.025 的藍色極淡方格讓背景有「工程圖紙」質感。不干擾閱讀，但任何滑動都讓使用者感受到「這是一個精密系統」。

### 6.3 Gradient Title（漸層標題）

```css
.gl-hero-title,
.gl-title-gradient {
    font-size: 2.4rem;
    font-weight: 800;
    background: var(--gl-grad-hero-title);    /* slate → blue → violet */
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
    letter-spacing: -0.03em;
}
```

**為什麼**：單色標題 = 普通文件；漸層標題 = 品牌認同。**只在 Hero 使用**，其他標題仍是純黑以保可讀性。

### 6.4 Pulse Live Indicator（脈動即時點）

```css
.gl-live {
    display: inline-flex; align-items: center; gap: 8px;
    font-family: var(--gl-font-mono);
    font-size: 0.76rem;
    color: var(--gl-emerald);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.gl-live::before {
    content: "";
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--gl-emerald);
    animation: gl-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
@keyframes gl-pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0   rgba(16,185,129,0.7); }
    50%      { opacity: .8; box-shadow: 0 0 0 8px rgba(16,185,129,0);    }
}
```

**為什麼**：一個小小的綠點在 Hero 上脈動 → 使用者直觀感受「這個系統是活的、資料是最新的」。心理效應遠強於寫一行「資料更新至 2026-04-20」。

### 6.5 Mono-font for Numbers（等寬數字）

所有數字用 `JetBrains Mono` + `tabular-nums`：

```
Sharpe 0.81         ← 若用比例字，小數點會跑位
        vs
Sharpe 0.81         ← Mono + tabular-nums，數字在縱向完美對齊
```

**為什麼**：量化研究員一眼看到 `0.015` 是 `+0.015` 還是 `-0.015` 非常關鍵。等寬數字配合 tabular-nums 能讓比較時眼睛不用跳來跳去。

### 6.6 Accent Bar on H2（章節左側漸層條）

```css
.block-container h2 {
    position: relative;
    padding-left: 16px;
}
.block-container h2::before {
    content: "";
    position: absolute;
    left: 0; top: 4px; bottom: 4px;
    width: 4px;
    background: var(--gl-grad-pri);
    border-radius: 4px;
}
```

**為什麼**：每個 H2 標題左側都有一條 4 px 寬的藍紫漸層條，視覺錨點明確，讓長頁面捲動時仍能快速定位段落。

---

## 7. 八大核心元件規格

### 7.1 `<GlHero>` 頁首英雄區

**Anatomy**

```
┌──────────────────────────────────────────────────────┐
│  ◎ LIVE · 2026-04-20                                 │ ← gl-live 脈動點
│                                                      │
│  ┃ Phase 6 深度驗證                                  │ ← H1 漸層標題
│                                                      │
│  LOPO · Threshold Sweep · Single-Stock Case         │ ← 副標
└──────────────────────────────────────────────────────┘
   + 右上 blur glow disc
```

**Props / Slots**

| Slot | 必要 | 說明 |
|---|---|---|
| `eyebrow` | optional | `gl-live` 脈動指示器文字 |
| `title` | required | 頁面大標（套漸層） |
| `subtitle` | required | 一句話描述 |
| `actions` | optional | 右上角按鈕群 |

**規格**
- Padding: `40px 48px`
- Radius: `18px`
- Background: `var(--gl-surface)` 加右上角 `filter: blur(40px)` 藍紫漸層 disc
- Box-shadow: `var(--gl-shadow-md)`

### 7.2 `<GlKpi>` KPI 指標卡

**Anatomy**

```
┌─────────────────────────────┐
│  ▎▎▎ hover gradient bar      │ ← 3px top gradient（hover 出現）
│                              │
│  ANNUALIZED RETURN          │ ← label (uppercase)
│  +17.77%                    │ ← value (Mono, 28px)
│  △ vs baseline: +12.3%      │ ← delta
│  discount-cost scenario     │ ← sub
└─────────────────────────────┘
```

**Python 呼叫**

```python
from utils import render_kpi, THEME
render_kpi(
    label="Annualized Return",
    value="+17.77%",
    delta="△ vs baseline: +12.3%",
    sub="discount-cost scenario",
    accent=THEME["blue"],
)
```

**規格**
- Padding: `18px 22px`
- Radius: `14px`
- Border: `1px solid #e2e8f0`
- Top bar: 3px `var(--gl-grad-pri)`（hover 出現，`opacity 0 → 1`）
- Value: `JetBrains Mono 2.0rem, weight 700, tabular-nums`
- Label: `0.76rem, weight 600, UPPERCASE, letter-spacing 0.06em, color --gl-text-3`

### 7.3 `<GlPanel>` 通用面板

玻璃擬態容器，用於包裝一組相關內容。

```html
<div class="gl-panel">
  <div class="gl-panel-header">
    <h3>LOPO 支柱貢獻</h3>
    <span class="gl-chip">D+20</span>
  </div>
  <div class="gl-panel-body">
    <!-- 圖表 / 表格 / 敘述 -->
  </div>
</div>
```

**規格**
- `background: var(--gl-overlay)` + `backdrop-filter: blur(12px)`
- `border: 1px solid var(--gl-border)`
- `border-radius: 20px`
- `padding: 20px 24px`
- `box-shadow: var(--gl-shadow-md)`

### 7.4 `<GlChip>` / `<GlPillar>` 徽章

| 類型 | 用途 | 範例 |
|---|---|---|
| `.gl-chip` | 中性徽章、metadata | `D+20`、`2026-04-20`、`OOS` |
| `.gl-chip--accent` | 強調徽章 | `NEW`、`Phase 6` |
| `.gl-pillar` | 九支柱專用徽章（帶色） | `trend`、`risk`、`txt`、`sent` |

**標準樣式**
- `border-radius: 999px`
- `padding: 4px 12px`
- `font-family: var(--gl-font-mono)`
- `font-size: 0.72rem`
- `font-weight: 600`

### 7.5 `<GlTimeline>` 階段時間軸

用於呈現 Phase 1 → 6 的旅程：

```
P1 ──○── P2 ──○── P3 ──○── P4 ──○── P5 ──○── P6●
資料   模型   擴充   治理   文本   深度驗證 NEW
```

**規格**
- 水平線 2px `var(--gl-border-str)`
- 節點直徑 12px；已完成填 emerald、進行中填 blue、未完成描邊灰
- 當前 phase 加外發光 `0 0 0 4px rgba(37,99,235,0.15)`

### 7.6 `<GlAlert>` 告知橫幅

```
┌──────────────────────────────────────────────┐
│ ⓘ  本頁為 Phase 1 初版，當前已推進至 Phase 5B   │
│    1,623 → 91 features。詳見 Feature Analysis │
└──────────────────────────────────────────────┘
```

**四種 variant**：`info`（blue）· `success`（emerald）· `warn`（amber）· `error`（rose）

**規格**
- `border-radius: 0 10px 10px 0`（非對稱）
- Border-left: 4px `var(--gl-{variant})`
- Background: `linear-gradient(90deg, var(--gl-{variant})/12% 0%, transparent 60%)`
- Padding: `12px 16px`

### 7.7 `<GlDataTable>` 資料表

Streamlit `st.dataframe` 上加：

- `thead`：`var(--gl-subtle)` 底、大寫字、letter-spacing 0.06em
- `tbody`：zebra（`nth-child(even)` 套 `--gl-tint`）
- Row hover：`rgba(37,99,235,0.06)`
- 數值欄位：強制 `font-family: var(--gl-font-mono); font-variant-numeric: tabular-nums;`
- Border-radius: `10px` 外框 + `overflow: hidden`

### 7.8 `<GlPulse>` 即時指示器

見 [§6.4](#64-pulse-live-indicator脈動即時點)。

在強調即時性的頁面使用（Phase 6 深度驗證、Signal Monitor、首頁 Hero）。

---

## 8. 九支柱色彩系統

> 九個因子家族（factor pillars）以顏色區分，不使用 emoji。

| 支柱 | prefix | Token / Color | 語意 |
|---|---|---|---|
| **trend** | `trend_` | `--gl-blue` `#2563eb` | 趨勢與價格技術面 |
| **fund** | `fund_` | `--gl-emerald` `#10b981` | 基本面（ROE / Margin） |
| **val** | `val_` | `--gl-amber` `#f59e0b` | 估值（P/B, EV/EBITDA） |
| **event** | `event_` | `--gl-rose` `#f43f5e` | 事件（新聞提及） |
| **risk** | `risk_` | `--gl-indigo` `#4f46e5` | 風險（波動、MDD） |
| **chip** | `chip_` | `--gl-violet` `#7c3aed` | 籌碼（三大法人） |
| **ind** | `ind_` | `--gl-cyan` `#06b6d4` | 產業（相對強弱） |
| **txt** | `txt_` | `#0ea5e9` sky | 文本（關鍵字 rolling） |
| **sent** | `sent_` | `#ec4899` pink | 情緒（SnowNLP + 辭典） |

**使用規則**
- 徽章背景：`rgba({token}, 0.12)`，文字用 `{token}` 全飽和
- 邊框（可選）：`1px solid rgba({token}, 0.35)`
- 條件：僅用於 pillar badge / 條狀圖著色；不要濫用於 body text。

---

## 9. 資訊架構與導覽

### 9.1 導覽結構（`st.navigation`）

```
🏠 首頁
│
├── 📖 投資解讀 ────── 🌱 投資解讀面板              [散戶動線]
│
├── 🔬 量化研究工作台
│   ├── 📊 模型績效        ← Model Metrics
│   ├── 📈 ICIR 信號穩定性 ← ICIR Analysis
│   ├── 💰 策略回測        ← Backtest
│   ├── 🔬 特徵工程分析    ← Feature Analysis
│   ├── 🗃️ 資料品質總覽    ← Data Explorer
│   └── 📝 文本分析        ← Text Analysis
│
└── 🛡️ 模型治理與監控
    ├── 🛡️ 模型治理        ← Model Governance
    ├── 📡 信號監控        ← Signal Monitor
    ├── 🎯 擴充分析        ← Extended Analytics
    └── 🔭 Phase 6 深度驗證 [NEW]  ← LOPO / Threshold / 2454
```

### 9.2 三種使用者動線

```
散戶動線（小綠）：
  🏠 首頁 → 看 KPI → 選「投資解讀」→ 進 🌱 → 看推薦清單 → 離開

研究員動線（阿凱）：
  🏠 首頁 → 選「量化研究」→ 📊 模型績效 → 📈 ICIR →
   💰 回測 → 🔬 特徵 → 📝 文本 → 🗃️ 資料品質

評審動線（林教授）：
  🏠 首頁 → 📊 模型績效（看 AUC/Sharpe）→ 🛡️ 治理（看 9/9 閘門）→
   📡 信號監控（看漂移）→ 🎯 擴充分析（看成本敏感度）→
   🔭 Phase 6（看 LOPO 邊際貢獻）
```

### 9.3 Sidebar 設計（深色專業感）

```css
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1419 0%, #1a2332 100%);
}
```

**為何 sidebar 用深色、主內容用亮色？**

Bloomberg Terminal 用深色讓長時間看盤不刺眼；我們把這個概念用在 sidebar（恆常顯示的導覽），而主內容區保持亮色讓圖表 + 白板感更現代。這是**「兩種情緒的融合」**：

- 專業感 → 深色 Sidebar
- 開放感 → 亮色內容

---

## 10. 11 頁儀表板職責矩陣

| # | 頁面檔名 | 圖示 | 職責（一句話） | 主要資料源 |
|---|---|---|---|---|
| 0 | `home.py` | 🏠 | 專案總入口、6 KPI、Phase 時間軸 | 聚合 JSON |
| 1 | `0_🌱_投資解讀面板.py` | 🌱 | **散戶面板**：推薦清單 + 公司基本面 + 風險提示 | `recommendations.json` + `stock_prices.parquet` |
| 2 | `1_📊_Model_Metrics.py` | 📊 | AUC / LogLoss / Calibration / Confusion Matrix | `phase2_report.json` |
| 3 | `2_📈_ICIR_Analysis.py` | 📈 | 訊號穩定性：Rank IC、ICIR、時序衰減 | `phase3_analytics.json` |
| 4 | `3_💰_Backtest.py` | 💰 | 回測：累積報酬、DD、三情境、Bootstrap CI | `phase3_report.json` |
| 5 | `4_🔬_Feature_Analysis.py` | 🔬 | SHAP、Quintile、Feature Importance、九支柱分布 | `phase2_report.json` + `.joblib` |
| 6 | `5_🗃️_Data_Explorer.py` | 🗃️ | 資料品質：null 比例、分布、九支柱結構樹 | `feature_store_final.parquet` |
| 7 | `6_🛡️_Model_Governance.py` | 🛡️ | Model Card × 6、9/9 閘門、漂移監控 | `governance/*.json` |
| 8 | `7_📡_Signal_Monitor.py` | 📡 | 信號衰減：半衰期、再訓練建議 | `signal_decay.json` |
| 9 | `8_🎯_Extended_Analytics.py` | 🎯 | 成本敏感度、跨 horizon、支柱貢獻、個案 | `phase3_analytics.json` |
| 10 | `9_📝_Text_Analysis.py` | 📝 | 文本：coverage / 情緒 / 關鍵字 / 詞雲 | `text_features.parquet` |
| 11 | `A_🔭_Phase6_深度驗證.py` | 🔭 | **NEW**：LOPO / Threshold / 2454 | `lopo_*.json`、`threshold_*.json`、`single_stock_*.json` |

---

## 11. 圖表設計原則

> 所有圖表使用 **Plotly**，透過 `glint_plotly_layout()` 統一樣板（見 [utils.py](程式碼/儀表板/utils.py)）。

### 11.1 Plotly 通用設定

| 項目 | 值 |
|---|---|
| `paper_bgcolor` | `rgba(0,0,0,0)`（透明，讓 canvas 穿透） |
| `plot_bgcolor` | `rgba(255,255,255,0)`（透明） |
| Axis line color | `#cbd5e1` |
| Axis text color | `#475569` |
| Axis font | `Inter` |
| Tick font | `JetBrains Mono` |
| Gridline | `#e2e8f0`，`dash` dotted |
| Margin | `l=60, r=30, t=60, b=50` |

### 11.2 色板（Colorway）

```python
colorway = [
    "#2563eb",  # blue
    "#7c3aed",  # violet
    "#06b6d4",  # cyan
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#f43f5e",  # rose
    "#4f46e5",  # indigo
    "#ec4899",  # pink
]
```

### 11.3 三種 Colorscale

| 名稱 | 使用情境 | 色彩 |
|---|---|---|
| `GLINT_DIVERGING` | 雙向指標（正負 edge、IC） | rose → neutral → emerald |
| `GLINT_SEQUENTIAL_COOL` | 單向度量（AUC、Hit rate） | light blue → deep blue/violet |
| `GLINT_SEQUENTIAL_WARM` | 警示型單向（波動、風險） | yellow → amber → rose |

### 11.4 圖表命名規範

`glint_plotly_layout()` 接受：

| 參數 | 說明 |
|---|---|
| `title` | 粗體主標 |
| `subtitle` | 11px grey 副標（解釋軸或單位） |
| `height` | 預設 360px |
| `show_grid` | 是否顯示 gridline |
| `xlabel` / `ylabel` | 軸標 |

### 11.5 Heatmap 專用

- 使用 `glint_heatmap_colorscale(kind)`（kind ∈ `diverging` / `sequential_cool` / `sequential_warm`）
- Colorbar 透過 `glint_colorbar(title, fmt)` 建構
- 雙向指標必附 `zmid=threshold`（例如 AUC 的 `zmid=0.52`）
- 格子內文字：白色 / 深藍二值（依底色亮度）

---

## 12. 從 HTML Prototype 到 Streamlit 的映射

### 12.1 原型檔案兩種版本

| 檔案 | 用途 | 備註 |
|---|---|---|
| `台股多因子預測系統 - Dashboard.html` | 亮色版（散戶導向） | 展示 glint-light 主樣貌 |
| `台股多因子預測系統 - Terminal.html` | 深色版（研究員 terminal） | 展示資訊密集極致狀態 |
| `ui_kits/dashboard/index.html` | UI kit 主入口 | 各 component 集合頁 |
| `ui_kits/dashboard/terminal.html` | Terminal UI kit | 深色版 KPI + 表格 |

### 12.2 原型 → 實作的對應

| HTML class / pattern | Streamlit 實作位置 | 備註 |
|---|---|---|
| `body::before` tech-grid | `utils.py` → `inject_custom_css()` | Fixed 貼於每頁 |
| `.gl-hero` | 各 page 頂部 `st.markdown("""<div class="gl-hero">...""")` | 使用 `unsafe_allow_html=True` |
| `.gl-kpi` | `utils.py` → `render_kpi()` Python 函式 | 回傳 HTML 字串 |
| `.gl-panel` | `st.container(border=True)` + 自訂 CSS | 玻璃擬態 |
| `.gl-chip` / `.gl-pillar` | inline HTML or `st.markdown` | 亦可 `st.caption` 襯托 |
| `.gl-live` | Hero 區內 inline HTML | 脈動動畫 CSS 全域注入 |
| Sidebar dark bg | `section[data-testid="stSidebar"]` CSS override | 需用 attribute selector |
| Primary button | `st.button(type="primary")` + CSS override | `kind="primary"` 元素會繼承 |

### 12.3 實作原則

1. **HTML 是 visual contract，不是 code contract**。不要複製原型的 DOM 結構；只需保證視覺輸出像素對齊。
2. **所有色碼 / 尺寸 / 間距**：通過 `inject_custom_css()` 注入 `:root` 的 CSS 變數，頁面內只引用 `var(--gl-*)`。
3. **不要在個別 page 寫死 hex 色碼**。違反 single source of truth，未來調 token 會漏掉。

---

## 13. 無障礙與響應式

### 13.1 色彩對比（WCAG）

| 組合 | 對比比 | 結果 |
|---|---|---|
| `text` `#0f172a` on `bg` `#fafbfc` | 17.8:1 | AAA |
| `text-2` `#475569` on `surface` `#fff` | 7.6:1 | AAA |
| `text-3` `#94a3b8` on `surface` `#fff` | 3.3:1 | AA（僅用於 small / footnote） |
| `blue` `#2563eb` on `surface` `#fff` | 6.5:1 | AAA（大 CTA 安全） |
| `sidebar-fg` `#c8d6e5` on `sidebar-1` `#0f1419` | 11.5:1 | AAA（Sidebar dark 方向） |

### 13.2 鍵盤導航

- Tab 順序遵循視覺順序（top-down、left-to-right）
- 所有互動元件（selectbox / button / radio）皆可 Tab 聚焦
- Focus ring 使用 `--gl-shadow-glow`（藍色外光暈），visibility 高

### 13.3 響應式斷點

| 斷點 | 處理 |
|---|---|
| ≥ 1280 px | 所有 KPI 橫排（6 欄） |
| 960 – 1279 | KPI 3×2 |
| 640 – 959 | KPI 2×3，sidebar auto-collapse |
| < 640 | KPI 單欄，圖表垂直堆疊 |

Streamlit 的 `st.columns` 與 `st.container` 會自動處理；所有 Plotly 圖表使用 `use_container_width=True`，**絕不固定像素寬度**。

---

## 14. 反模式（Anti-Patterns）

### 14.1 色彩

- ❌ 純白 `#fff` 當 page background（刺眼）→ ✅ 用 `#fafbfc` off-white
- ❌ 純黑 `#000` 當文字 → ✅ 用 `#0f172a` near-black
- ❌ Blue 與 Violet 分開當兩色 → ✅ **永遠**作為漸層共同出現
- ❌ 在 body 裡用 `--gl-text-3` #94a3b8 → ✅ 只在 small/caption 使用

### 14.2 字體

- ❌ 數字用比例字 → ✅ 一律 `JetBrains Mono` + `tabular-nums`
- ❌ Hero 用純色 → ✅ 必用 `-webkit-background-clip: text` 漸層
- ❌ 中文套 Inter 不 fallback JhengHei → ✅ Fallback 鏈必含 `'Microsoft JhengHei'`, `'PingFang TC'`, `'Noto Sans TC'`

### 14.3 動效

- ❌ 加彈跳、旋轉、視差 → ✅ **只有 `gl-pulse` 一個 keyframe**
- ❌ 頁面載入 fade-in 疊 slide-in → ✅ 資料頁面即顯即得，不需儀式
- ❌ Hover 變色變太多（顏色跳來跳去）→ ✅ 只 border + shadow，最多 `translateY(-1px)`

### 14.4 Layout

- ❌ Plotly `width=800` 固定像素 → ✅ 必用 `use_container_width=True`
- ❌ 在頁面寫 `style="color: #2563eb"` 硬編碼 → ✅ 用 `var(--gl-blue)` 或 CSS class
- ❌ 每頁自己寫 Hero HTML → ✅ 用共用組件 / render function
- ❌ Emoji 當 bullet → ✅ 用 `ul > li::marker` 或標準列表

### 14.5 內容

- ❌ 「超強！業界最佳！」等行銷形容詞 → ✅ 用「嚴謹 / 可回看 / 可解釋 / 可治理」
- ❌ 第一/二人稱（我們 / 您 / 你）→ ✅ 第三人稱（本系統 / 本平台）
- ❌ 數字無 caveat → ✅ 每個 headline 必附 Bootstrap CI / DSR / sample reminder
- ❌ Emoji 連續（✨🚀）→ ✅ 單個 section-defining emoji

---

## 15. 檔案索引

### 15.1 Claude Design Bundle（本規範範圍）

```
claude-design-bundle/design-system/
├── README.md                              ← 「Coding agents: read this first」
├── chats/chat1.md                         ← 設計對話紀錄（意圖所在）
└── project/
    ├── README.md                          ← 反向工程主文件（177 行）
    ├── colors_and_type.css                ← CSS 變數權威（183 行）
    ├── uploads/
    │   └── 系統設計手冊.md                 ← 使用者上傳原始手冊（1,182 行）
    ├── preview/                            ← 17 支 HTML 示範卡
    ├── ui_kits/dashboard/                  ← Dashboard UI kit（index.html + terminal.html）
    ├── 台股多因子預測系統 - Dashboard.html ← 亮色版完整原型
    └── 台股多因子預測系統 - Terminal.html  ← 深色版完整原型
```

### 15.2 實作端檔案（被此規範實現）

| 實作文件 | 關係 |
|---|---|
| [utils.py](程式碼/儀表板/utils.py) → `inject_custom_css()` | **Design token 實作的 single source of truth** |
| [utils.py](程式碼/儀表板/utils.py) → `glint_plotly_layout()` | Plotly 統一樣板 |
| [utils.py](程式碼/儀表板/utils.py) → `GLINT_DIVERGING` / `GLINT_SEQUENTIAL_COOL` / `GLINT_SEQUENTIAL_WARM` | 三種 colorscale |
| [utils.py](程式碼/儀表板/utils.py) → `glint_heatmap_colorscale()` / `glint_colorbar()` | Heatmap helper |
| [utils.py](程式碼/儀表板/utils.py) → `render_kpi()` | `<GlKpi>` 實作 |
| [.streamlit/config.toml](程式碼/儀表板/.streamlit/config.toml) | Streamlit 主題設定（`primaryColor = #636EFA`） |
| [app.py](程式碼/儀表板/app.py) | `st.navigation` router + 頂部導覽 |

### 15.3 相關設計文件

| 文件 | 位置 | 用途 |
|---|---|---|
| 網站設計概念與架構 | [網站設計概念與架構.md](網站設計概念與架構.md) | 本專案端設計文件（此文件的姊妹篇） |
| 系統設計手冊 | `claude-design-bundle/design-system/project/uploads/系統設計手冊.md` | 原始完整手冊（1,182 行） |
| 儀表板修訂規格書 | `進度報告/儀表板修訂規格書.md` | 早期 UI 規格 |

### 15.4 外部參考資源

**設計靈感**
- [glint.trade / terminal](https://glint.trade/terminal)
- Bloomberg Terminal Design Language
- [Stripe Dashboard](https://stripe.com/)
- [Linear Method](https://linear.app/method)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Refactoring UI](https://www.refactoringui.com/)

**字型**
- Inter — <https://rsms.me/inter/>
- JetBrains Mono — <https://www.jetbrains.com/lp/mono/>
- Noto Sans TC — Google Fonts

**技術文件**
- [Streamlit `st.navigation`](https://docs.streamlit.io/develop/api-reference/navigation)
- [Plotly Python](https://plotly.com/python/)

---

## 版本歷史

| 版本 | 日期 | 修訂 |
|---|---|---|
| 1.0 | 2026-04-20 | 初版 — 整合 Claude Design bundle 之完整 Token / 理念 / 元件 / 頁面 / 實作對應 |

---

> **聯絡**：陳延逸（andychen050229@gmail.com）
> **授權**：MIT License — 僅供學術研究用途
> **專案網址**：[taiwan-stock-multifacto-dashboardapp.streamlit.app](https://taiwan-stock-multifacto-dashboardapp-wdjhcj.streamlit.app/)
> **GitHub**：[andychen050229-cell/taiwan-stock-multifactor](https://github.com/andychen050229-cell/taiwan-stock-multifactor)
