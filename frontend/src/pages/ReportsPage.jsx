import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { BarChart3, AlertTriangle, Users, Award, TrendingUp, RefreshCw, Download, FileSpreadsheet, FileText } from 'lucide-react';

export function ReportsPage() {
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState('');
  const [comparison, setComparison] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [underutilization, setUnderutilization] = useState(null);
  const [staffing, setStaffing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [chartUrl, setChartUrl] = useState('');
  const [exportingFormat, setExportingFormat] = useState('');
  const [exportError, setExportError] = useState('');

  useEffect(() => () => {
    if (chartUrl) URL.revokeObjectURL(chartUrl);
  }, [chartUrl]);

  async function loadData(evId) {
    setLoading(true);
    try {
      const evRes = await api.getEvents();
      setEvents(evRes.data || []);

      const activeId = evId || evRes.data?.find(e => e.name === 'Kala Fest')?.id || evRes.data?.[0]?.id;
      if (activeId) {
        setSelectedEventId(activeId);
        const [compRes, recRes, underRes, staffingRes, chartBlob] = await Promise.all([
          api.getAlgorithmComparison(activeId),
          api.getRecommendations(activeId),
          api.getUnderutilizationReport(activeId),
          api.getStaffingReport(activeId),
          api.getReportChart(activeId).catch(() => null)
        ]);
        setComparison(compRes.data);
        setRecommendations(recRes.data || []);
        setUnderutilization(underRes.data);
        setStaffing(staffingRes.data || null);
        setChartUrl(chartBlob ? URL.createObjectURL(chartBlob) : '');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function handleEventChange(e) {
    const newId = e.target.value;
    setSelectedEventId(newId);
    loadData(newId);
  }

  async function refreshChart() {
    try {
      const blob = await api.getReportChart(selectedEventId);
      setChartUrl(URL.createObjectURL(blob));
    } catch (err) {
      setChartUrl('');
    }
  }

  async function downloadRoster(format) {
    setExportingFormat(format);
    setExportError('');
    try {
      const { blob, filename } = await api.downloadRoster(selectedEventId, format);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setExportError(err.message || 'Roster download failed.');
    } finally {
      setExportingFormat('');
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="h1">Staffing Reports & Optimization Insights</h1>
          <p className="text-muted" style={{ marginTop: '4px' }}>
            Algorithm comparison, shortage analysis, and evidence-grounded recommendations
          </p>
        </div>

        {events.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', fontWeight: 500 }}>Select Event:</span>
            <select
              className="form-select"
              style={{ width: '220px' }}
              value={selectedEventId}
              onChange={handleEventChange}
            >
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.name} ({ev.status})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {selectedEventId && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header" style={{ alignItems: 'center' }}>
            <div>
              <h3 className="h3">Department Head Rosters</h3>
              <p className="text-muted text-sm" style={{ marginTop: '4px' }}>
                {staffing?.can_export_roster
                  ? `Published allocation v${staffing.version_number} · Excel includes a summary and a sheet for each department; CSV includes all assigned volunteers.`
                  : 'Downloads become available after an allocation is published.'}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => downloadRoster('csv')}
                disabled={!staffing?.can_export_roster || Boolean(exportingFormat)}
              >
                {exportingFormat === 'csv' ? <Download size={14} /> : <FileText size={14} />}
                <span>Download CSV</span>
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => downloadRoster('xlsx')}
                disabled={!staffing?.can_export_roster || Boolean(exportingFormat)}
              >
                {exportingFormat === 'xlsx' ? <Download size={14} /> : <FileSpreadsheet size={14} />}
                <span>Download Excel</span>
              </button>
            </div>
          </div>
          {exportError && <p role="alert" style={{ color: 'var(--color-danger)', fontSize: '13px' }}>{exportError}</p>}
        </div>
      )}

      {/* 1. Matplotlib Department Staffing Chart */}
      {selectedEventId && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <div>
              <h3 className="h3">Department Staffing: Required vs. Allocated</h3>
              <p className="text-muted text-sm">
                Restrained comparative visualization rendered by backend Matplotlib service
              </p>
            </div>
            <button
              onClick={refreshChart}
              className="btn btn-secondary btn-sm"
            >
              <RefreshCw size={13} />
              <span>Refresh Chart</span>
            </button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0' }}>
            {chartUrl ? (
              <img
                key={chartUrl}
                src={chartUrl}
                alt="Department staffing chart showing required and allocated positions"
                style={{ maxWidth: '100%', height: 'auto', borderRadius: 'var(--radius-md)' }}
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            ) : (
              <p className="text-muted text-sm">Chart is unavailable for this event.</p>
            )}
          </div>
        </div>
      )}

      {/* 2. Algorithm Comparison Section */}
      {comparison && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <div>
              <h3 className="h3">Greedy Baseline vs. PuLP ILP Optimizer Comparison</h3>
              <p className="text-muted text-sm">
                Both algorithms evaluated strictly on the exact same snapshot and hard eligibility rules
              </p>
            </div>
          </div>

          {/* Metric Comparison Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px', marginBottom: '20px' }}>
            <div style={{ padding: '16px', backgroundColor: 'var(--color-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>Greedy Priority Baseline</div>
              <div style={{ fontSize: '20px', fontWeight: 600 }}>{comparison.greedy.allocated} / {comparison.total_required} Filled</div>
              <div style={{ fontSize: '12px', color: 'var(--color-muted)', marginTop: '4px' }}>
                Coverage: {comparison.greedy.coverage_pct}% · Runtime: {comparison.greedy.runtime_seconds}s
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-muted)' }}>
                Top-2 Preferences Met: {comparison.greedy.preference_top2_satisfied} volunteers
              </div>
            </div>

            <div style={{ padding: '16px', backgroundColor: 'var(--color-primary-soft)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-primary)' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-primary-hover)', marginBottom: '6px' }}>PuLP ILP Optimizer</div>
              <div style={{ fontSize: '20px', fontWeight: 600 }}>{comparison.ilp.allocated} / {comparison.total_required} Filled</div>
              <div style={{ fontSize: '12px', color: 'var(--color-muted)', marginTop: '4px' }}>
                Coverage: {comparison.ilp.coverage_pct}% · Runtime: {comparison.ilp.runtime_seconds}s
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-muted)' }}>
                Top-2 Preferences Met: {comparison.ilp.preference_top2_satisfied} volunteers · Objective: {comparison.ilp.objective_value}
              </div>
            </div>
          </div>

          {/* Evaluation Notes */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', marginBottom: '20px' }}>
            <div style={{ fontWeight: 600, fontSize: '13px', marginBottom: '6px' }}>Analytical Assessment:</div>
            <ul style={{ paddingLeft: '20px', fontSize: '13px', color: 'var(--color-text)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {comparison.evaluation_notes?.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </div>

          {/* Department Comparison Table */}
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Demand</th>
                  <th>Greedy Allocated</th>
                  <th>ILP Allocated</th>
                  <th>Optimization Diff</th>
                </tr>
              </thead>
              <tbody>
                {comparison.department_comparison?.map((dc, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{dc.department}</td>
                    <td>{dc.required}</td>
                    <td>{dc.greedy_allocated} ({dc.greedy_coverage_pct}%)</td>
                    <td style={{ fontWeight: 600, color: 'var(--color-primary-hover)' }}>{dc.ilp_allocated} ({dc.ilp_coverage_pct}%)</td>
                    <td>
                      {dc.diff_allocated > 0 ? (
                        <span style={{ color: 'var(--color-success)', fontWeight: 600 }}>+{dc.diff_allocated}</span>
                      ) : dc.diff_allocated < 0 ? (
                        <span style={{ color: 'var(--color-danger)', fontWeight: 600 }}>{dc.diff_allocated}</span>
                      ) : (
                        <span className="text-muted">0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. Evidence-Grounded Recommendations */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <h3 className="h3">Actionable Shortage & Utilization Recommendations</h3>
        </div>
        {recommendations.length === 0 ? (
          <p className="text-muted text-sm">No critical shortages or bottleneck recommendations at this time.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {recommendations.map((rec, i) => (
              <div key={i} style={{ padding: '14px 16px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: '14px' }}>{rec.title}</span>
                  <Badge type={rec.priority}>{rec.priority}</Badge>
                </div>
                <p style={{ fontSize: '13px', color: 'var(--color-text)', marginTop: '6px' }}>{rec.description}</p>
                <div style={{ fontSize: '12px', color: 'var(--color-muted)', marginTop: '6px', fontStyle: 'italic' }}>
                  Evidence: {rec.evidence}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 4. Underutilization: Unassigned Active Volunteers */}
      {underutilization && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="h3">Unassigned Active Volunteers ({underutilization.total_unassigned})</h3>
              <p className="text-muted text-sm">
                Available committee volunteers currently unassigned who can be manually reassigned to vacant positions
              </p>
            </div>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Volunteer</th>
                  <th>Student ID</th>
                  <th>Verified Skills</th>
                  <th>Availability</th>
                </tr>
              </thead>
              <tbody>
                {underutilization.unassigned_volunteers?.slice(0, 15).map((v) => (
                  <tr key={v.id}>
                    <td style={{ fontWeight: 500 }}>{v.full_name}</td>
                    <td><code>{v.student_id}</code></td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {v.skills?.map((s, i) => (
                          <span key={i} style={{ backgroundColor: '#FFFFFF', border: '1px solid var(--color-border)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' }}>
                            {s}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="text-muted text-sm">{v.max_hours || 8.0} hrs capacity</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
