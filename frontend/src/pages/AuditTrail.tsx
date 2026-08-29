import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { AuditLogEntry } from '../types';
import './AuditTrail.css';

const actorBadge = (actor: string) => {
  if (actor === 'agent') return { icon: '🤖', label: 'Agent', className: 'actor-agent' };
  if (actor === 'baseline') return { icon: '🧪', label: 'Baseline', className: 'actor-baseline' };
  return { icon: '👤', label: 'Human', className: 'actor-human' };
};

const AuditTrail = () => {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    setLoading(true);
    api.getAuditTrail(page)
      .then(res => {
        setEntries(res.items);
        setTotalPages(Math.max(1, res.total_pages));
      })
      .finally(() => setLoading(false));
  }, [page]);

  const filtered = entries.filter(e => {
    if (!search.trim()) return true;
    const needle = search.toLowerCase();
    return (
      e.entity_id.toLowerCase().includes(needle) ||
      e.action_type.toLowerCase().includes(needle) ||
      (e.reasoning ?? '').toLowerCase().includes(needle)
    );
  });

  return (
    <div className="audit-trail">
      <div className="page-header">
        <h1>Audit Trail</h1>
      </div>

      <div className="audit-controls">
        <input
          type="text"
          className="search-input"
          placeholder="Search entity ID, action..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className="table-card">
        {loading ? (
          <p>Loading…</p>
        ) : filtered.length === 0 ? (
          <p>No audit entries match. {entries.length === 0 && 'The audit log is empty — generate some data first.'}</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Entity Type</th>
                <th>Entity ID</th>
                <th>Action Type</th>
                <th>Actor</th>
                <th>NPCI Window</th>
                <th>Attempt #</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry) => {
                const badge = actorBadge(entry.actor);
                return (
                  <tr key={entry.id} className="clickable-row">
                    <td>{new Date(entry.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                    <td>{entry.entity_type}</td>
                    <td className="mono">{entry.entity_id}</td>
                    <td>{entry.action_type}</td>
                    <td>
                      <span className={`actor-badge ${badge.className}`}>
                        {badge.icon} {badge.label}
                      </span>
                    </td>
                    <td>
                      {entry.npci_window === 'valid' && <span className="npci-valid">Valid</span>}
                      {entry.npci_window === 'invalid' && <span className="npci-invalid">Outside Window</span>}
                      {!entry.npci_window && <span>—</span>}
                    </td>
                    <td>{entry.attempt_number ?? '—'}</td>
                    <td className="reasoning-cell" title={entry.reasoning ?? ''}>{entry.reasoning ?? '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        <div className="pagination">
          <button className={`page-btn ${page <= 1 ? 'disabled' : ''}`} disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>
            Previous
          </button>
          <span className="page-info">Page {page} of {totalPages}</span>
          <button className={`page-btn ${page >= totalPages ? 'disabled' : ''}`} disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuditTrail;
