/* global React */

// ============================================================================
// PillarBars — horizontal bars with colored pill labels
// ============================================================================
function PillarBars({ data }) {
  const max = Math.max(...data.map(d => d.value));
  return (
    <div className="pillar-bars">
      {data.map((d, i) => (
        <div key={i} className="pb-row">
          <span className="pb-pill" data-p={d.pillar}>{d.pillar}</span>
          <div className="pb-bar-wrap">
            <div className="pb-bar" style={{ width: `${(d.value / max) * 100}%`, background: d.color }}></div>
          </div>
          <span className="pb-num">{d.value.toFixed(4)}</span>
          <span className={`pb-delta ${d.delta < 0 ? 'down' : ''}`}>{d.delta >= 0 ? '+' : ''}{d.delta.toFixed(3)}</span>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// LineChart — SVG, minimal
// ============================================================================
function LineChart({ series, height = 160, colors = ['#2563eb', '#7c3aed'] }) {
  const w = 560, pad = 28;
  const allY = series.flatMap(s => s.points.map(p => p[1]));
  const ymin = Math.min(...allY), ymax = Math.max(...allY);
  const xmax = series[0].points.length - 1;
  const sx = i => pad + (i / xmax) * (w - pad * 2);
  const sy = y => height - pad - ((y - ymin) / (ymax - ymin || 1)) * (height - pad * 2);

  return (
    <svg className="chart-svg" viewBox={`0 0 ${w} ${height}`}>
      <g className="cg-grid">
        {[0, 0.25, 0.5, 0.75, 1].map(f => {
          const y = pad + f * (height - pad * 2);
          return <line key={f} x1={pad} x2={w - pad} y1={y} y2={y} />;
        })}
      </g>
      {series.map((s, si) => {
        const d = s.points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${sx(i)} ${sy(p[1])}`).join(' ');
        return <path key={si} className="cg-line" d={d} stroke={colors[si % colors.length]} />;
      })}
      <g className="cg-axis">
        <text x={pad} y={height - 8}>{series[0].points[0][0]}</text>
        <text x={w - pad - 40} y={height - 8}>{series[0].points[xmax][0]}</text>
        <text x={4} y={pad + 4}>{ymax.toFixed(2)}</text>
        <text x={4} y={height - pad + 4}>{ymin.toFixed(2)}</text>
      </g>
      {series.map((s, si) => (
        <g key={si} transform={`translate(${pad + si * 120}, 14)`}>
          <rect width="10" height="2" y="4" fill={colors[si]} />
          <text x="14" y="8" fill="#475569" fontSize="10" fontFamily="JetBrains Mono">{s.label}</text>
        </g>
      ))}
    </svg>
  );
}

// ============================================================================
// PhaseTimeline — 6-up
// ============================================================================
function PhaseTimeline({ phases, current }) {
  return (
    <div className="phase-row">
      {phases.map((p, i) => (
        <div key={i} className={`ph ${p.key === current ? 'cur' : ''}`}>
          <div className="ph-k">Phase {i}</div>
          <div className="ph-ti">{p.title}</div>
          <div className="ph-sb">{p.sub}</div>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// InsightBox
// ============================================================================
function InsightBox({ tone = 'info', children }) {
  return <div className={`box ${tone}`}>{children}</div>;
}

// ============================================================================
// StockTable
// ============================================================================
function StockTable({ rows, onRowClick }) {
  return (
    <table className="st-tbl">
      <thead>
        <tr><th>#</th><th>Ticker</th><th>Name</th><th>Industry</th><th style={{textAlign:'right'}}>Score</th><th style={{textAlign:'right'}}>Fwd D+20</th></tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.ticker} onClick={() => onRowClick?.(r)}>
            <td>{String(i+1).padStart(2,'0')}</td>
            <td className="ticker">{r.ticker}</td>
            <td className="name-zh">{r.name}</td>
            <td><span className="ind-chip">{r.industry}</span></td>
            <td style={{textAlign:'right'}}>{r.score.toFixed(3)}</td>
            <td style={{textAlign:'right'}} className={r.ret >= 0 ? 'ret-up' : 'ret-dn'}>{r.ret >= 0 ? '+' : ''}{r.ret.toFixed(2)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ============================================================================
// Gauge — semicircle for AUC / DSR
// ============================================================================
function Gauge({ value, max = 1, label, color = '#2563eb' }) {
  const pct = Math.min(1, value / max);
  const r = 52, cx = 70, cy = 70;
  const start = Math.PI, end = 0;
  const angle = start + (end - start) * pct;
  const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start);
  const x2 = cx + r * Math.cos(angle), y2 = cy + r * Math.sin(angle);
  const large = pct > 0.5 ? 1 : 0;
  return (
    <div className="gauge">
      <div className="gauge-ring">
        <svg width="140" height="90" viewBox="0 0 140 90">
          <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke="#f1f5f9" strokeWidth="10" strokeLinecap="round" />
          <path d={`M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" />
        </svg>
      </div>
      <div className="gauge-val mono">{value.toFixed(value < 1 ? 3 : 2)}</div>
      <div className="gauge-lbl">{label}</div>
    </div>
  );
}

// ============================================================================
// Card — generic surface with header
// ============================================================================
function Card({ title, meta, span = 6, children, actions }) {
  return (
    <div className={`card span-${span}`}>
      <div className="card-hd">
        <div className="ti">{title}</div>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          {actions}
          {meta && <div className="mt">{meta}</div>}
        </div>
      </div>
      {children}
    </div>
  );
}

// ============================================================================
// Segmented
// ============================================================================
function Segmented({ options, value, onChange }) {
  return (
    <div className="seg">
      {options.map(o => (
        <button key={o.value} className={value === o.value ? 'on' : ''} onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

window.DashboardKit = Object.assign(window.DashboardKit || {}, {
  PillarBars, LineChart, PhaseTimeline, InsightBox, StockTable, Gauge, Card, Segmented
});
