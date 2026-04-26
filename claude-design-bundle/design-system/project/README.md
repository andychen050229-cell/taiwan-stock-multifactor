# 台股多因子預測系統 Design System

> Taiwan Stock Multi-Factor Prediction System — a data-dense, research-grade Streamlit dashboard for historical quantitative analysis (2023/03–2025/03).
>
> This design system captures the visual language, content voice, and UI components of the production Streamlit app so that any future surface (docs, decks, marketing, prototypes) stays on brand.

---

## Product context

The parent product is a **course research platform** that packages a full end-to-end Taiwan-equity multi-factor research pipeline behind a 10-page Streamlit dashboard. The system is explicitly **not** a real-time trading product — it is a *historical snapshot interactive research terminal*.

The dashboard is split into two deliberate reading modes that share one visual language:

| Mode | Audience | Tone |
|---|---|---|
| 🌱 **投資解讀面板** (Investor Interpretation) | Investors, business readers, marketing, general audience | Plainer Mandarin, warm left-accent cards, disclaimers foregrounded |
| ⚙️ **量化研究工作台** (Quant Research Bench) | Professors, judges, quant researchers | Dense KPIs, charts, tables, monospace numerics, Bloomberg-terminal feel |

Internally the team calls the shared look **"glint-light"** — inspired by the Bloomberg Terminal / glint.trade / 財報狗 but rendered in a light theme on an off-white tech grid.

### Signature moves
- **Hero gradient title** — tri-stop blue→violet `-webkit-background-clip: text`
- **Tech grid canvas** — 40×40px `rgba(37,99,235,0.025)` lines behind every page
- **Left-accent insight boxes** — 4px left border + soft gradient fill; colored by intent (info/warn/ok/danger)
- **KPI tiles** — off-white card, 3px colored top border, tabular-numeric JetBrains Mono value, uppercase 0.76rem label
- **Pillar badges** — 9 colour-coded factor family pills (`trend`, `fund`, `val`, `event`, `risk`, `chip`, `ind`, `txt`, `sent`)
- **Live chip** — pulsing emerald dot for status indicators

---

## Sources

This system was reverse-engineered from a single attached codebase:

- **Codebase path:** `大數據與商業分析專案/` (mounted via File System Access API, read-only)
- **Canonical dashboard entry:** `程式碼/儀表板/app.py` (uses `st.navigation`)
- **Design tokens source of truth:** `程式碼/儀表板/utils.py` → `inject_custom_css()` (glint-light theme)
- **Streamlit theme:** `程式碼/儀表板/.streamlit/config.toml` (primary `#636EFA`)
- **Content samples:** `README.md`, `SCOPE.md`, `pages/home.py`, `pages/0_🌱_投資解讀面板.py`, `data/recommendations.json`
- **Figures:** `outputs/figures/*.png` (55 charts from Phase 2/3/5B/6)
- **Slides:** `進度報告/台股多因子預測系統_簡報_v4.pptx`

No Figma file was provided. All colours, type sizes, spacing, radii, shadows, and component shapes were lifted directly from the dashboard CSS.

---

## CONTENT FUNDAMENTALS

### Languages & code-switching
- **Traditional Chinese (zh-TW) is primary**; English is freely code-switched in for technical terms (`AUC`, `ICIR`, `Purged Walk-Forward CV`, `Feature Store`, `Bootstrap`).
- **Pipe-separated bilingual labels** are common in headings: *"模型指標分析 | Model Metrics"*, *"選擇 Horizon | Select Horizon"*.
- Taiwanese financial jargon is preserved literally (e.g. *出手率*, *籌碼*, *支柱*, *回測*).

### Voice & tone
- **Confident but hedged.** The product is a *research* platform, not advice. Every headline metric is followed by a caveat (Bootstrap CI, DSR result, sample-size reminder).
- **Researcher-to-peer, not vendor-to-user.** Copy assumes the reader is literate in stats. For the investor panel, the writer "translates down" with analogies.
- **"本平台 / 本系統 / 本專案"** third-person self-reference. Almost no *you* (*您/你*), almost no *we*.
- **No marketing adjectives.** Instead: *嚴謹 · 可回看 · 可解釋 · 可治理*.

