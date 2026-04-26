/* global React */
const { useState, useEffect } = React;

// ============================================================================
// Sidebar — dark gradient, grouped links, live status, footer meta
// ============================================================================
function Sidebar({ active, onNav }) {
  const groups = [
    { title: "Overview", items: [["home", "🏠", "首頁", "G"]] },
    { title: "📖 投資解讀", items: [["invest", "🌱", "投資解讀面板", "I"]] },
    { title: "🔬 量化研究工作台", items: [
      ["model", "📊", "模型績效", ""],
      ["icir", "📈", "ICIR 信號穩定性", ""],
      ["bt", "💰", "策略回測", ""],
      ["feat", "🔬", "特徵工程分析", ""],
    ]},
    { title: "🛡️ 治理 · 監控", items: [
      ["gov", "🛡️", "模型治理", ""],
      ["sig", "📡", "信號監控", ""],
      ["p6", "🔭", "Phase 6 深度驗證", ""],
    ]},
  ];
  return (
    <aside className="sb">
      <div className="sb-brand">
        <div className="sb-logo">台</div>
        <div className="sb-title">台股多因子預測系統</div>
        <div className="sb-version mono">v11.5.17 · 2026-04-24</div>
      </div>
      {groups.map(g => (
        <div key={g.title}>
          <div className="sb-group">{g.title}</div>
          {g.items.map(([key, icon, label, k]) => (
            <a key={key}
               className={`sb-link ${active === key ? 'active' : ''}`}
               onClick={() => onNav(key)}>
              <span className="glyph">{icon}</span>{label}
              {k && <span className="k">{k}</span>}
            </a>
          ))}
        </div>
      ))}
      <div className="sb-foot">
        <div className="row"><span>STATUS</span><span className="live">live</span></div>
        <div className="row"><span>GATES</span><b>9 / 9 PASS</b></div>
        <div className="row"><span>ENGINE</span><b>LGB + XGB</b></div>
        <div className="row"><span>CV</span><b>Purged WF · 4-fold</b></div>
        <div className="row"><span>EMBARGO</span><b>20d</b></div>
      </div>
    </aside>
  );
}

// ============================================================================
// Topbar
// ============================================================================
function Topbar({ crumb, chips = [] }) {
  const [now, setNow] = useState('');
  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setNow(d.toLocaleString('zh-TW', { hour12: false }).replace(/\//g, '-'));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="topbar">
      <div className="crumbs">
        <span>量化研究終端</span>
        <span className="slash">/</span>
        <span className="cur">{crumb}</span>
      </div>
      <div className="topbar-r">
        {chips.map((c, i) => <span key={i} className={`chip ${c.tone || ''}`}>{c.label}</span>)}
        <span className="sep">|</span>
        <span className="mono">{now}</span>
      </div>
    </div>
  );
}

// ============================================================================
// Hero
// ============================================================================
function Hero({ eyebrow, title, sub, meta = [] }) {
  return (
    <div className="hero">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h1 className="hero-title">{title}</h1>
      <p className="hero-sub">{sub}</p>
      {meta.length > 0 && (
        <div className="hero-meta">
          {meta.map((m, i) => <span key={i} className={`chip ${m.tone || ''}`}>{m.label}</span>)}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// KpiCard
// ============================================================================
function KpiCard({ accent = 'blue', label, value, sub, delta }) {
  return (
    <div className={`kpi acc-${accent}`}>
      <div className="kpi-lbl">{label}</div>
      <div className="kpi-val mono">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
      {delta && <div className={`kpi-delta ${delta.dir}`}>{delta.dir === 'up' ? '↑' : '↓'} {delta.text}</div>}
    </div>
  );
}

window.DashboardKit = { Sidebar, Topbar, Hero, KpiCard };
