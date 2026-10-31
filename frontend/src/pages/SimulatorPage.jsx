import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Sliders, Play, AlertCircle, Users, CheckCircle2, RefreshCw } from 'lucide-react';

export function SimulatorPage() {
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState('');
  const [absenteeismRate, setAbsenteeismRate] = useState(15);
  const [simCandidateName, setSimCandidateName] = useState('');
  const [simCandidateSkill, setSimCandidateSkill] = useState('Stage & Backstage Management');
  const [simulatedCohort, setSimulatedCohort] = useState([]);
  const [headcountAdjustments, setHeadcountAdjustments] = useState({});
  const [requirements, setRequirements] = useState([]);

  const [simResult, setSimResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [catalogSkills, setCatalogSkills] = useState([]);

  useEffect(() => {
    async function init() {
      try {
        const evRes = await api.getEvents();
        setEvents(evRes.data || []);
        const active = evRes.data?.find(e => e.name === 'Kala Fest') || evRes.data?.[0];
        if (active) {
          setSelectedEventId(active.id);
          const reqRes = await api.getRequirements(active.id);
          setRequirements(reqRes.data || []);
        }

        const skRes = await api.getSkills();
        setCatalogSkills(skRes.data || []);
      } catch (err) {
        console.error(err);
      }
    }
    init();
  }, []);

  function handleAddSimCandidate() {
    if (!simCandidateName) return;
    setSimulatedCohort([
      ...simulatedCohort,
      { name: simCandidateName, skills: [simCandidateSkill] }
    ]);
    setSimCandidateName('');
  }

  function handleRemoveSimCandidate(index) {
    setSimulatedCohort(simulatedCohort.filter((_, i) => i !== index));
  }

  async function handleRunSimulation() {
    if (!selectedEventId) return;
    setRunning(true);
    try {
      const payload = {
        algorithm: 'ilp',
        adjustments: {
          volunteer_drop_rate_pct: parseFloat(absenteeismRate),
          add_simulated_volunteers: simulatedCohort,
          headcount_multipliers: headcountAdjustments
        }
      };

      const res = await api.runSimulation(selectedEventId, payload);
      setSimResult(res.data);
    } catch (err) {
      alert(err.message || 'Simulation execution failed.');
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 className="h1">What-If Capacity & Scenario Simulator</h1>
            <span className="simulation-pill">
              Simulation · Not published
            </span>
          </div>
          <p className="text-muted" style={{ marginTop: '4px' }}>
            Test volunteer absenteeism, surge demand, and simulated candidate cohorts on isolated data copies
          </p>
        </div>
      </div>

      {/* Scenario Controls Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {/* Control 1: Event & Absenteeism */}
        <div className="card">
          <h3 className="h3" style={{ marginBottom: '14px' }}>1. Attendance & Volunteer Surge Controls</h3>
          
          <div className="form-group">
            <label className="form-label">Target Pilot Event</label>
            <select
              className="form-select"
              value={selectedEventId}
              onChange={(e) => setSelectedEventId(e.target.value)}
            >
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>{ev.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <label className="form-label">Simulated Volunteer Absenteeism / Drop Rate</label>
              <span style={{ fontWeight: 600, color: 'var(--color-primary)' }}>{absenteeismRate}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              step="5"
              value={absenteeismRate}
              onChange={(e) => setAbsenteeismRate(e.target.value)}
              style={{ width: '100%', accentColor: 'var(--color-primary)' }}
            />
            <span className="text-muted text-sm">Simulates unexpected exam/illness dropouts before event execution.</span>
          </div>
        </div>

        {/* Control 2: Simulated Volunteer Cohort */}
        <div className="card">
          <h3 className="h3" style={{ marginBottom: '14px' }}>2. Add Scenario-Only Simulated Volunteers</h3>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Extra Tech Volunteer"
              value={simCandidateName}
              onChange={(e) => setSimCandidateName(e.target.value)}
            />
            <select
              className="form-select"
              style={{ width: '200px' }}
              value={simCandidateSkill}
              onChange={(e) => setSimCandidateSkill(e.target.value)}
            >
              {catalogSkills.map((sk) => (
                <option key={sk.id} value={sk.name}>{sk.name}</option>
              ))}
            </select>
            <button type="button" onClick={handleAddSimCandidate} className="btn btn-secondary btn-sm">
              Add
            </button>
          </div>

          {simulatedCohort.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', maxHeight: '100px', overflowY: 'auto' }}>
              {simulatedCohort.map((sc, idx) => (
                <span key={idx} style={{ backgroundColor: 'var(--color-subtle)', border: '1px solid var(--color-border)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>{sc.name} ({sc.skills[0]})</span>
                  <button type="button" onClick={() => handleRemoveSimCandidate(idx)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--color-danger)' }}>×</button>
                </span>
              ))}
            </div>
          )}
          {simulatedCohort.length === 0 && (
            <p className="text-muted text-sm">No simulated candidates added. Add above to test recruitment impact.</p>
          )}
        </div>
      </div>

      {/* Run Action */}
      <div style={{ marginBottom: '24px' }}>
        <button
          onClick={handleRunSimulation}
          className="btn btn-primary"
          style={{ height: '42px', padding: '0 24px' }}
          disabled={running}
        >
          <Play size={16} />
          <span>{running ? 'Running Isolated Optimization...' : 'Run Scenario Simulation'}</span>
        </button>
      </div>

      {/* Simulation Results Display */}
      {simResult && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <h2 className="h2">Baseline vs. Scenario Comparison</h2>
            <span className="simulation-pill">Simulation · Not published</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            <div className="card">
              <div className="metric-label">Baseline Live Status</div>
              <div style={{ fontSize: '22px', fontWeight: 600 }}>{simResult.baseline.total_allocated} / {simResult.baseline.total_required}</div>
              <div className="text-muted text-sm" style={{ marginTop: '4px' }}>
                Coverage: {simResult.baseline.coverage_pct}% · Vacancies: {simResult.baseline.vacancies}
              </div>
            </div>

            <div className="card" style={{ border: '1px solid var(--color-primary)', backgroundColor: 'var(--color-primary-soft)' }}>
              <div className="metric-label" style={{ color: 'var(--color-primary-hover)' }}>Scenario Result</div>
              <div style={{ fontSize: '22px', fontWeight: 600, color: 'var(--color-primary-hover)' }}>
                {simResult.scenario.total_allocated} / {simResult.scenario.total_required}
              </div>
              <div className="text-muted text-sm" style={{ marginTop: '4px' }}>
                Coverage: {simResult.scenario.coverage_pct}% · Vacancies: {simResult.scenario.vacancies}
              </div>
              <div style={{ fontSize: '11.5px', color: 'var(--color-primary-hover)', fontWeight: 600, marginTop: '4px' }}>
                Simulated Volunteers Assigned: {simResult.scenario.simulated_volunteers_assigned}
              </div>
            </div>

            <div className="card">
              <div className="metric-label">Scenario Impact (Delta)</div>
              <div style={{ fontSize: '22px', fontWeight: 600 }}>
                {simResult.delta.allocated_diff >= 0 ? `+${simResult.delta.allocated_diff}` : simResult.delta.allocated_diff} positions
              </div>
              <div className="text-muted text-sm" style={{ marginTop: '4px' }}>
                Coverage Change: {simResult.delta.coverage_pct_diff > 0 ? `+${simResult.delta.coverage_pct_diff}` : simResult.delta.coverage_pct_diff}%
              </div>
            </div>
          </div>

          {/* Scenario Assignments Table */}
          <div className="card">
            <div className="card-header">
              <h3 className="h3">Scenario Assignments (Isolated · Not Saved to Database)</h3>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Department & Role</th>
                    <th>Priority</th>
                    <th>Assigned Volunteer</th>
                    <th>Identity Type</th>
                  </tr>
                </thead>
                <tbody>
                  {simResult.scenario_assignments?.map((a, i) => (
                    <tr key={i}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{a.department}</div>
                        <div className="text-muted text-sm">{a.role}</div>
                      </td>
                      <td>
                        <Badge type={a.priority}>{a.priority}</Badge>
                      </td>
                      <td style={{ fontWeight: 500 }}>
                        {a.volunteer_name} ({a.volunteer_student_id})
                      </td>
                      <td>
                        {a.is_simulated ? (
                          <span className="simulation-pill" style={{ fontSize: '11px' }}>Simulated Candidate</span>
                        ) : (
                          <span className="text-muted text-sm">Real Committee Volunteer</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
