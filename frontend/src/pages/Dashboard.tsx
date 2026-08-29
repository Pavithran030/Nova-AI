import { useEffect, useState } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title } from 'chart.js';
import { Doughnut, Line } from 'react-chartjs-2';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import { api } from '../services/api';
import type { ReportSummary } from '../types';
import './Dashboard.css';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title);

const DONUT_COLORS = ['#3B6CF5', '#12875A', '#C77A13', '#D13438', '#5E6678', '#9CA3B0', '#1B2330', '#E2E5EA'];

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
};

const Dashboard = () => {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDashboardSummary()
      .then(setSummary)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="dashboard"><div className="page-header"><h1>Overview</h1></div><p>Loading…</p></div>;
  }

  if (!summary) {
    return <div className="dashboard"><div className="page-header"><h1>Overview</h1></div><p>Could not load dashboard data.</p></div>;
  }

  const rootCauseEntries = Object.entries(summary.by_root_cause);
  const hasData = rootCauseEntries.length > 0;

  const donutData = {
    labels: rootCauseEntries.map(([cause]) => cause),
    datasets: [
      {
        data: rootCauseEntries.map(([, data]) => data.count),
        backgroundColor: DONUT_COLORS,
        borderWidth: 0,
      },
    ],
  };

  const donutOptions = {
    cutout: '75%',
    plugins: {
      legend: { position: 'right' as const, labels: { boxWidth: 12, usePointStyle: true, font: { family: 'Inter' } } },
    },
  };

  const lineData = {
    labels: summary.trend.map(t => t.date),
    datasets: [
      { label: 'At-Risk Revenue', data: summary.trend.map(t => t.at_risk), borderColor: '#C77A13', backgroundColor: '#FEF3E2', tension: 0.4 },
      { label: 'Recovered Revenue', data: summary.trend.map(t => t.recovered), borderColor: '#12875A', backgroundColor: '#E8F5EF', tension: 0.4 },
    ],
  };

  const lineOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' as const, labels: { font: { family: 'Inter' } } } },
    scales: {
      y: { beginAtZero: true, grid: { color: '#E2E5EA' } },
      x: { grid: { display: false } },
    },
  };

  return (
    <div className="dashboard">
      <div className="page-header">
        <h1>Overview</h1>
      </div>

      <div className="metrics-grid">
        <MetricCard title="Total At-Risk Revenue" value={formatCurrency(summary.total_at_risk)} />
        <MetricCard title="Recovered Revenue" value={formatCurrency(summary.total_recovered)} highlight />
        <MetricCard title="Recovery Rate" value={`${summary.recovery_rate}%`} />
        <MetricCard title="Active Cases" value={String(summary.active_cases)} />
      </div>

      {!hasData ? (
        <div className="table-card">
          <p>No recovery activity yet. Run <code>python -m app.utils.generate_history</code> (or <code>POST /simulate/generate-batch</code>) against the backend, then reload.</p>
        </div>
      ) : (
        <>
          <div className="charts-grid">
            <div className="chart-card">
              <h3>Root Cause Distribution</h3>
              <div className="chart-container">
                <Doughnut data={donutData} options={donutOptions} />
              </div>
            </div>
            <div className="chart-card">
              <h3>Recovery Trend</h3>
              <div className="chart-container">
                <Line data={lineData} options={lineOptions} />
              </div>
            </div>
          </div>

          <div className="table-card">
            <h3>Recent Recovery Actions</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Transaction ID</th>
                  <th>Amount</th>
                  <th>Root Cause</th>
                  <th>Action</th>
                  <th>Channel</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {summary.recent_actions.map((action, idx) => (
                  <tr key={idx}>
                    <td>{action.timestamp ? new Date(action.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '—'}</td>
                    <td className="mono">{action.transaction_id}</td>
                    <td>{formatCurrency(action.amount)}</td>
                    <td>{action.root_cause ? <StatusBadge status={action.root_cause} type="cause" /> : '—'}</td>
                    <td>{action.action_type}</td>
                    <td>{action.channel ?? '—'}</td>
                    <td><StatusBadge status={action.outcome ?? 'pending'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;
