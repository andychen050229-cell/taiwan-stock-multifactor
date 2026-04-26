# Dashboard UI Kit — 量化研究終端

Interactive recreation of the Streamlit dashboard at `taiwan-stock-multifacto-dashboardapp-wdjhcj.streamlit.app`, remixed into a tech-dense, Bloomberg-terminal-inspired surface while staying 100% faithful to the glint-light design tokens.

## What's in this file

- **Dark fixed sidebar** with grouped nav, brand block, live gates indicator, keyboard-shortcut chips — mirrors the Streamlit `st.navigation` layout.
- **Sticky top-bar** with breadcrumb, model chips (`xgboost_D20`, `embargo=20`, `DSR 12.12 → PASS`), live clock.
- **Hero section** with gradient-clipped title + radial blur orb + live pulse chip.
- **6-tile KPI strip** (SAMPLES · FEATURES · PILLARS · HORIZONS · QUALITY · TOP PILLAR) with 3px colored top-border and mono tabular numerics.
- **Dual-path entrypoints** — investor (amber wash) vs quant (sky wash).
- **6-up phase timeline** — Phase 1–6, emerald left-bars.
- **Three methodology panels** — feature · validation · model.
- **Model view** — horizon segmented control (D+1 / D+5 / D+20), AUC gauge, 3-cost cumulative-returns chart, 9-pillar LOPO bars.
- **Investor view** — 8-row stock table, clickable rows open a slide-in drawer with per-stock observation + risk summary, live cost calculator, signal-distribution histogram.
- **ICIR view** — 24-month Rank IC time series, monthly-returns histogram, 4-fold stability bars.
- **Feature view** — 9-pillar distribution, 3-stage filter funnel, SHAP top-20 with pillar-colored bars.
- **Text view** — Phase 5B word cloud (colored by sentiment), platform share, coverage summary.
- **Keyboard shortcuts** — `G` home, `I` investor, `Esc` closes drawer. `localStorage` persists the active view.

## Components

- `Sidebar` — dark gradient + pulse live chip + nav links w/ active left-border
- `Topbar` — breadcrumb + chips + clock
- `Hero` — eyebrow + gradient title + meta chips
- `KPI` — labeled tile; variants `acc-blue/violet/cyan/emerald/amber/rose`
- `Path` — entrypoint card (variants `inv`, `qnt`)
- `PhaseChip` — emerald left-bar, `cur` variant uses primary gradient
- `Card` — generic panel; span classes `span-3 / 4 / 6 / 8 / 12` for the 12-col grid
- `PillarBar` — colored pill label + progress bar + numeric + delta
- `Gauge` — SVG half-ring gauge w/ tech gradient
- `StockTable` — sortable-looking table; rows open `Drawer`
- `Drawer` — fixed right sheet w/ 2×2 KPI + observation + risk
- `Box` — left-accent info / ok / warn / danger message
- `Seg` — segmented control for horizon switching
- `Chip` — default / pri / vio / ok / warn

## Architecture

Single vanilla-JS file with string-template views. No build step. Tokens aligned 1:1 with `colors_and_type.css` and `程式碼/儀表板/utils.py` → `inject_custom_css`. Every view is reached via the same `nav(v)` function which swaps `#app` innerHTML with a fade-in.

## Fidelity notes

- Copy is lifted verbatim from the source dashboard where possible (hero subtitle, disclaimer, KPI numbers from `phase2_report` and `recommendations.json`).
- Stock list uses real Taiwan equities (2330 台積電, 2454 聯發科, 2317 鴻海, etc.) with directionally-plausible synthetic return/margin values anchored to samples in `recommendations.json`.
- SHAP list uses real feature names from the source pillar taxonomy.
- Charts are hand-rolled SVG rather than Plotly — this is the **only** deliberate departure, chosen so the file stays standalone with no external JS.
- LOPO Δ-AUC bars match the Phase 6 top-pillar ranking in the source (`risk` → `fund` → `chip`).