### Casing
- Chinese: natural, no stylization.
- English **ALL-CAPS + letter-spacing 0.06–0.10em** is reserved for KPI labels (`SAMPLES`, `FEATURES`, `QUALITY`) and eyebrows (`TAIWAN STOCK · MULTI-FACTOR PREDICTION`).
- Monospace chips use lowercase: `xgboost_D20`, `initial_train=252`, `embargo=20`.

### Emoji usage
- **Yes, but structural, not decorative.** Every page tab has a single section-defining emoji (🌱 📊 📈 💰 🔬 🗃️ 🛡️ 📡 🎯 📝 🔭). Boxes use 📋 ⚠️ 📅 🎯 ✅ ❌ as status glyphs. Never two in a row, never as bullets, never in body copy.
- The nine factor pillars use **colour badges**, not emoji.

### Numerics
- Percentages: 2 decimals with a sign when it's a performance delta (`+13.83%`, `−8.70%`). `%` uses ASCII, not `％`.
- Basis points: `+1.5bps`, `12.12 → PASS`.
- Ratios: 3–4 decimals (`AUC 0.6455`, `IC 0.015`).
- Commas every 3 digits (`948,976 rows`, `1,930 家上市櫃`).
- All monetary and statistical values **must** use `font-family: JetBrains Mono` with `font-variant-numeric: tabular-nums`.

### Example copy (lifted verbatim)
> 以 **2023/03 – 2025/03** 台股歷史資料為基礎，整合 **9 支柱 1,623 候選因子**、**LightGBM + XGBoost 雙引擎**、**Purged Walk-Forward CV** 與 **LOPO 深度驗證**，提供可回看、可解釋、可治理的研究展示平台。

> ⚠️ **免責聲明**：本系統為課程專案成果，不構成任何投資建議。所有顯示結果均為歷史回測數據。

> 近期回撤僅 1%，價格走勢相對穩定；目前處於高波動環境，短期價格變動可能較劇烈。

---

## VISUAL FOUNDATIONS

### Colour
- **Canvas:** `#fafbfc` off-white with two radial tints (blue top-left, violet top-right) and a subtle 40px tech grid. Never pure `#fff` as page bg.
- **Primary accent:** electric blue `#2563eb` → violet `#7c3aed` — always used as a **gradient**, never as two separate tones.
- **Signal palette:** emerald `#10b981` (pass/up), amber `#f59e0b` (warn/watch), rose `#f43f5e` (fail/down), cyan `#06b6d4` (data), indigo `#4f46e5` (accent).
- **Nine pillar tints** are muted pastel backgrounds with darker text.
- Dark only appears in the **sidebar** (`linear-gradient(180deg, #0f1419 0%, #1a2332 100%)`) — Bloomberg-terminal reference.

### Type
- **Sans:** Inter (400/500/600/700/800) with `-apple-system, 'Microsoft JhengHei', 'PingFang TC'` CJK fallbacks.
- **Mono:** JetBrains Mono (400/500/600/700) — mandatory for all numbers, tickers, code, chips.
- Hero titles use `-webkit-background-clip: text` with a tri-stop slate→blue→violet gradient and `letter-spacing: -0.03em`.
- Section `h2` gets a 4px left accent bar rendered via `::before` gradient.
- KPI labels: `0.72–0.76rem, font-weight: 600, text-transform: uppercase, letter-spacing: 0.06–0.08em, color: var(--gl-text-3)`.

### Spacing & layout
- Block container padding-top `1.5rem`. Cards: 18–24px inner padding.
- Fixed attachment background so the tech grid doesn't scroll.
- Content is mostly **full-width multi-column** (3-up, 6-up KPI grids). The hero is always full-bleed.

### Radii
- **Pill / chip:** `999px` · **Box / card:** `10–14px` · **Hero:** `18px` · **Button:** `10px`
- Left-accent info boxes use asymmetric `0 10px 10px 0` so the 4px border-left reads as a flag.

