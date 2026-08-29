import { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import type { QueueItem } from '../types';
import StatusBadge from '../components/StatusBadge';
import './RecoveryQueue.css';

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
};

const RecoveryQueue = () => {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'b2b' | 'b2c'>('all');
  const [rootCauseFilter, setRootCauseFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    api.getRecoveryQueue()
      .then(res => setItems(res.items))
      .finally(() => setLoading(false));
  }, []);

  const rootCauses = useMemo(
    () => Array.from(new Set(items.map(i => i.root_cause).filter((v): v is string => !!v))),
    [items]
  );
  const statuses = useMemo(
    () => Array.from(new Set(items.map(i => i.status))),
    [items]
  );

  const filtered = items.filter(item => {
    if (activeTab === 'b2b' && item.entity_type !== 'invoice') return false;
    if (activeTab === 'b2c' && item.entity_type !== 'transaction') return false;
    if (rootCauseFilter !== 'all' && item.root_cause !== rootCauseFilter) return false;
    if (statusFilter !== 'all' && item.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="recovery-queue">
      <div className="page-header">
        <h1>Recovery Queue</h1>
      </div>

      <div className="queue-controls">
        <div className="tabs">
          <button className={`tab ${activeTab === 'all' ? 'active' : ''}`} onClick={() => setActiveTab('all')}>All Entities</button>
          <button className={`tab ${activeTab === 'b2b' ? 'active' : ''}`} onClick={() => setActiveTab('b2b')}>B2B Invoices</button>
          <button className={`tab ${activeTab === 'b2c' ? 'active' : ''}`} onClick={() => setActiveTab('b2c')}>Consumer Transactions</button>
        </div>

        <div className="filters">
          <select className="filter-select" value={rootCauseFilter} onChange={e => setRootCauseFilter(e.target.value)}>
            <option value="all">All Root Causes</option>
            {rootCauses.map(rc => <option key={rc} value={rc}>{rc}</option>)}
          </select>
          <select className="filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="all">All Statuses</option>
            {statuses.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div className="table-card">
        {loading ? (
          <p>Loading…</p>
        ) : filtered.length === 0 ? (
          <p>No items match the current filters. {items.length === 0 && 'The recovery queue is empty — generate some data first.'}</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Entity Type</th>
                <th>Entity ID</th>
                <th>Amount</th>
                <th>Root Cause</th>
                <th>Confidence</th>
                <th>Next Action</th>
                <th>Expected Value</th>
                <th>Attempts</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, idx) => {
                const confidencePct = item.confidence != null ? Math.round(item.confidence * 100) : null;
                return (
                  <tr key={item.id} className="clickable-row">
                    <td><span className="priority-badge">#{idx + 1}</span></td>
                    <td>{item.entity_type}</td>
                    <td className="mono">{item.entity_id}</td>
                    <td>{formatCurrency(item.amount)}</td>
                    <td>{item.root_cause ? <StatusBadge status={item.root_cause} type="cause" /> : '—'}</td>
                    <td>
                      {confidencePct !== null ? (
                        <div className="confidence-cell">
                          <div className="confidence-bar-bg">
                            <div
                              className="confidence-bar-fill"
                              style={{
                                width: `${confidencePct}%`,
                                backgroundColor: confidencePct > 60 ? 'var(--color-success)' : confidencePct > 35 ? 'var(--color-warning)' : 'var(--color-danger)',
                              }}
                            />
                          </div>
                          <span>{confidencePct}%</span>
                        </div>
                      ) : '—'}
                    </td>
                    <td>{item.next_action ?? '—'}</td>
                    <td>{item.expected_recovery_value != null ? formatCurrency(item.expected_recovery_value) : '—'}</td>
                    <td>{item.attempt_count}/{item.max_attempts}</td>
                    <td><StatusBadge status={item.status} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default RecoveryQueue;
