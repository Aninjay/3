import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { Badge } from '../components/Badge';
import { Calendar, Users, AlertTriangle, CheckCircle2, ArrowRight, ChevronDown, UserRoundCog } from 'lucide-react';

export function OrganizerDashboard({ onSelectEvent, onManageCoreCommittee }) {
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState('');
  const [staffing, setStaffing] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [departmentRequirements, setDepartmentRequirements] = useState([]);
  const [departmentAssignments, setDepartmentAssignments] = useState([]);
  const [departmentHeads, setDepartmentHeads] = useState({});
  const [expandedDepartment, setExpandedDepartment] = useState('');
  const [loading, setLoading] = useState(true);
  const [coverageLoading, setCoverageLoading] = useState(false);
  const [coverageError, setCoverageError] = useState('');

  useEffect(() => {
    async function loadEvents() {
      try {
        const evRes = await api.getEvents();
        const eventList = evRes.data || [];
        setEvents(eventList);

        const activeEvents = eventList.filter(e => e.status === 'upcoming' || e.status === 'ongoing');
        const selectableEvents = activeEvents.length > 0 ? activeEvents : eventList;
        const initialEvent = selectableEvents.find(e => e.name === 'Kala Fest') || selectableEvents[0];
        if (initialEvent) {
          setSelectedEventId(String(initialEvent.id));
        }
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadEvents();
  }, []);

  useEffect(() => {
    if (!selectedEventId) return undefined;
    let cancelled = false;

    async function loadSelectedEvent() {
      setCoverageLoading(true);
      setCoverageError('');
      setExpandedDepartment('');
      setDepartmentHeads({});
      try {
        const [eventRes, staffingRes, recommendationRes, departmentHeadsRes] = await Promise.all([
          api.getEvent(selectedEventId),
          api.getStaffingReport(selectedEventId),
          api.getRecommendations(selectedEventId).catch(() => ({ data: [] })),
          api.getEventDepartmentHeads(selectedEventId).catch(() => ({ data: { departments: [] } }))
        ]);

        const selectedStaffing = staffingRes.data || null;
        let assignments = [];
        if (selectedStaffing?.version_id) {
          const allocationRes = await api.getAllocationVersion(selectedStaffing.version_id);
          assignments = allocationRes.data?.assignments || [];
        }

        if (!cancelled) {
          setDepartmentRequirements(eventRes.data?.requirements || []);
          setStaffing(selectedStaffing);
          setRecommendations(recommendationRes.data || []);
          setDepartmentAssignments(assignments);
          setDepartmentHeads(Object.fromEntries(
            (departmentHeadsRes.data?.departments || []).map(department => [department.department_name, department.head_name])
          ));
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to load selected event staffing:', err);
          setStaffing(null);
          setRecommendations([]);
          setDepartmentRequirements([]);
          setDepartmentAssignments([]);
          setCoverageError(err.message || 'Could not load event staffing.');
        }
      } finally {
        if (!cancelled) setCoverageLoading(false);
      }
    }

    loadSelectedEvent();
    return () => { cancelled = true; };
  }, [selectedEventId]);

  const activeEvents = events.filter(e => e.status === 'upcoming' || e.status === 'ongoing');
  const selectableEvents = activeEvents.length > 0 ? activeEvents : events;
  const selectedEvent = events.find(e => String(e.id) === selectedEventId);
  const totalReq = staffing?.total_required ?? selectedEvent?.total_required ?? 0;
  const totalAlloc = staffing?.total_allocated ?? selectedEvent?.total_allocated ?? 0;
  const totalVac = staffing?.total_vacancies ?? selectedEvent?.total_vacancies ?? Math.max(0, totalReq - totalAlloc);
  const coveragePct = staffing?.coverage_pct ?? (totalReq > 0 ? Math.round((totalAlloc / totalReq) * 100) : 0);

  const coverageRows = staffing?.department_breakdown?.length
    ? staffing.department_breakdown
    : Object.values(departmentRequirements.reduce((departments, requirement) => {
        const department = requirement.department_name;
        if (!departments[department]) {
          departments[department] = { department, required: 0, allocated: 0, vacant: 0, coverage_pct: 0 };
        }
        departments[department].required += Number(requirement.headcount || 0);
        departments[department].vacant = departments[department].required;
        return departments;
      }, {}));

  const sortedCoverageRows = [...coverageRows].sort((a, b) => {
    const headA = departmentHeads[a.department] || '';
    const headB = departmentHeads[b.department] || '';
    if (!headA && headB) return 1;
    if (headA && !headB) return -1;
    return headA.localeCompare(headB) || a.department.localeCompare(b.department);
  });

  if (loading) {
    return <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-muted)' }}>Loading dashboard...</div>;
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <h1 className="h1">Organizer Dashboard</h1>
          <p className="text-muted" style={{ marginTop: '4px' }}>
            Committee staffing overview across upcoming events
          </p>
        </div>
        <button type="button" className="btn btn-outline" onClick={onManageCoreCommittee}>
          <UserRoundCog size={16} />
          <span>Manage Core Committee</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="metric-grid">
        <MetricCard
          label="Upcoming Events"
          value={events.filter(e => e.status === 'upcoming' || e.status === 'ongoing').length}
          sub="Cultural Committee Calendar"
          icon={Calendar}
        />
        <MetricCard
          label="Total Required Positions"
          value={totalReq}
          sub={selectedEvent?.name || 'Selected event'}
          icon={Users}
        />
        <MetricCard
          label="Allocated Staff"
          value={totalAlloc}
          sub={`${coveragePct}% coverage for ${selectedEvent?.name || 'selected event'}`}
          icon={CheckCircle2}
          color="var(--color-success)"
        />
        <MetricCard
          label="Vacant Positions"
          value={totalVac}
          sub="Awaiting assignment"
          icon={AlertTriangle}
          color={totalVac > 0 ? "var(--color-warning)" : "var(--color-success)"}
        />
      </div>

      {/* Actionable Recommendations Banner */}
      {recommendations.length > 0 && (
        <div className="card" style={{ marginBottom: '24px', borderLeft: '4px solid var(--color-primary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <AlertTriangle size={18} color="var(--color-primary)" />
            <h3 className="h3">System Shortage Insights & Recommendations</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {recommendations.slice(0, 3).map((rec, i) => (
              <div key={i} style={{ padding: '10px 14px', backgroundColor: 'var(--color-subtle)', borderRadius: 'var(--radius-md)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--color-text)' }}>{rec.title}</span>
                  <Badge type={rec.priority}>{rec.priority}</Badge>
                </div>
                <p className="text-muted" style={{ fontSize: '13px', marginTop: '4px' }}>{rec.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Two Column Layout: Events list & Department Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))', gap: '24px' }}>
        {/* Events Table */}
        <div className="card">
          <div className="card-header">
            <h3 className="h3">Upcoming Cultural Events</h3>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Event Name</th>
                  <th>Dates</th>
                  <th>Status</th>
                  <th>Staffing</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{ev.name}</div>
                      <div className="text-muted text-sm">{ev.venue}</div>
                    </td>
                    <td className="text-sm">
                      {new Date(ev.starts_at).toLocaleDateString()}
                    </td>
                    <td>
                      <Badge type={ev.status}>{ev.status}</Badge>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600 }}>{ev.total_allocated || 0}</span>
                      <span className="text-muted"> / {ev.total_required || 0}</span>
                    </td>
                    <td>
                      <button
                        onClick={() => onSelectEvent(ev.id)}
                        className="btn btn-outline btn-sm"
                      >
                        Manage
                        <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Department Staffing Table */}
        <div className="card">
          <div className="card-header" style={{ alignItems: 'center', gap: '16px' }}>
            <div>
              <h3 className="h3">{selectedEvent?.name || 'Event'} Department Coverage</h3>
              <p className="text-muted text-sm" style={{ marginTop: '4px' }}>
                Click a department to see its assigned volunteers.
              </p>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--color-muted)' }}>
              <span>Event</span>
              <select
                className="form-select"
                aria-label="Select event for department coverage"
                value={selectedEventId}
                onChange={(e) => setSelectedEventId(e.target.value)}
                style={{ minWidth: '160px', maxWidth: '220px' }}
              >
                {selectableEvents.map((event) => (
                  <option key={event.id} value={String(event.id)}>{event.name}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Headed By</th>
                  <th>Required</th>
                  <th>Allocated</th>
                  <th>Vacant</th>
                  <th>Coverage</th>
                </tr>
              </thead>
              <tbody>
                {coverageLoading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: 'var(--color-muted)' }}>
                      Loading event staffing…
                    </td>
                  </tr>
                ) : coverageError ? (
                  <tr>
                    <td colSpan={6} role="alert" style={{ textAlign: 'center', color: 'var(--color-danger)' }}>
                      {coverageError}
                    </td>
                  </tr>
                ) : sortedCoverageRows.length > 0 ? (
                  sortedCoverageRows.map((department) => {
                    const isExpanded = expandedDepartment === department.department;
                    const assignedVolunteers = departmentAssignments.filter(
                      assignment => assignment.department_name === department.department
                    );
                    const departmentCoverage = department.coverage_pct ?? (
                      department.required > 0 ? Math.round((department.allocated / department.required) * 100) : 0
                    );

                    return (
                      <React.Fragment key={department.department}>
                        <tr>
                          <td style={{ fontWeight: 500 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <button
                                type="button"
                                aria-label={`${isExpanded ? 'Hide' : 'Show'} assigned volunteers for ${department.department}`}
                                aria-expanded={isExpanded}
                                onClick={() => setExpandedDepartment(isExpanded ? '' : department.department)}
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  width: '24px',
                                  height: '24px',
                                  padding: 0,
                                  border: 'none',
                                  background: 'transparent',
                                  color: 'var(--color-muted)',
                                  cursor: 'pointer'
                                }}
                              >
                                <ChevronDown size={16} style={{ transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }} />
                              </button>
                              <span>{department.department}</span>
                            </div>
                          </td>
                          <td>{departmentHeads[department.department] || <span className="text-muted">—</span>}</td>
                          <td>{department.required}</td>
                          <td style={{ color: 'var(--color-success)', fontWeight: 600 }}>{department.allocated}</td>
                          <td style={{ color: department.vacant > 0 ? 'var(--color-danger)' : 'inherit', fontWeight: department.vacant > 0 ? 600 : 400 }}>
                            {department.vacant}
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <div style={{ flex: 1, height: '6px', backgroundColor: 'var(--color-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
                                <div style={{
                                  width: `${departmentCoverage}%`,
                                  height: '100%',
                                  backgroundColor: departmentCoverage === 100 ? 'var(--color-success)' : 'var(--color-primary)'
                                }} />
                              </div>
                              <span style={{ fontSize: '12px', fontWeight: 600, minWidth: '36px' }}>{departmentCoverage}%</span>
                            </div>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr>
                            <td colSpan={6} style={{ backgroundColor: 'var(--color-subtle)', padding: '12px 20px 12px 42px' }}>
                              {assignedVolunteers.length > 0 ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  {assignedVolunteers.map((assignment) => (
                                    <div key={assignment.id} style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', fontSize: '13px' }}>
                                      <span style={{ fontWeight: 600 }}>{assignment.volunteer_name}</span>
                                      <span className="text-muted">
                                        {assignment.role_name}{assignment.student_id ? ` · ${assignment.student_id}` : ''}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-muted text-sm">No volunteers assigned to this department for {selectedEvent?.name || 'this event'}.</span>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: 'var(--color-muted)' }}>
                      No staffing requirements recorded for this event yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
