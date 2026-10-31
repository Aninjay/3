import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { Search, Plus, UserCheck, UserX, AlertCircle, KeyRound, CheckCircle2 } from 'lucide-react';

const SHARED_VOLUNTEER_LOGIN_EMAIL = 'volunteer@tapmi.edu.in';

export function VolunteersPage() {
  const [volunteers, setVolunteers] = useState([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);

  // New Volunteer Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [fullName, setFullName] = useState('');
  const [studentId, setStudentId] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [passwordTarget, setPasswordTarget] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [actionNotice, setActionNotice] = useState('');

  async function getVolunteers(searchValue = search, statusValue = statusFilter) {
    const params = {};
    const query = searchValue.trim();
    if (query) params.search = query;
    if (statusValue) params.status = statusValue;
    const res = await api.getVolunteers(params);
    return res.data || [];
  }

  async function loadVolunteers() {
    setLoading(true);
    try {
      setVolunteers(await getVolunteers());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let current = true;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const results = await getVolunteers(search, statusFilter);
        if (current) setVolunteers(results);
      } catch (err) {
        if (current) console.error(err);
      } finally {
        if (current) setLoading(false);
      }
    }, 180);

    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [search, statusFilter]);

  async function handleToggleStatus(vol) {
    const nextStatus = !vol.active_status;
    const actionText = nextStatus ? 'activate' : 'deactivate';
    if (!confirm(`Are you sure you want to ${actionText} volunteer ${vol.full_name} (${vol.student_id})? Inactive volunteers cannot be assigned to events.`)) {
      return;
    }

    try {
      await api.updateVolunteer(vol.id, {
        active_status: nextStatus,
        reason: `Organizer manual ${actionText}`
      });
      loadVolunteers();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleCreateVolunteer(e) {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);
    try {
      await api.createVolunteer({
        full_name: fullName,
        student_id: studentId,
        contact_email: contactEmail,
        password
      });
      setIsModalOpen(false);
      setFullName('');
      setStudentId('');
      setContactEmail('');
      setPassword('');
      loadVolunteers();
    } catch (err) {
      setFormError(err.message || 'Failed to register volunteer.');
    } finally {
      setSubmitting(false);
    }
  }

  function openPasswordModal(volunteer) {
    setPasswordTarget(volunteer);
    setNewPassword('');
    setPasswordError('');
    setActionNotice('');
  }

  async function handleSetPassword(e) {
    e.preventDefault();
    if (!passwordTarget) return;
    setPasswordError('');
    setPasswordSaving(true);
    try {
      await api.setVolunteerPassword(passwordTarget.id, newPassword);
      setActionNotice(`Password set for ${passwordTarget.full_name}. It is stored securely and cannot be viewed later.`);
      setPasswordTarget(null);
      setNewPassword('');
      await loadVolunteers();
    } catch (err) {
      setPasswordError(err.message || 'Could not set the volunteer password.');
    } finally {
      setPasswordSaving(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="h1">Volunteers Roster</h1>
          <p className="text-muted" style={{ marginTop: '4px' }}>
            Showing {volunteers.length} matching volunteer records
          </p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
          <Plus size={16} />
          <span>Register Volunteer</span>
        </button>
      </div>

      {actionNotice && (
        <div className="banner banner-success" role="status" style={{ marginBottom: '16px' }}>
          <CheckCircle2 size={16} /><span>{actionNotice}</span>
        </div>
      )}

      {/* Filter & Search Bar */}
      <div className="card" style={{ padding: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={16} aria-hidden="true" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-muted)' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '38px' }}
              aria-label="Search names, interviewers, skills, student IDs, or email"
              placeholder="Search names, interviewer, skills, ID, or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="form-select"
            style={{ width: '160px' }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
            <option value="pending">Pending Activation</option>
          </select>
        </div>
      </div>

      {/* Volunteers Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Volunteer</th>
              <th>Student ID</th>
              <th>Approved Skills</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-muted)' }}>
                  Loading volunteers...
                </td>
              </tr>
            ) : volunteers.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-muted)' }}>
                  No volunteers matched the query.
                </td>
              </tr>
            ) : (
              volunteers.map((v) => (
                <tr key={v.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{v.full_name}</div>
                    <div className="text-muted text-sm">{v.email}</div>
                    {v.interviewed_by && <div className="text-muted text-sm">Interviewed by {v.interviewed_by}</div>}
                  </td>
                  <td>
                    <code style={{ fontSize: '13px', fontWeight: 600 }}>{v.student_id}</code>
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxWidth: '420px' }}>
                      {v.skills?.map((sk, i) => (
                        <span key={i} style={{ backgroundColor: 'var(--color-subtle)', border: '1px solid var(--color-border)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' }}>
                          {sk.name}
                        </span>
                      ))}
                      {(!v.skills || v.skills.length === 0) && (
                        <span className="text-muted text-sm">No skills recorded</span>
                      )}
                    </div>
                  </td>
                  <td>
                    {v.active_status ? (
                      <Badge type="success">Active</Badge>
                    ) : (
                      <Badge type="critical">Inactive</Badge>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '142px' }}>
                      <button type="button" onClick={() => openPasswordModal(v)} className="btn btn-secondary btn-sm">
                        <KeyRound size={14} />{v.account_status ? 'Reset Password' : 'Set Password'}
                      </button>
                      <button
                        onClick={() => handleToggleStatus(v)}
                        className="btn btn-secondary btn-sm"
                      >
                        {v.active_status ? 'Deactivate' : 'Activate'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Register Volunteer Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Register Volunteer Record"
      >
        {formError && (
          <div className="banner banner-danger">
            <AlertCircle size={16} />
            <span>{formError}</span>
          </div>
        )}
        <form onSubmit={handleCreateVolunteer}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Rahul Sharma"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">University Student ID (Unique)</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. V101"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Shared Volunteer Login Email</label>
            <input
              type="email"
              className="form-input"
              value={SHARED_VOLUNTEER_LOGIN_EMAIL}
              readOnly
            />
            <span className="text-muted text-sm">Every volunteer signs in with this email and their own distinct password.</span>
          </div>

          <div className="form-group">
            <label className="form-label">Personal Contact Email (Optional)</label>
            <input
              type="email"
              className="form-input"
              placeholder="e.g. volunteer's personal email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Create Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
            <span className="text-muted text-sm">Use a different password for every account using the shared email.</span>
          </div>

          <p className="text-muted text-sm" style={{ marginTop: '12px' }}>
            The student ID is the volunteer’s unique login ID. The contact email can be shared by multiple people.
          </p>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsModalOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting ? 'Registering...' : 'Register Volunteer'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={Boolean(passwordTarget)}
        onClose={() => setPasswordTarget(null)}
        title={passwordTarget?.account_status ? 'Reset Volunteer Password' : 'Set Volunteer Password'}
      >
        {passwordTarget && (
          <form onSubmit={handleSetPassword}>
            <p className="text-muted text-sm" style={{ marginBottom: '16px' }}>
              Set a password for {passwordTarget.full_name} ({passwordTarget.student_id}) to use with {SHARED_VOLUNTEER_LOGIN_EMAIL}. Choose a password not used by another volunteer.
            </p>
            {passwordError && (
              <div className="banner banner-danger" role="alert" style={{ marginBottom: '16px' }}>
                <AlertCircle size={16} /><span>{passwordError}</span>
              </div>
            )}
            <div className="form-group">
              <label className="form-label" htmlFor="volunteer-password-reset">New password</label>
              <input
                id="volunteer-password-reset"
                type="password"
                className="form-input"
                value={newPassword}
                onChange={event => setNewPassword(event.target.value)}
                minLength={8}
                autoComplete="new-password"
                required
              />
            </div>
            <p className="text-muted text-sm">Only a secure hash is saved. Organizers cannot view this password later; set a new one if it is forgotten.</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setPasswordTarget(null)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={passwordSaving}>
                {passwordSaving ? 'Saving...' : 'Save Password'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
