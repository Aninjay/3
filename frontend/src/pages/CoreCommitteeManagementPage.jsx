import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, KeyRound, Mail, Save, UserPlus, Users } from 'lucide-react';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';

const SHARED_CORE_LOGIN_EMAIL = 'core@tapmi.edu.in';

export function CoreCommitteeManagementPage() {
  const [members, setMembers] = useState([]);
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState('');
  const [departments, setDepartments] = useState([]);
  const [selectedHeads, setSelectedHeads] = useState({});
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState(SHARED_CORE_LOGIN_EMAIL);
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(true);
  const [assignmentLoading, setAssignmentLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [passwordTarget, setPasswordTarget] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const activeMembers = members
    .filter(member => member.status === 'active')
    .sort((a, b) => a.full_name.localeCompare(b.full_name));
  const assignedHeadCount = Object.values(selectedHeads).filter(Boolean).length;

  useEffect(() => {
    let current = true;
    async function loadPage() {
      setLoading(true);
      try {
        const [memberResponse, eventResponse] = await Promise.all([
          api.getCoreCommitteeMembers(),
          api.getEvents()
        ]);
        if (!current) return;
        setMembers(memberResponse.data || []);
        const assignableEvents = (eventResponse.data || []).filter(event => event.status === 'upcoming' || event.status === 'ongoing');
        setEvents(assignableEvents);
        if (assignableEvents.length > 0) setSelectedEventId(String(assignableEvents[0].id));
      } catch (err) {
        if (current) setError(err.message || 'Could not load Core Committee management data.');
      } finally {
        if (current) setLoading(false);
      }
    }
    loadPage();
    return () => { current = false; };
  }, []);

  useEffect(() => {
    if (!selectedEventId) {
      setDepartments([]);
      setSelectedHeads({});
      return undefined;
    }

    let current = true;
    async function loadDepartmentHeads() {
      setAssignmentLoading(true);
      setError('');
      try {
        const response = await api.getEventDepartmentHeads(selectedEventId);
        if (!current) return;
        const rows = response.data?.departments || [];
        setDepartments(rows);
        setSelectedHeads(Object.fromEntries(rows.map(row => [
          String(row.department_id), row.head_user_id ? String(row.head_user_id) : ''
        ])));
      } catch (err) {
        if (current) setError(err.message || 'Could not load department head assignments.');
      } finally {
        if (current) setAssignmentLoading(false);
      }
    }
    loadDepartmentHeads();
    return () => { current = false; };
  }, [selectedEventId]);

  async function handleCreateMember(event) {
    event.preventDefault();
    setError('');
    setSuccess('');
    setCreating(true);
    try {
      const response = await api.createCoreCommitteeMember({ full_name: fullName, email, login_id: loginId, password });
      setMembers(current => [...current, response.data].sort((a, b) => a.full_name.localeCompare(b.full_name)));
      setFullName('');
      setEmail(SHARED_CORE_LOGIN_EMAIL);
      setLoginId('');
      setPassword('');
      setSuccess(`${response.data.full_name} can now sign in as a Core Committee member.`);
    } catch (err) {
      setError(err.message || 'Could not create the Core Committee account.');
    } finally {
      setCreating(false);
    }
  }

  async function handleSetMemberPassword(event) {
    event.preventDefault();
    if (!passwordTarget) return;
    setPasswordError('');
    setPasswordSaving(true);
    try {
      await api.setCoreCommitteePassword(passwordTarget.id, newPassword);
      setMembers(current => current.map(member => member.id === passwordTarget.id ? { ...member, status: 'active' } : member));
      setPasswordTarget(null);
      setNewPassword('');
      setSuccess(`Password set for ${passwordTarget.full_name}. It is stored securely and cannot be viewed later.`);
    } catch (err) {
      setPasswordError(err.message || 'Could not set the Core Committee password.');
    } finally {
      setPasswordSaving(false);
    }
  }

  async function handleSaveHeads() {
    if (!selectedEventId) return;
    setError('');
    setSuccess('');

    const selectedUserIds = departments
      .map(department => selectedHeads[String(department.department_id)])
      .filter(Boolean);
    if (new Set(selectedUserIds).size !== selectedUserIds.length) {
      const message = 'A Core Committee member can head only one department per event. Choose a different member for each department.';
      setError(message);
      return;
    }

    setSaving(true);
    try {
      const assignments = departments.map(department => ({
        department_id: department.department_id,
        user_id: selectedHeads[String(department.department_id)] || null
      }));
      await api.saveEventDepartmentHeads(selectedEventId, assignments);
      setSuccess('Department heads saved. Members will see their departments and volunteer rosters when they sign in.');
      const response = await api.getEventDepartmentHeads(selectedEventId);
      const rows = response.data?.departments || [];
      setDepartments(rows);
      setSelectedHeads(Object.fromEntries(rows.map(row => [
        String(row.department_id), row.head_user_id ? String(row.head_user_id) : ''
      ])));
    } catch (err) {
      const message = err.message || 'Could not save department head assignments.';
      setError(message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-muted)' }}>Loading Core Committee tools...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1 className="h1">Core Committee</h1>
        <p className="text-muted" style={{ marginTop: '4px' }}>
          Create member accounts and assign a department head for each published event roster.
        </p>
      </div>

      {error && (
        <div className="banner banner-danger" role="alert" style={{ marginBottom: '16px' }}>
          <AlertCircle size={16} /><span>{error}</span>
        </div>
      )}
      {success && (
        <div className="banner banner-success" role="status" style={{ marginBottom: '16px' }}>
          <CheckCircle2 size={16} /><span>{success}</span>
        </div>
      )}

      <section className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <UserPlus size={18} color="var(--color-primary)" />
            <div>
              <h2 className="h3">Add a Core Committee Member</h2>
          <p className="text-muted text-sm">Use the shared committee login email. Each member needs a different password; the login ID remains available as an individual sign-in option.</p>
            </div>
          </div>
        </div>
        <form onSubmit={handleCreateMember}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="core-member-name">Full name</label>
              <input id="core-member-name" className="form-input" value={fullName} onChange={event => setFullName(event.target.value)} maxLength={160} required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="core-member-email">Shared Committee Login Email</label>
              <div style={{ position: 'relative' }}>
                <Mail size={15} aria-hidden="true" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-muted)' }} />
              <input id="core-member-email" type="email" className="form-input" style={{ paddingLeft: '36px' }} value={email} readOnly />
              </div>
              <span className="text-muted text-sm">All Core Committee members sign in with this email. Each member must have a different password.</span>
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="core-member-login-id">Unique login ID</label>
              <input id="core-member-login-id" className="form-input" placeholder="e.g. core.jane" value={loginId} onChange={event => setLoginId(event.target.value)} maxLength={80} pattern="[A-Za-z0-9._-]{2,80}" required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="core-member-password">Create password</label>
              <div style={{ position: 'relative' }}>
                <KeyRound size={15} aria-hidden="true" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-muted)' }} />
                <input id="core-member-password" type="password" className="form-input" style={{ paddingLeft: '36px' }} value={password} onChange={event => setPassword(event.target.value)} minLength={8} required />
              </div>
              <span className="text-muted text-sm">At least 8 characters.</span>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" className="btn btn-primary" disabled={creating}>
              <UserPlus size={15} />{creating ? 'Creating...' : 'Create Member Account'}
            </button>
          </div>
        </form>
      </section>

      <section className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Users size={18} color="var(--color-primary)" />
            <div>
              <h2 className="h3">Committee Members</h2>
              <p className="text-muted text-sm">{members.length} member account{members.length === 1 ? '' : 's'}</p>
            </div>
          </div>
        </div>
        {members.length === 0 ? (
          <p className="text-muted text-sm">No Core Committee members have been added yet.</p>
        ) : (
          <div className="table-container">
            <table>
              <thead><tr><th>Name</th><th>Login ID</th><th>Email</th><th>Department Heads</th><th>Account</th><th>Action</th></tr></thead>
              <tbody>
                {members.map(member => (
                  <tr key={member.id}>
                    <td style={{ fontWeight: 600 }}>{member.full_name}</td>
                    <td>{member.login_id}</td>
                    <td>{member.email}</td>
                    <td>{member.department_head_count || 0}</td>
                    <td><Badge type={member.status === 'active' ? 'success' : 'critical'}>{member.status}</Badge></td>
                    <td><button type="button" className="btn btn-secondary btn-sm" onClick={() => { setPasswordTarget(member); setNewPassword(''); setPasswordError(''); }}><KeyRound size={14} />Reset Password</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Modal
        isOpen={Boolean(passwordTarget)}
        onClose={() => setPasswordTarget(null)}
        title="Reset Core Committee Password"
      >
        {passwordTarget && (
          <form onSubmit={handleSetMemberPassword}>
            <p className="text-muted text-sm" style={{ marginBottom: '16px' }}>
              Set a new password for {passwordTarget.full_name} ({passwordTarget.login_id}) to use with {SHARED_CORE_LOGIN_EMAIL}. Choose a password not used by another Core Committee member.
            </p>
            {passwordError && <div className="banner banner-danger" role="alert" style={{ marginBottom: '16px' }}><AlertCircle size={16} /><span>{passwordError}</span></div>}
            <div className="form-group">
              <label className="form-label" htmlFor="core-password-reset">New password</label>
              <input id="core-password-reset" type="password" className="form-input" value={newPassword} onChange={event => setNewPassword(event.target.value)} minLength={8} autoComplete="new-password" required />
            </div>
            <p className="text-muted text-sm">Only a secure hash is saved. Organizers cannot view this password later; reset it if it is forgotten.</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setPasswordTarget(null)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={passwordSaving}>{passwordSaving ? 'Saving...' : 'Save Password'}</button>
            </div>
          </form>
        )}
      </Modal>

      <section className="card">
        <div className="card-header" style={{ alignItems: 'flex-end' }}>
          <div>
            <h2 className="h3">Assign Department Heads</h2>
          <p className="text-muted text-sm">Assign heads as soon as an event is upcoming; a published volunteer roster is not required. Choose one active member per department.</p>
          </div>
          {events.length > 0 && (
            <div style={{ minWidth: '230px' }}>
              <label className="form-label" htmlFor="core-head-event">Published event</label>
              <select id="core-head-event" className="form-select" value={selectedEventId} onChange={event => { setSelectedEventId(event.target.value); setError(''); setSuccess(''); }}>
                {events.map(event => <option key={event.id} value={event.id}>{event.name}</option>)}
              </select>
            </div>
          )}
        </div>

        {events.length === 0 ? (
          <div className="text-muted text-sm" style={{ padding: '12px 0' }}>There are no upcoming or ongoing events to assign heads for yet.</div>
        ) : members.length === 0 ? (
          <div className="text-muted text-sm" style={{ padding: '12px 0' }}>Add Core Committee member accounts above before assigning department heads.</div>
        ) : assignmentLoading ? (
          <div className="text-muted text-sm" style={{ padding: '16px 0' }}>Loading departments...</div>
        ) : departments.length === 0 ? (
          <div className="text-muted text-sm" style={{ padding: '12px 0' }}>This event has no department staffing requirements.</div>
        ) : (
          <>
            {(error || success) && (
              <div className={`banner ${error ? 'banner-danger' : 'banner-success'}`} role={error ? 'alert' : 'status'} style={{ marginBottom: '16px' }}>
                {error ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
                <span>{error || success}</span>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
              <p className="text-muted text-sm">Select a name beside each department, then save your assignments.</p>
              <span className="text-muted text-sm">{assignedHeadCount} of {departments.length} departments assigned</span>
            </div>
            <div className="table-container">
              <table>
                <thead><tr><th>Department</th><th>Assigned Volunteers</th><th>Choose Department Head</th></tr></thead>
                <tbody>
                  {departments.map(department => (
                    <tr key={department.department_id}>
                      <td style={{ fontWeight: 600 }}>{department.department_name}</td>
                      <td>{department.volunteer_count}</td>
                      <td>
                        <select
                          className="form-select"
                          aria-label={`Department head for ${department.department_name}`}
                          value={selectedHeads[String(department.department_id)] || ''}
                          disabled={saving || assignmentLoading}
                          onChange={event => {
                            const selectedUserId = event.target.value;
                            setError('');
                            setSelectedHeads(current => ({ ...current, [String(department.department_id)]: selectedUserId }));
                          }}
                        >
                          <option value="">Unassigned — choose a member</option>
                          {activeMembers.map(member => {
                            const memberId = String(member.id);
                            const assignedToOtherDepartment = departments.some(otherDepartment => (
                              otherDepartment.department_id !== department.department_id
                              && selectedHeads[String(otherDepartment.department_id)] === memberId
                            ));
                            return (
                              <option key={member.id} value={member.id} disabled={assignedToOtherDepartment}>
                                {member.full_name} · {member.login_id}{assignedToOtherDepartment ? ' — assigned to another department' : ''}
                              </option>
                            );
                          })}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button type="button" className="btn btn-primary" onClick={handleSaveHeads} disabled={saving || assignmentLoading || activeMembers.length === 0}>
                <Save size={15} />{saving ? 'Saving...' : 'Save Assignments'}
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
