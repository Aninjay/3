import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ShieldCheck, Search } from 'lucide-react';

export function AuditLogPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function loadLogs() {
      setLoading(true);
      try {
        const res = await api.getAuditLog();
        setLogs(res.data || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadLogs();
  }, []);

  const filteredLogs = logs.filter(l => 
    !search || 
    l.action?.toLowerCase().includes(search.toLowerCase()) ||
    l.actor_email?.toLowerCase().includes(search.toLowerCase()) ||
    l.reason?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="h1">Audit & Decision History</h1>
          <p className="text-muted" style={{ marginTop: '4px' }}>
            Immutable record of manual allocation changes, skill overrides, approvals, and publications
          </p>
        </div>
      </div>

      <div className="card" style={{ padding: '14px', marginBottom: '20px' }}>
        <input
          type="text"
          className="form-input"
          placeholder="Filter audit records by actor email, action type, or override reason..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target Entity</th>
              <th>Reason & Decision Evidence</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-muted)' }}>
                  Loading audit trail...
                </td>
              </tr>
            ) : filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-muted)' }}>
                  No audit entries found.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => (
                <tr key={log.id}>
                  <td className="text-muted text-sm">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td style={{ fontWeight: 500 }}>
                    {log.actor_email || 'System'}
                  </td>
                  <td>
                    <code style={{ fontSize: '12px', color: 'var(--color-primary-hover)', fontWeight: 600 }}>
                      {log.action}
                    </code>
                  </td>
                  <td className="text-muted text-sm">
                    {log.entity_type} #{log.entity_id || '—'}
                  </td>
                  <td style={{ fontSize: '13px' }}>
                    {log.reason || log.after_data || '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
