import { mockAudit } from '../data/mockData';
import StatusBadge from '../components/StatusBadge';
import './AuditTrail.css';

const AuditTrail = () => {
  return (
    <div className="audit-trail">
      <div className="page-header">
        <h1>Audit Trail</h1>
      </div>

      <div className="audit-controls">
        <input type="text" className="search-input" placeholder="Search entity ID, action..." />
        <div className="filters">
          <select className="filter-select">
            <option>All Entity Types</option>
            <option>Payment</option>
            <option>Invoice</option>
            <option>Subscription</option>
          </select>
          <select className="filter-select">
            <option>Last 7 Days</option>
            <option>Last 30 Days</option>
          </select>
        </div>
      </div>

      <div className="table-card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Entity Type</th>
              <th>Entity ID</th>
              <th>Action Type</th>
              <th>Channel</th>
              <th>Actor</th>
              <th>NPCI Window</th>
              <th>Attempt #</th>
              <th>Reasoning</th>
            </tr>
          </thead>
          <tbody>
            {mockAudit.map((entry, idx) => (
              <tr key={idx} className="clickable-row">
                <td>{new Date(entry.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                <td>{entry.entityType}</td>
                <td className="mono">{entry.entityId}</td>
                <td>{entry.actionType}</td>
                <td>{entry.channel}</td>
                <td>
                  <span className={`actor-badge ${entry.actor === 'agent' ? 'actor-agent' : 'actor-human'}`}>
                    {entry.actor === 'agent' ? '🤖 Agent' : '👤 Human'}
                  </span>
                </td>
                <td>
                  {entry.npciWindow ? <span className="npci-valid">Valid</span> : <span className="npci-invalid">Outside Window</span>}
                </td>
                <td>{entry.attempt}</td>
                <td className="reasoning-cell" title={entry.reasoning}>{entry.reasoning}</td>
              </tr>
            ))}
          </tbody>
        </table>
        
        <div className="pagination">
          <button className="page-btn disabled">Previous</button>
          <span className="page-info">Page 1 of 5</span>
          <button className="page-btn">Next</button>
        </div>
      </div>
    </div>
  );
};

export default AuditTrail;
