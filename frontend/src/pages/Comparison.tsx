import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import MetricCard from '../components/MetricCard';
import './Comparison.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const Comparison = () => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  const barData = {
    labels: ['INSUFFICIENT_FUNDS', 'BANK_TIMEOUT', 'CARD_EXPIRED', 'MANDATE_REVOKED'],
    datasets: [
      {
        label: 'Baseline Rate (%)',
        data: [15, 45, 12, 8],
        backgroundColor: '#E2E5EA',
      },
      {
        label: 'Nova Rate (%)',
        data: [42, 85, 35, 25],
        backgroundColor: '#3B6CF5',
      },
    ],
  };

  const barOptions = {
    responsive: true,
    plugins: {
      legend: { position: 'top' as const, labels: { font: { family: 'Inter' } } },
    },
    scales: {
      y: { beginAtZero: true, max: 100, grid: { color: '#E2E5EA' } },
      x: { grid: { display: false } }
    }
  };

  return (
    <div className="comparison-page">
      <div className="page-header">
        <h1>Baseline vs Agent Comparison</h1>
      </div>

      <div className="headline-metrics">
        <div className="metric-box baseline">
          <div className="metric-label">Baseline Recovery</div>
          <div className="metric-value">{formatCurrency(450000)}</div>
          <div className="metric-sub">36.0% Recovery Rate</div>
        </div>
        <div className="metric-box nova">
          <div className="metric-label">Nova Agent Recovery</div>
          <div className="metric-value">{formatCurrency(875000)}</div>
          <div className="metric-sub">70.2% Recovery Rate</div>
        </div>
        <div className="metric-box delta">
          <div className="metric-label">Net Value Added</div>
          <div className="metric-value">+{formatCurrency(425000)}</div>
          <div className="metric-sub delta-text">↑ 34.2% Absolute Increase</div>
        </div>
      </div>

      <div className="metrics-grid">
        <MetricCard title="NPCI Window Violations" value="0" trend="vs 12 Baseline" trendDirection="up" highlight />
        <MetricCard title="Wasted Retries" value="0" trend="vs 18 Baseline" trendDirection="up" />
        <MetricCard title="Avg Days to Recovery (B2B)" value="7.8" trend="vs 15.2 Baseline" trendDirection="up" />
        <MetricCard title="Recovery Rate Delta" value="+34.0%" highlight />
      </div>

      <div className="comparison-layout">
        <div className="chart-card flex-2">
          <h3>Recovery Rate by Root Cause</h3>
          <div className="chart-container">
            <Bar data={barData} options={barOptions} />
          </div>
        </div>

        <div className="table-card flex-3">
          <h3>Detailed Performance Breakdown</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Baseline</th>
                <th>Nova</th>
                <th>Improvement</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>INSUFFICIENT_FUNDS</td>
                <td>15%</td>
                <td>42%</td>
                <td className="success-text">+27%</td>
              </tr>
              <tr>
                <td>BANK_TIMEOUT</td>
                <td>45%</td>
                <td>85%</td>
                <td className="success-text">+40%</td>
              </tr>
              <tr>
                <td>CARD_EXPIRED</td>
                <td>12%</td>
                <td>35%</td>
                <td className="success-text">+23%</td>
              </tr>
              <tr>
                <td>MANDATE_REVOKED</td>
                <td>8%</td>
                <td>25%</td>
                <td className="success-text">+17%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Comparison;
