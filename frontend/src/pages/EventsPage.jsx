import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { Plus, Calendar, MapPin, ArrowRight } from 'lucide-react';

export function EventsPage({ onSelectEvent }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // New Event Form State
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [startsAt, setStartsAt] = useState('2026-11-14T09:00');
  const [endsAt, setEndsAt] = useState('2026-11-15T22:00');
  const [venue, setVenue] = useState('TAPMI Campus Auditorium');
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function loadEvents() {
    setLoading(true);
    try {
      const res = await api.getEvents();
      setEvents(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEvents();
  }, []);

  async function handleCreateEvent(e) {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);
    try {
      await api.createEvent({
        name,
        description,
        starts_at: new Date(startsAt).toISOString(),
        ends_at: new Date(endsAt).toISOString(),
        venue
      });
      setIsModalOpen(false);
      setName('');
      setDescription('');
      loadEvents();
    } catch (err) {
      setFormError(err.message || 'Failed to create event.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="h1">Cultural Events</h1>
          <p className="text-muted" style={{ marginTop: '4px' }}>
            Event management, department staffing demand, and resource allocations
          </p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
          <Plus size={16} />
          <span>Create Event</span>
        </button>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Venue & Schedule</th>
              <th>Status</th>
              <th>Staffing Progress</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-muted)' }}>
                  Loading events...
                </td>
              </tr>
            ) : events.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-muted)' }}>
                  No events found. Click "Create Event" to begin.
                </td>
              </tr>
            ) : (
              events.map((ev) => (
                <tr key={ev.id}>
                  <td>
                    <div style={{ fontWeight: 600, fontSize: '15px' }}>{ev.name}</div>
                    <div className="text-muted text-sm" style={{ maxWidth: '380px', marginTop: '2px' }}>
                      {ev.description || 'No description provided.'}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                      <MapPin size={14} color="var(--color-muted)" />
                      <span>{ev.venue}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-muted)', marginTop: '4px' }}>
                      <Calendar size={13} />
                      <span>{new Date(ev.starts_at).toLocaleDateString()} – {new Date(ev.ends_at).toLocaleDateString()}</span>
                    </div>
                  </td>
                  <td>
                    <Badge type={ev.status}>{ev.status}</Badge>
                  </td>
                  <td>
                    <div style={{ fontSize: '13px' }}>
                      <span style={{ fontWeight: 600 }}>{ev.total_allocated || 0}</span>
                      <span className="text-muted"> / {ev.total_required || 0} filled</span>
                    </div>
                    <div className="text-muted text-sm">
                      {ev.published_version_id ? 'Published allocation active' : 'No published allocation'}
                    </div>
                  </td>
                  <td>
                    <button
                      onClick={() => onSelectEvent(ev.id)}
                      className="btn btn-outline btn-sm"
                    >
                      <span>Manage & Allocate</span>
                      <ArrowRight size={13} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Event Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create New Cultural Event"
      >
        {formError && (
          <div className="banner banner-danger">
            <span>{formError}</span>
          </div>
        )}
        <form onSubmit={handleCreateEvent}>
          <div className="form-group">
            <label className="form-label">Event Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Kala Fest 2026"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              placeholder="Overview of festival activities, department coordination..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Starts At</label>
              <input
                type="datetime-local"
                className="form-input"
                value={startsAt}
                onChange={(e) => setStartsAt(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Ends At</label>
              <input
                type="datetime-local"
                className="form-input"
                value={endsAt}
                onChange={(e) => setEndsAt(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Venue</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. TAPMI Main Auditorium & Campus Amphitheatre"
              value={venue}
              onChange={(e) => setVenue(e.target.value)}
              required
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
              {submitting ? 'Creating...' : 'Create Event'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
