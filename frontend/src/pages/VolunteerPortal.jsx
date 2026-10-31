import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { Calendar, MapPin, CheckCircle2, Clock, Plus } from 'lucide-react';

export function VolunteerPortal({ activeTab = 'my-assignments' }) {
  const [assignments, setAssignments] = useState([]);
  const [history, setHistory] = useState([]);
  const [mySkills, setMySkills] = useState([]);
  const [allSkills, setAllSkills] = useState([]);
  const [selectedSkillIds, setSelectedSkillIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [savingSkills, setSavingSkills] = useState(false);
  const [skillSuccess, setSkillSuccess] = useState('');

  // Suggest skill modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [suggestName, setSuggestName] = useState('');
  const [suggestDesc, setSuggestDesc] = useState('');

  async function loadData() {
    setLoading(true);
    try {
      const assnRes = await api.getMyAssignments();
      setAssignments(assnRes.data || []);

      const histRes = await api.getMyAssignmentHistory();
      setHistory(histRes.data || []);

      const skRes = await api.getMySkills();
      setMySkills(skRes.data || []);
      setSelectedSkillIds(new Set((skRes.data || []).map(s => s.id)));

      const catalogRes = await api.getSkills();
      setAllSkills(catalogRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function toggleSkill(id) {
    const next = new Set(selectedSkillIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedSkillIds(next);
  }

  async function handleSaveSkills() {
    setSavingSkills(true);
    setSkillSuccess('');
    try {
      await api.updateMySkills(Array.from(selectedSkillIds));
      setSkillSuccess('Your skills were successfully updated in your profile!');
      const updated = await api.getMySkills();
      setMySkills(updated.data || []);
    } catch (err) {
      alert(err.message || 'Failed to update skills.');
    } finally {
      setSavingSkills(false);
    }
  }

  async function handleSuggestSkill(e) {
    e.preventDefault();
    try {
      await api.suggestSkill({ name: suggestName, description: suggestDesc });
      setIsModalOpen(false);
      setSuggestName('');
      setSuggestDesc('');
      alert('Skill suggestion submitted for organizer approval!');
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1 className="h1">Volunteer Portal</h1>
        <p className="text-muted" style={{ marginTop: '4px' }}>
          Personal published event assignments and verified capability profile
        </p>
      </div>

      {/* TAB 1: MY PUBLISHED ASSIGNMENTS */}
      {activeTab === 'my-assignments' && (
        <div>
          {assignments.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '40px 20px' }}>
              <Clock size={32} color="var(--color-muted)" style={{ margin: '0 auto 12px' }} />
              <h3 className="h3">No Published Assignments Yet</h3>
              <p className="text-muted text-sm" style={{ maxWidth: '400px', margin: '6px auto 0' }}>
                Assignments will appear here once the Convener or Co-convener reviews, approves, and officially publishes the event roster.
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
              {assignments.map((a) => (
                <div key={a.assignment_id} className="card" style={{ borderLeft: '4px solid var(--color-primary)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <h3 className="h3">{a.event_name}</h3>
                    <Badge type="success">Published</Badge>
                  </div>

                  <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-primary-hover)', marginBottom: '4px' }}>
                    {a.department_name} — {a.role_name}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px', color: 'var(--color-muted)', marginTop: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <MapPin size={14} />
                      <span>{a.venue}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Calendar size={14} />
                      <span>{new Date(a.starts_at).toLocaleDateString()} · {new Date(a.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: MY SKILLS */}
      {activeTab === 'my-skills' && (
        <div>
          <div className="card" style={{ marginBottom: '24px' }}>
            <div className="card-header">
              <div>
                <h3 className="h3">Manage Your Verified Skills</h3>
                <p className="text-muted text-sm">
                  Select your capabilities from the approved Cultural Committee catalog. These are used during automatic allocation.
                </p>
              </div>
              <button onClick={() => setIsModalOpen(true)} className="btn btn-secondary btn-sm">
                <Plus size={14} />
                <span>Suggest Other Skill</span>
              </button>
            </div>

            {skillSuccess && (
              <div className="banner banner-success" style={{ marginBottom: '16px' }}>
                <CheckCircle2 size={16} />
                <span>{skillSuccess}</span>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '10px', marginBottom: '24px' }}>
              {allSkills.map((sk) => {
                const isSelected = selectedSkillIds.has(sk.id);
                return (
                  <div
                    key={sk.id}
                    onClick={() => toggleSkill(sk.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '10px 14px',
                      borderRadius: 'var(--radius-md)',
                      border: isSelected ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                      backgroundColor: isSelected ? 'var(--color-primary-soft)' : '#FFFFFF',
                      cursor: 'pointer',
                      userSelect: 'none',
                      transition: 'all 0.1s ease'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      style={{ accentColor: 'var(--color-primary)', cursor: 'pointer' }}
                    />
                    <div>
                      <div style={{ fontWeight: 500, fontSize: '13.5px', color: isSelected ? 'var(--color-primary-hover)' : 'var(--color-text)' }}>
                        {sk.name}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={handleSaveSkills}
                className="btn btn-primary"
                disabled={savingSkills}
              >
                {savingSkills ? 'Saving...' : 'Save My Skills'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: ASSIGNMENT HISTORY */}
      {activeTab === 'my-history' && (
        <div className="card">
          <div className="card-header">
            <h3 className="h3">Past Cultural Event History</h3>
          </div>
          {history.length === 0 ? (
            <p className="text-muted text-sm" style={{ padding: '20px 0' }}>No past event assignment records found.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Department</th>
                    <th>Role</th>
                    <th>Dates</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.assignment_id}>
                      <td style={{ fontWeight: 600 }}>{h.event_name}</td>
                      <td>{h.department_name}</td>
                      <td>{h.role_name}</td>
                      <td className="text-muted text-sm">{new Date(h.starts_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Suggest Skill Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Suggest Skill to Cultural Committee"
      >
        <form onSubmit={handleSuggestSkill}>
          <div className="form-group">
            <label className="form-label">Skill Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Classical Carnatic Vocals"
              value={suggestName}
              onChange={(e) => setSuggestName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Brief Description</label>
            <textarea
              className="form-textarea"
              placeholder="How this capability helps festival execution..."
              value={suggestDesc}
              onChange={(e) => setSuggestDesc(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancel</button>
            <button type="submit" className="btn btn-primary">Submit Suggestion</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
