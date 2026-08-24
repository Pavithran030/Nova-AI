import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import './Strategy.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const Strategy = () => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  const channels = [
    { name: 'WhatsApp', success: 62.2, recovered: 320000, roi: 2.3 },
    { name: 'Email', success: 39.5, recovered: 180000, roi: 1.5 },
    { name: 'SMS', success: 45.0, recovered: 120000, roi: 1.8 },
    { name: 'API Retry', success: 71.0, recovered: 210000, roi: 3.1 },
    { name: 'Voice', success: 33.0, recovered: 45000, roi: 1.2 },
  ];

  const roiData = {
    labels: channels.map(c => c.name),
    datasets: [
      {
        label: 'ROI Multiplier (x)',
        data: channels.map(c => c.roi),
        backgroundColor: '#3B6CF5',
        borderRadius: 4,
      }
    ]
  };

  const roiOptions = {
    indexAxis: 'y' as const,
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { x: { beginAtZero: true, grid: { color: '#E2E5EA' } }, y: { grid: { display: false } } }
  };

  const successData = {
    labels: channels.map(c => c.name),
    datasets: [
      { label: 'Success (%)', data: channels.map(c => c.success), backgroundColor: '#12875A' },
      { label: 'Failed (%)', data: channels.map(c => 100 - c.success), backgroundColor: '#FDE8E8' }
    ]
  };

  const successOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' as const } },
    scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, max: 100, grid: { color: '#E2E5EA' } } }
  };

  return (
    <div className="strategy-page">
      <div className="page-header">
        <h1>Strategy Performance</h1>
      </div>

      <div className="channel-grid">
        {channels.map((ch, idx) => (
          <div key={idx} className="channel-card">
            <div className="channel-header">
              <h3>{ch.name}</h3>
              <span className="roi-badge">{ch.roi}x ROI</span>
            </div>
            <div className="channel-stats">
              <div className="stat-row">
                <span className="stat-label">Success Rate</span>
                <span className="stat-val">{ch.success}%</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Recovered</span>
                <span className="stat-val amount">{formatCurrency(ch.recovered)}</span>
              </div>
            </div>
            <div className="progress-bg">
              <div className="progress-fill" style={{ width: `${ch.success}%` }}></div>
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
