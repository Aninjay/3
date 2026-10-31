import React from 'react';

export function MetricCard({ label, value, sub, icon: Icon, color }) {
  return (
    <div className="metric-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div className="metric-label">{label}</div>
        {Icon && <Icon size={18} color={color || 'var(--color-muted)'} />}
      </div>
      <div className="metric-value" style={color ? { color } : {}}>
        {value}
      </div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}