### Shadows
- `--gl-shadow-sm` — default card rest state.
- `--gl-shadow-md` — hero, elevated panels.
- `--gl-shadow-glow: 0 0 0 1px rgba(37,99,235,.08), 0 8px 30px rgba(37,99,235,.12)` — hover on any interactive card, paired with `translateY(-1px)`.

### Backgrounds & imagery
- **Tech grid** (40px, `rgba(37,99,235,0.025)`) is the signature texture — fixed-attach, behind every page.
- **Two radial blue/violet washes** at top-left and top-right corners of the canvas.
- Charts are **Plotly** with white paper bg, light-grey axis (`#cbd5e1`), Inter labels, monospace tick values.
- **No photography, no illustrations, no hand-drawn art.** Charts *are* the imagery.

### Animation
- Transitions default to `.25s ease` on hover state changes.
- One keyframe: `gl-pulse` — 2s cubic-bezier infinite ring on live-status dots. Do not add more.
- No page-load animations, no bouncing, no parallax.

### Hover / press
- **Hover:** border `#e2e8f0` → `rgba(37,99,235,0.35)`; shadow → `--gl-shadow-glow`; card lifts 1–2px; optional top `::before` gradient bar fades in from opacity 0→1.
- **Press:** Streamlit defaults apply. Primary buttons use `box-shadow: 0 4px 14px rgba(37,99,235,0.25)` at rest, `0 6px 20px` on hover.

### Borders
- `--gl-border: #e2e8f0` everywhere. `--gl-border-str: #cbd5e1` for heavier dividers.
- Accent bars are 3px (top of KPI cards) or 4px (left of insight boxes and h2).

### Transparency & blur
- `rgba(255,255,255,0.72)` overlay token for glass feel.
- `filter: blur(40px)` on the hero corner glow disc.
- No backdrop-filter elsewhere.

### Cards (canonical spec)
> `background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 18px 22px; box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 1px 3px rgba(15,23,42,.06);`
> On hover: border `rgba(37,99,235,.35)`, shadow `--gl-shadow-glow`, `translateY(-1px)`.

### Layout rules
- Sidebar is fixed dark `#0f1419→#1a2332` with uppercase group labels.
- Main column responsive via Streamlit's `st.columns`.
- All charts go `use_container_width=True`; never fixed pixel widths.

---

## ICONOGRAPHY

This product **does not use an icon library.** There is no Lucide, Heroicons, Font Awesome, or custom SVG sprite in the codebase.

**What is actually used:**
- **Emoji as section markers** — one per page, placed in the filename/route (`0_🌱_投資解讀面板.py`) so they surface in `st.Page(icon=...)`. Specific emoji are locked by role:
  - 🏠 Home · 🌱 Beginner/Investor · 📊 Model Metrics · 📈 ICIR · 💰 Backtest · 🔬 Feature · 🗃️ Data · 🛡️ Governance · 📡 Signal · 🎯 Extended · 📝 Text · 🔭 Phase 6
- **Status glyphs** inside boxes: ✅ ❌ ⚠️ 📋 📅 🕐 🎯 ⚡ 🔒 🔧 📐.
- **Pillar badges** are text + colour, not icons.

**Derived house rule for this design system:** when an icon is needed outside the dashboard context (e.g. a docs page or marketing slide), use **Lucide** (`https://unpkg.com/lucide@latest`) at stroke-width 1.5, colour = `currentColor`. This is a **substitution**, not present in the source codebase — flagged here so the user can swap it if they have an alternative in mind.

**No logos or wordmarks were provided.** The header uses the page title "台股多因子預測系統" as the wordmark. Flag: if a logo is desired, the user should supply one.

---

## Index

```
README.md                  ← you are here
SKILL.md                   ← agent-skill entrypoint
colors_and_type.css        ← CSS variables + semantic styles
preview/                   ← Design-System-tab cards
ui_kits/dashboard/         ← Streamlit dashboard recreation (JSX)
assets/                    ← logos / images (empty — none in source)
```
