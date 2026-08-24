import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title } from 'chart.js';
import { Doughnut, Line } from 'react-chartjs-2';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import { mockTransactions } from '../data/mockData';
import './Dashboard.css';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title);

const Dashboard = () => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  const donutData = {
    labels: ['INSUFFICIENT_FUNDS', 'BANK_TIMEOUT', 'CARD_EXPIRED', 'MANDATE_REVOKED', 'NETWORK_ERROR', 'RISK_DECLINE', 'ABANDONMENT', 'OVERDUE'],
    datasets: [
      {
        data: [32, 22, 15, 10, 8, 5, 5, 3],
        backgroundColor: [
          '#3B6CF5', '#12875A', '#C77A13', '#D13438', '#5E6678', '#9CA3B0', '#1B2330', '#E2E5EA'
        ],
        borderWidth: 0,
      },
    ],
  };

  const donutOptions = {
    cutout: '75%',
    plugins: {
      legend: { position: 'right' as const, labels: { boxWidth: 12, usePointStyle: true, font: { family: 'Inter' } } }
    }
  };

  const lineData = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      {
        label: 'At-Risk Revenue',
        data: [150, 180, 120, 200, 250, 170, 140],
        borderColor: '#C77A13',
        backgroundColor: '#FEF3E2',
        tension: 0.4,
      },
      {
        label: 'Recovered Revenue',
        data: [100, 140, 90, 150, 200, 130, 110],
        borderColor: '#12875A',
        backgroundColor: '#E8F5EF',
        tension: 0.4,
      }
    ]
  };

  const lineOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' as const, labels: { font: { family: 'Inter' } } } },
    scales: {
      y: { beginAtZero: true, grid: { color: '#E2E5EA' } },
      x: { grid: { display: false } }
    }
  };

  return (
    <div className="dashboard">
      <div className="page-header">
        <h1>Overview</h1>
      </div>

      <div className="metrics-grid">
        <MetricCard title="Total At-Risk Revenue" value={formatCurrency(1245000)} trend="12% vs last week" trendDirection="up" />
        <MetricCard title="Recovered Revenue" value={formatCurrency(875000)} highlight />
        <MetricCard title="Recovery Rate" value="70.2%" trend="4.5% vs baseline" trendDirection="up" />
        <MetricCard title="Active Cases" value="47" />
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Root Cause Distribution</h3>
          <div className="chart-container">
            <Doughnut data={donutData} options={donutOptions} />
          </div>
        </div>
        <div className="chart-card">
          <h3>Recovery Trend (Last 7 Days)</h3>
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
            {mockTransactions.map((txn) => (
              <tr key={txn.id}>
                <td>{new Date(txn.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</td>
                <td className="mono">{txn.id}</td>
                <td>{formatCurrency(txn.amount)}</td>
                <td><StatusBadge status={txn.rootCause} type="cause" /></td>
                <td>{txn.action}</td>
                <td>{txn.channel}</td>
                <td><StatusBadge status={txn.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Dashboard;
