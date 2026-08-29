import { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { api } from '../services/api';
import type { ChannelPerformance } from '../types';
import './Strategy.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
};

const Strategy = () => {
  const [channels, setChannels] = useState<ChannelPerformance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getStrategyPerformance()
      .then(res => setChannels(res.channels))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="strategy-page"><div className="page-header"><h1>Strategy Performance</h1></div><p>Loading…</p></div>;
  if (channels.length === 0) return <div className="strategy-page"><div className="page-header"><h1>Strategy Performance</h1></div><p>No processed recovery actions yet.</p></div>;

  const roiData = {
    labels: channels.map(c => c.channel),
    datasets: [
      { label: 'ROI Multiplier (x)', data: channels.map(c => c.roi), backgroundColor: '#3B6CF5', borderRadius: 4 },
    ],
  };

  const roiOptions = {
    indexAxis: 'y' as const,
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { x: { beginAtZero: true, grid: { color: '#E2E5EA' } }, y: { grid: { display: false } } },
  };

  const successData = {
    labels: channels.map(c => c.channel),
    datasets: [
      { label: 'Success (%)', data: channels.map(c => c.success_rate), backgroundColor: '#12875A' },
      { label: 'Failed (%)', data: channels.map(c => 100 - c.success_rate), backgroundColor: '#FDE8E8' },
    ],
  };

  const successOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' as const } },
    scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, max: 100, grid: { color: '#E2E5EA' } } },
  };

  return (
    <div className="strategy-page">
      <div className="page-header">
        <h1>Strategy Performance</h1>
      </div>

      <div className="channel-grid">
        {channels.map((ch) => (
          <div key={ch.channel} className="channel-card">
            <div className="channel-header">
              <h3>{ch.channel}</h3>
              <span className="roi-badge">{ch.roi}x ROI</span>
            </div>
            <div className="channel-stats">
              <div className="stat-row">
                <span className="stat-label">Success Rate</span>
                <span className="stat-val">{ch.success_rate}%</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Recovered</span>
                <span className="stat-val amount">{formatCurrency(ch.revenue_recovered)}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Attempts</span>
                <span className="stat-val">{ch.attempts}</span>
              </div>
            </div>
            <div className="progress-bg">
              <div className="progress-fill" style={{ width: `${ch.success_rate}%` }}></div>
            </div>
          </div>
        ))}
      </div>

      <div className="charts-grid-strategy">
        <div className="chart-card">
          <h3>ROI by Channel</h3>
          <div className="chart-container">
            <Bar data={roiData} options={roiOptions} />
          </div>
        </div>
        <div className="chart-card">
          <h3>Success vs Failed Distribution</h3>
          <div className="chart-container">
            <Bar data={successData} options={successOptions} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Strategy;
