import { useState } from 'react';
import { mockQueue } from '../data/mockData';
import StatusBadge from '../components/StatusBadge';
import './RecoveryQueue.css';

const RecoveryQueue = () => {
  const [activeTab, setActiveTab] = useState('all');

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  return (
    <div className="recovery-queue">
      <div className="page-header">
        <h1>Recovery Queue</h1>
      </div>

      <div className="queue-controls">
        <div className="tabs">
          <button className={`tab ${activeTab === 'all' ? 'active' : ''}`} onClick={() => setActiveTab('all')}>All Entities</button>
          <button className={`tab ${activeTab === 'b2b' ? 'active' : ''}`} onClick={() => setActiveTab('b2b')}>B2B Invoices</button>
          <button className={`tab ${activeTab === 'b2c' ? 'active' : ''}`} onClick={() => setActiveTab('b2c')}>Consumer Subscriptions</button>
        </div>
        
        <div className="filters">
          <select className="filter-select">
            <option>All Root Causes</option>
            <option>BANK_TIMEOUT</option>
            <option>INSUFFICIENT_FUNDS</option>
            <option>MANDATE_REVOKED</option>
          </select>
          <select className="filter-select">
            <option>All Statuses</option>
            <option>Pending</option>
            <option>In Progress</option>
          </select>
        </div>
      </div>

      <div className="table-card">
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
              <th>Scheduled For</th>
              <th>Attempts</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {mockQueue.map((item, idx) => (
              <tr key={idx} className="clickable-row">
                <td><span className="priority-badge">#{item.priority}</span></td>
                <td>{item.entityType}</td>
                <td className="mono">{item.entityId}</td>
                <td>{formatCurrency(item.amount)}</td>
                <td><StatusBadge status={item.rootCause} type="cause" /></td>
                <td>
                  <div className="confidence-cell">
                    <div className="confidence-bar-bg">
                      <div className="confidence-bar-fill" style={{ width: `${item.confidence}%`, backgroundColor: item.confidence > 80 ? 'var(--color-success)' : item.confidence > 50 ? 'var(--color-warning)' : 'var(--color-danger)' }}></div>
                    </div>
                    <span>{item.confidence}%</span>
                  </div>
                </td>
                <td>{item.nextAction}</td>
                <td>{item.scheduledFor}</td>
                <td>{item.attempts}/4</td>
                <td><StatusBadge status={item.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RecoveryQueue;
