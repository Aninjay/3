import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { Award, Plus, CheckCircle2, XCircle } from 'lucide-react';

export function SkillsPage() {
  const [skills, setSkills] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Suggest Skill Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [skillName, setSkillName] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const skRes = await api.getSkills();
      setSkills(skRes.data || []);
      const sugRes = await api.getSuggestions();
      setSuggestions(sugRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleApprove(id) {
    try {
      await api.approveSuggestion(id);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleReject(id) {
    const reason = prompt("Enter rejection reason:");
    if (!reason) return;
    try {
      await api.rejectSuggestion(id, reason);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleSuggestSkill(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.suggestSkill({ name: skillName, description });
      setIsModalOpen(false);
      setSkillName('');
      setDescription('');
      loadData();
      alert("Skill suggestion submitted!");
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="h1">Skills Catalog</h1>
          <p className="text-muted" style={{ marginTop: '4px' }}>
            Standardized volunteer capability taxonomy ({skills.length} approved skills)
          </p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
          <Plus size={16} />
          <span>Suggest New Skill</span>
        </button>
      </div>

      {/* Pending Suggestions Section */}
      {suggestions.length > 0 && (
        <div className="card" style={{ marginBottom: '24px', borderLeft: '4px solid var(--color-warning)' }}>
          <div className="card-header">
            <h3 className="h3">Pending Volunteer Suggestions ({suggestions.length})</h3>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Suggested Skill</th>
                  <th>Description</th>
                  <th>Submitted By</th>
                  <th>Review Actions</th>
                </tr>
              </thead>
              <tbody>
                {suggestions.map((sug) => (
                  <tr key={sug.id}>
                    <td style={{ fontWeight: 600 }}>{sug.name}</td>
                    <td className="text-muted text-sm">{sug.description || 'No description provided'}</td>
                    <td className="text-muted text-sm">{sug.suggested_by_email || 'Volunteer'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          onClick={() => handleApprove(sug.id)}
                          className="btn btn-primary btn-sm"
                        >
                          <CheckCircle2 size={13} />
                          <span>Approve</span>
                        </button>
                        <button
                          onClick={() => handleReject(sug.id)}
                          className="btn btn-secondary btn-sm"
                          style={{ color: 'var(--color-danger)' }}
                        >
                          <XCircle size={13} />
                          <span>Reject</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Approved Catalog Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="h3">Approved Standard Catalog</h3>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Skill Name</th>
                <th>Description</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {skills.map((sk) => (
                <tr key={sk.id}>
                  <td style={{ fontWeight: 600, color: 'var(--color-text)' }}>
                    {sk.name}
                  </td>
                  <td className="text-muted text-sm">
                    {sk.description || 'Standard verified capability'}
                  </td>
                  <td>
                    <Badge type="success">Approved</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Suggest Skill Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Suggest New Skill for Catalog"
      >
        <form onSubmit={handleSuggestSkill}>
          <div className="form-group">
            <label className="form-label">Skill Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Drone Videography"
              value={skillName}
              onChange={(e) => setSkillName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description & Application</label>
            <textarea
              className="form-textarea"
              placeholder="Describe what tasks this skill covers..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

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
              {submitting ? 'Submitting...' : 'Submit Suggestion'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
