import { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import MetricCard from '../components/MetricCard';
import { api } from '../services/api';
import type { BaselineComparisonResponse } from '../types';
import './Comparison.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
};

const Comparison = () => {
  const [data, setData] = useState<BaselineComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getBaselineComparison().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="comparison-page"><div className="page-header"><h1>Baseline vs Agent Comparison</h1></div><p>Loading…</p></div>;
  if (!data) return <div className="comparison-page"><div className="page-header"><h1>Baseline vs Agent Comparison</h1></div><p>Could not load comparison data.</p></div>;

  const rootCauses = Array.from(new Set([
    ...Object.keys(data.baseline.by_root_cause),
    ...Object.keys(data.agent.by_root_cause),
  ]));

  const barData = {
    labels: rootCauses,
    datasets: [
      { label: 'Baseline Rate (%)', data: rootCauses.map(rc => data.baseline.by_root_cause[rc]?.rate ?? 0), backgroundColor: '#E2E5EA' },
      { label: 'Nova Rate (%)', data: rootCauses.map(rc => data.agent.by_root_cause[rc]?.rate ?? 0), backgroundColor: '#3B6CF5' },
    ],
  };

  const barOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' as const, labels: { font: { family: 'Inter' } } } },
    scales: {
      y: { beginAtZero: true, max: 100, grid: { color: '#E2E5EA' } },
      x: { grid: { display: false } },
    },
  };

  return (
    <div className="comparison-page">
      <div className="page-header">
        <h1>Baseline vs Agent Comparison</h1>
      </div>

      <div className="headline-metrics">
        <div className="metric-box baseline">
          <div className="metric-label">Baseline Recovery</div>
          <div className="metric-value">{formatCurrency(data.baseline.total_recovered)}</div>
          <div className="metric-sub">{data.baseline.recovery_rate}% Recovery Rate</div>
        </div>
        <div className="metric-box nova">
          <div className="metric-label">Nova Agent Recovery</div>
          <div className="metric-value">{formatCurrency(data.agent.total_recovered)}</div>
          <div className="metric-sub">{data.agent.recovery_rate}% Recovery Rate</div>
        </div>
        <div className="metric-box delta">
          <div className="metric-label">Net Value Added</div>
          <div className="metric-value">+{formatCurrency(data.delta.revenue_delta)}</div>
          <div className="metric-sub delta-text">↑ {data.delta.rate_delta}% Absolute Increase</div>
        </div>
      </div>

      <div className="metrics-grid">
        <MetricCard title="NPCI Window Violations" value={String(data.agent.retries_outside_window)} trend={`vs ${data.baseline.retries_outside_window} Baseline`} trendDirection="up" highlight />
        <MetricCard title="Wasted Retries" value={String(data.agent.wasted_attempts)} trend={`vs ${data.baseline.wasted_attempts} Baseline`} trendDirection="up" />
        <MetricCard title="Avg Days to Recovery (B2B)" value={String(data.agent.avg_days_to_recovery_b2b)} trend={`vs ${data.baseline.avg_days_to_recovery_b2b} Baseline`} trendDirection="up" />
        <MetricCard title="Recovery Rate Delta" value={`+${data.delta.rate_delta}%`} highlight />
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
              {rootCauses.map(rc => {
                const b = data.baseline.by_root_cause[rc]?.rate ?? 0;
                const a = data.agent.by_root_cause[rc]?.rate ?? 0;
                return (
                  <tr key={rc}>
                    <td>{rc}</td>
                    <td>{b}%</td>
                    <td>{a}%</td>
                    <td className="success-text">{a - b >= 0 ? '+' : ''}{(a - b).toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Comparison;
