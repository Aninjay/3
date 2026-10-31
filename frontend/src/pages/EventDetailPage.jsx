import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { 
  Calendar, MapPin, Users, Award, Play, CheckCircle2, Download, FileSpreadsheet, FileText,
  AlertTriangle, RefreshCw, Plus, Edit3, Trash2, ArrowLeft, Send
} from 'lucide-react';

export function EventDetailPage({ eventId, onBack }) {
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);

  // Versions State
  const [versions, setVersions] = useState([]);
  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [versionDetail, setVersionDetail] = useState(null);
  const [engineLoading, setEngineLoading] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [exportingRosterFormat, setExportingRosterFormat] = useState('');
  const [rosterExportError, setRosterExportError] = useState('');

  // Manual Edit Modal State
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editOp, setEditOp] = useState('add'); // 'add', 'replace', 'remove'
  const [editReqId, setEditReqId] = useState('');
  const [editVolId, setEditVolId] = useState('');
  const [replacementVolId, setReplacementVolId] = useState('');
  const [skillOverride, setSkillOverride] = useState(false);
  const [overrideReason, setOverrideReason] = useState('');
  const [modalWarning, setModalWarning] = useState('');
  const [modalError, setModalError] = useState('');
  const [availableVolunteers, setAvailableVolunteers] = useState([]);

  // Capacity Calculator Modal State
  const [calcModalOpen, setCalcModalOpen] = useState(false);
  const [calcWorkload, setCalcWorkload] = useState('160');
  const [calcServiceTime, setCalcServiceTime] = useState('0.5');
  const [calcPeakWindow, setCalcPeakWindow] = useState('20');
  const [calcResult, setCalcResult] = useState(null);

  // Add Requirement Modal State
  const [reqModalOpen, setReqModalOpen] = useState(false);
  const [reqDeptId, setReqDeptId] = useState(1);
  const [reqRole, setReqRole] = useState('');
  const [reqHeadcount, setReqHeadcount] = useState(2);
  const [reqPriority, setReqPriority] = useState('normal');
  const [reqMandatorySkills, setReqMandatorySkills] = useState([]);
  const [catalogSkills, setCatalogSkills] = useState([]);
  const [departments, setDepartments] = useState([]);

  async function loadEventData() {
    setLoading(true);
    try {
      const evRes = await api.getEvent(eventId);
      setEvent(evRes.data);

      const verRes = await api.getEventAllocations(eventId);
      setVersions(verRes.data || []);

      // Versions are returned newest-first; keep the latest draft visible so a fresh run and manual fills persist on reload.
      const targetVer = verRes.data?.[0];
      if (targetVer) {
        setSelectedVersionId(targetVer.id);
        const detailRes = await api.getAllocationVersion(targetVer.id);
        setVersionDetail(detailRes.data);
      }

      const skRes = await api.getSkills();
      setCatalogSkills(skRes.data || []);

      const volRes = await api.getVolunteers({ status: 'active' });
      setAvailableVolunteers(volRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEventData();
  }, [eventId]);

  async function loadVersion(vId) {
    setSelectedVersionId(vId);
    try {
      const res = await api.getAllocationVersion(vId);
      setVersionDetail(res.data);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleRunAlgorithm(algo) {
    setEngineLoading(true);
    setComparisonData(null);
    try {
      const res = await api.runAllocation(eventId, { algorithm: algo });
      if (res.data.comparison) {
        setComparisonData(res.data.comparison);
      }
      await loadEventData();
      if (res.data.version_id) {
        await loadVersion(res.data.version_id);
      }
    } catch (err) {
      alert(err.message || 'Failed to run allocation.');
    } finally {
      setEngineLoading(false);
    }
  }

  async function handleCalculateCapacity() {
    try {
      const res = await api.calculateCapacity(eventId, {
        workload_value: parseFloat(calcWorkload),
        service_time_value: parseFloat(calcServiceTime),
        peak_window_value: parseFloat(calcPeakWindow)
      });
      setCalcResult(res.data);
      setReqHeadcount(res.data.calculated_headcount);
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleSaveManualEdit(e) {
    e.preventDefault();
    setModalWarning('');
    setModalError('');

    try {
      const payload = {
        operation: editOp,
        requirement_id: parseInt(editReqId),
        volunteer_id: parseInt(editVolId),
        replacement_volunteer_id: replacementVolId ? parseInt(replacementVolId) : null,
        skill_override: skillOverride,
        override_reason: overrideReason
      };

      await api.editAssignment(selectedVersionId, payload);
      setEditModalOpen(false);
      await loadVersion(selectedVersionId);
    } catch (err) {
      if (err.data?.warning) {
        setModalWarning(err.data.warning.message);
        setSkillOverride(true);
      } else {
        setModalError(err.message || 'Failed to update assignment.');
      }
    }
  }

  function openManualFill(requirementId) {
    const assignedIds = new Set(versionDetail?.assignments?.map((assignment) => assignment.volunteer_id) || []);
    const firstAvailable = availableVolunteers.find((volunteer) => !assignedIds.has(volunteer.id));
    setEditOp('add');
    setEditReqId(String(requirementId));
    setEditVolId(firstAvailable ? String(firstAvailable.id) : '');
    setSkillOverride(false);
    setOverrideReason('');
    setModalWarning('');
    setModalError('');
    setEditModalOpen(true);
  }

  async function handleApproveVersion() {
    if (!confirm(`Are you sure you want to approve allocation version #${versionDetail.version_number}?`)) return;
    try {
      await api.approveAllocation(selectedVersionId, "Approved by Organizer");
      await loadVersion(selectedVersionId);
      await loadEventData();
      alert(`Version #${versionDetail.version_number} approved successfully!`);
    } catch (err) {
      alert(err.message);
    }
  }

  async function handlePublishVersion() {
    if (!confirm(`Confirm publication of version #${versionDetail.version_number}? Volunteers will now see their assigned roles.`)) return;
    try {
      await api.publishAllocation(selectedVersionId);
      await loadVersion(selectedVersionId);
      await loadEventData();
      alert(`Version #${versionDetail.version_number} is now officially published!`);
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleRegenerateVersion() {
    if (!confirm("Regenerating will create a brand new draft version. Any unsaved manual changes will not carry over. Proceed?")) return;
    try {
      const res = await api.regenerateAllocation(selectedVersionId, { confirmed: true, algorithm: 'ilp' });
      await loadEventData();
      if (res.data.version_id) {
        await loadVersion(res.data.version_id);
      }
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleDownloadRoster(format) {
    setExportingRosterFormat(format);
    setRosterExportError('');
    try {
      const { blob, filename } = await api.downloadRoster(eventId, format);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setRosterExportError(err.message || 'Roster download failed.');
    } finally {
      setExportingRosterFormat('');
    }
  }

  if (loading || !event) {
    return <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-muted)' }}>Loading event details...</div>;
  }

  return (
    <div>
      {/* Back button & Event Header */}
      <div style={{ marginBottom: '20px' }}>
        <button onClick={onBack} className="btn btn-secondary btn-sm" style={{ marginBottom: '12px' }}>
          <ArrowLeft size={14} />
          <span>Back to Events</span>
        </button>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 className="h1">{event.name}</h1>
              <Badge type={event.status}>{event.status}</Badge>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', color: 'var(--color-muted)', fontSize: '13px', marginTop: '6px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <MapPin size={14} />
                {event.venue}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Calendar size={14} />
                {new Date(event.starts_at).toLocaleDateString()} – {new Date(event.ends_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            {event.status !== 'archived' && (
              <button 
                onClick={async () => {
                  if (confirm("Archive this event? It will become read-only.")) {
                    await api.archiveEvent(event.id);
                    await loadEventData();
                  }
                }}
                className="btn btn-secondary btn-sm"
              >
                Archive Event
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Staffing requirements and capacity */}
      <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 className="h3">Event Department Requirements</h3>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              <button
                onClick={() => handleRunAlgorithm('ilp')}
                className="btn btn-primary btn-sm"
                disabled={engineLoading || !event.requirements?.length}
              >
                <Play size={15} />
                <span>{engineLoading ? 'Allocating by skills…' : 'Allocate Volunteers by Skills'}</span>
              </button>
            <button 
              onClick={() => setCalcModalOpen(true)}
              className="btn btn-secondary btn-sm"
            >
              Open Capacity Calculator Formula
            </button>
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Department & Role</th>
                  <th>Priority</th>
                  <th>Headcount</th>
                  <th>Mandatory Skills</th>
                  <th>Preferred Skills</th>
                  <th>Source Mode</th>
                </tr>
              </thead>
              <tbody>
                {event.requirements?.map((req) => (
                  <tr key={req.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{req.department_name}</div>
                      <div className="text-muted text-sm">{req.role_name}</div>
                    </td>
                    <td>
                      <Badge type={req.priority}>{req.priority}</Badge>
                    </td>
                    <td style={{ fontWeight: 600 }}>{req.headcount}</td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {req.mandatory_skills?.map((sk, i) => (
                          <span key={i} style={{ backgroundColor: 'var(--color-subtle)', border: '1px solid var(--color-border)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' }}>
                            {sk}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {req.preferred_skills?.map((sk, i) => (
                          <span key={i} style={{ color: 'var(--color-muted)', fontSize: '11px' }}>
                            {sk}
                          </span>
                        )) || '—'}
                      </div>
                    </td>
                    <td className="text-muted text-sm">
                      {req.requirement_source === 'workload_calculation' ? 'Workload Capacity' : 'Fixed Headcount'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {versionDetail && (
            <div className="card" style={{ marginTop: '20px' }}>
              <div className="card-header">
                <div>
                  <h3 className="h3">Volunteer Allocation</h3>
                  <p className="text-muted text-sm" style={{ marginTop: '4px' }}>
                    {versionDetail.total_allocated} assigned · {versionDetail.total_vacancies} open slots. Slots without a suitable match stay open for the convener.
                  </p>
                </div>
                <span className="text-muted text-sm">Version #{versionDetail.version_number}</span>
              </div>
              {(() => {
                const assignedByReq = new Map();
                (versionDetail.assignments || []).forEach((assignment) => {
                  assignedByReq.set(assignment.requirement_id, (assignedByReq.get(assignment.requirement_id) || 0) + 1);
                });
                const vacancies = (event.requirements || []).flatMap((req) => {
                  const open = Math.max(0, Number(req.headcount) - (assignedByReq.get(req.id) || 0));
                  return Array.from({ length: open }, (_, index) => ({ req, index }));
                });
                return vacancies.length ? (
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontWeight: 600, marginBottom: '8px' }}>Open slots ({vacancies.length})</div>
                    <div className="table-container">
                      <table>
                        <thead><tr><th>Department & Role</th><th>Required skills</th><th>Action</th></tr></thead>
                        <tbody>{vacancies.map(({ req, index }) => (
                          <tr key={`${req.id}-${index}`}>
                            <td><strong>{req.department_name}</strong><div className="text-muted text-sm">{req.role_name} · Slot {index + 1}</div></td>
                            <td className="text-muted text-sm">{req.mandatory_skills?.length ? req.mandatory_skills.join(', ') : 'No mandatory skills'}</td>
                            <td><button className="btn btn-secondary btn-sm" onClick={() => openManualFill(req.id)} disabled={!availableVolunteers.some((volunteer) => !(versionDetail.assignments || []).some((assignment) => assignment.volunteer_id === volunteer.id))}>Assign manually</button></td>
                          </tr>
                        ))}</tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <p style={{ color: 'var(--color-success)', marginBottom: '16px' }}>All required positions are filled.</p>
                );
              })()}
              <div className="table-container">
                <table>
                  <thead><tr><th>Department & Role</th><th>Volunteer</th><th>Priority</th></tr></thead>
                  <tbody>{(versionDetail.assignments || []).map((assignment) => (
                    <tr key={assignment.id}>
                      <td><strong>{assignment.department_name}</strong><div className="text-muted text-sm">{assignment.role_name}</div></td>
                      <td>{assignment.volunteer_name} <span className="text-muted text-sm">({assignment.student_id})</span></td>
                      <td><Badge type={assignment.priority}>{assignment.priority}</Badge></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </div>
          )}
      </div>

      {/* Allocation engine and review panels are hidden from this page. */}
      {false && (
        <div>
          <div className="card" style={{ marginBottom: '24px' }}>
            <div className="card-header">
              <div>
                <h3 className="h3">Run Python Allocation Engine</h3>
                <p className="text-muted text-sm">
                  Executes allocation algorithms using verified volunteer capabilities and department demand.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                onClick={() => handleRunAlgorithm('ilp')}
                className="btn btn-primary"
                disabled={engineLoading}
              >
                <Play size={15} />
                <span>Run PuLP ILP Optimizer</span>
              </button>
              <button
                onClick={() => handleRunAlgorithm('greedy')}
                className="btn btn-secondary"
                disabled={engineLoading}
              >
                <Play size={15} />
                <span>Run Greedy Baseline</span>
              </button>
              <button
                onClick={() => handleRunAlgorithm('compare')}
                className="btn btn-outline"
                disabled={engineLoading}
              >
                <span>Compare Both on Same Snapshot</span>
              </button>
            </div>
          </div>

          {/* Side-by-Side Comparison if generated */}
          {comparisonData && (
            <div className="card" style={{ marginBottom: '24px', backgroundColor: 'var(--color-subtle)' }}>
              <h3 className="h3" style={{ marginBottom: '12px' }}>Greedy Baseline vs. PuLP ILP Comparison</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div style={{ background: '#FFFFFF', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                  <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '8px' }}>Greedy Baseline</div>
                  <div>Allocated: <strong>{comparisonData.greedy.allocated}</strong> / {comparisonData.total_required}</div>
                  <div>Coverage: <strong>{comparisonData.greedy.coverage_pct}%</strong></div>
                  <div>Vacancies: <strong>{comparisonData.greedy.vacancies}</strong></div>
                  <div>Runtime: <strong>{comparisonData.greedy.runtime_seconds}s</strong></div>
                </div>
                <div style={{ background: '#FFFFFF', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-primary)' }}>
                  <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-primary)', marginBottom: '8px' }}>PuLP ILP Optimizer</div>
                  <div>Allocated: <strong>{comparisonData.ilp.allocated}</strong> / {comparisonData.total_required}</div>
                  <div>Coverage: <strong>{comparisonData.ilp.coverage_pct}%</strong></div>
                  <div>Vacancies: <strong>{comparisonData.ilp.vacancies}</strong></div>
                  <div>Runtime: <strong>{comparisonData.ilp.runtime_seconds}s</strong></div>
                  <div>Objective Score: <strong>{comparisonData.ilp.objective_value}</strong></div>
                </div>
              </div>
            </div>
          )}

          {/* Allocation Versions History */}
          <div className="card">
            <h3 className="h3" style={{ marginBottom: '16px' }}>Generated Allocation Versions</h3>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Algorithm</th>
                    <th>Status</th>
                    <th>Staffing Fill</th>
                    <th>Created At</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((ver) => (
                    <tr key={ver.id} style={{ backgroundColor: ver.id === selectedVersionId ? 'var(--color-primary-soft)' : 'inherit' }}>
                      <td style={{ fontWeight: 600 }}>Version #{ver.version_number}</td>
                      <td style={{ textTransform: 'uppercase', fontSize: '12px', fontWeight: 600 }}>{ver.algorithm}</td>
                      <td>
                        <Badge type={ver.status}>{ver.status}</Badge>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600 }}>{ver.allocated_count}</span>
                        <span className="text-muted"> / {ver.required_count} ({ver.coverage_pct}%)</span>
                      </td>
                      <td className="text-muted text-sm">{new Date(ver.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                      <td>
                        <button
                          onClick={() => loadVersion(ver.id)}
                          className="btn btn-secondary btn-sm"
                        >
                          Review & Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: REVIEW, MANUAL EDITS & PUBLISH */}
      {false && versionDetail && (
        <div>
          {/* Decision Action Bar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            backgroundColor: 'var(--color-subtle)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border)',
            marginBottom: '20px'
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 600, fontSize: '15px' }}>
                  Reviewed Version #{versionDetail.version_number}
                </span>
                <Badge type={versionDetail.status}>{versionDetail.status}</Badge>
              </div>
              <div className="text-muted text-sm" style={{ marginTop: '2px' }}>
                Allocated: {versionDetail.total_allocated} · Vacancies: {versionDetail.total_vacancies} · Coverage: {versionDetail.coverage_pct}%
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={handleRegenerateVersion}
                className="btn btn-secondary btn-sm"
              >
                <RefreshCw size={14} />
                <span>Regenerate...</span>
              </button>

              {versionDetail.status === 'draft' && (
                <button
                  onClick={handleApproveVersion}
                  className="btn btn-secondary btn-sm"
                >
                  <CheckCircle2 size={14} />
                  <span>Approve Version</span>
                </button>
              )}

              {versionDetail.status === 'approved' && (
                <button
                  onClick={handlePublishVersion}
                  className="btn btn-primary btn-sm"
                >
                  <Send size={14} />
                  <span>Publish to Volunteers</span>
                </button>
              )}

              {versionDetail.status === 'published' && (
                <span style={{ fontSize: '12px', color: 'var(--color-success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CheckCircle2 size={14} />
                  Live Official Allocation
                </span>
              )}
            </div>
          </div>

          {versionDetail.status === 'published' && (
            <div className="card" style={{ marginBottom: '20px' }}>
              <div className="card-header" style={{ alignItems: 'center' }}>
                <div>
                  <h3 className="h3">Department Head Rosters</h3>
                  <p className="text-muted text-sm" style={{ marginTop: '4px' }}>
                    Download the published allocation as CSV or an Excel workbook with a sheet for each department.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleDownloadRoster('csv')}
                    disabled={Boolean(exportingRosterFormat)}
                  >
                    {exportingRosterFormat === 'csv' ? <Download size={14} /> : <FileText size={14} />}
                    <span>Download CSV</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => handleDownloadRoster('xlsx')}
                    disabled={Boolean(exportingRosterFormat)}
                  >
                    {exportingRosterFormat === 'xlsx' ? <Download size={14} /> : <FileSpreadsheet size={14} />}
                    <span>Download Excel</span>
                  </button>
                </div>
              </div>
              {rosterExportError && (
                <p role="alert" style={{ color: 'var(--color-danger)', fontSize: '13px' }}>
                  {rosterExportError}
                </p>
              )}
            </div>
          )}

          {/* Vacancies & Shortages Alert Box */}
          {versionDetail.total_vacancies > 0 && (
            <div className="card" style={{ marginBottom: '20px', borderLeft: '4px solid var(--color-danger)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <AlertTriangle size={18} color="var(--color-danger)" />
                <h3 className="h3">Vacancies & Shortage Diagnostics ({versionDetail.total_vacancies} unfilled)</h3>
              </div>
              <p className="text-muted text-sm" style={{ marginBottom: '12px' }}>
                Vacancies are reported honestly. You may manually assign an eligible unassigned candidate or leave positions open.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {versionDetail.assignments && (
                  <div style={{ fontSize: '13px' }}>
                    Unassigned active volunteers available in pool: <strong>{versionDetail.unassigned_volunteers?.length || 0}</strong>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Assigned Volunteers Table */}
          <div className="card" style={{ marginBottom: '24px' }}>
            <div className="card-header">
              <h3 className="h3">Assigned Volunteers</h3>
              <button
                onClick={() => {
                  setEditOp('add');
                  setEditReqId(event.requirements?.[0]?.id || '');
                  setEditVolId(versionDetail.unassigned_volunteers?.[0]?.id || '');
                  setSkillOverride(false);
                  setOverrideReason('');
                  setModalWarning('');
                  setModalError('');
                  setEditModalOpen(true);
                }}
                className="btn btn-secondary btn-sm"
              >
                <Plus size={14} />
                <span>Manual Add / Replace</span>
              </button>
            </div>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Department & Role</th>
                    <th>Assigned Volunteer</th>
                    <th>Student ID</th>
                    <th>Priority</th>
                    <th>Source</th>
                    <th>Override Reason</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {versionDetail.assignments?.map((a) => (
                    <tr key={a.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{a.department_name}</div>
                        <div className="text-muted text-sm">{a.role_name}</div>
                      </td>
                      <td style={{ fontWeight: 500 }}>{a.volunteer_name}</td>
                      <td>
                        <code style={{ fontSize: '12px' }}>{a.student_id}</code>
                      </td>
                      <td>
                        <Badge type={a.priority}>{a.priority}</Badge>
                      </td>
                      <td>
                        <span style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 600, color: 'var(--color-muted)' }}>
                          {a.assignment_source}
                        </span>
                      </td>
                      <td className="text-sm">
                        {a.skill_override ? (
                          <span style={{ color: 'var(--color-warning)' }}>
                            Override: {a.override_reason}
                          </span>
                        ) : '—'}
                      </td>
                      <td>
                        <button
                          onClick={async () => {
                            if (confirm(`Remove ${a.volunteer_name} from this role?`)) {
                              await api.editAssignment(selectedVersionId, {
                                operation: 'remove',
                                requirement_id: a.requirement_id,
                                volunteer_id: a.volunteer_id
                              });
                              await loadVersion(selectedVersionId);
                            }
                          }}
                          className="btn btn-secondary btn-sm"
                          style={{ color: 'var(--color-danger)' }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Capacity Calculator Modal */}
      <Modal
        isOpen={calcModalOpen}
        onClose={() => setCalcModalOpen(false)}
        title="Capacity Staffing Calculator"
      >
        <p className="text-muted text-sm" style={{ marginBottom: '16px' }}>
          Formula from Project Proposal: <code>Required Staff = ceil(Workload × Service Time ÷ Peak Window)</code>
        </p>

        <div className="form-group">
          <label className="form-label">Expected Workload (Units / Deliveries / Attendees)</label>
          <input
            type="number"
            className="form-input"
            value={calcWorkload}
            onChange={(e) => setCalcWorkload(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Service Time per Unit (Hours)</label>
          <input
            type="number"
            step="0.1"
            className="form-input"
            value={calcServiceTime}
            onChange={(e) => setCalcServiceTime(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Peak Operating Window (Hours)</label>
          <input
            type="number"
            step="0.5"
            className="form-input"
            value={calcPeakWindow}
            onChange={(e) => setCalcPeakWindow(e.target.value)}
          />
        </div>

        {calcResult && (
          <div className="card" style={{ backgroundColor: 'var(--color-primary-soft)', border: '1px solid var(--color-primary)', marginTop: '16px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-primary-hover)' }}>
              Calculated Staff Demand: {calcResult.calculated_headcount} Volunteers
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-muted)', marginTop: '4px' }}>
              Raw Demand: {calcResult.raw_demand} → ceil({calcResult.raw_demand}) = {calcResult.calculated_headcount}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px' }}>
          <button className="btn btn-secondary" onClick={() => setCalcModalOpen(false)}>Close</button>
          <button className="btn btn-primary" onClick={handleCalculateCapacity}>Calculate</button>
        </div>
      </Modal>

      {/* Manual Edit Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Manual Assignment Edit"
      >
        {modalWarning && (
          <div className="banner banner-warning">
            <AlertTriangle size={16} />
            <div>
              <div style={{ fontWeight: 600 }}>Skill Mismatch Warning</div>
              <div>{modalWarning}</div>
            </div>
          </div>
        )}

        {modalError && (
          <div className="banner banner-danger">
            <div>{modalError}</div>
          </div>
        )}

        <form onSubmit={handleSaveManualEdit}>
          <div className="form-group">
            <label className="form-label">Target Role</label>
            <select
              className="form-select"
              value={editReqId}
              onChange={(e) => setEditReqId(e.target.value)}
              required
            >
              {event.requirements?.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.department_name} — {r.role_name} (Priority: {r.priority})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Select Volunteer</label>
            <select
              className="form-select"
              value={editVolId}
              onChange={(e) => setEditVolId(e.target.value)}
              required
            >
              {availableVolunteers.filter((v) => editOp !== 'add' || !(versionDetail?.assignments || []).some((assignment) => assignment.volunteer_id === v.id)).map((v) => (
                <option key={v.id} value={v.id}>
                  {v.full_name} ({v.student_id}) {v.active_status ? '' : '— [INACTIVE]'}
                </option>
              ))}
            </select>
          </div>

          {skillOverride && (
            <div className="form-group" style={{ marginTop: '14px', borderTop: '1px solid var(--color-border)', paddingTop: '12px' }}>
              <label className="form-label" style={{ color: 'var(--color-danger)' }}>
                Mandatory Skill Override Reason (Required)
              </label>
              <textarea
                className="form-textarea"
                placeholder="Explain why this volunteer is suitable despite missing the mandatory skill..."
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                required
              />
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setEditModalOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
            >
              {skillOverride ? 'Confirm & Override' : 'Save Assignment'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
