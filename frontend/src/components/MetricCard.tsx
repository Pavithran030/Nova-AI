import React from 'react';
import './MetricCard.css';

interface MetricCardProps {
  title: string;
  value: string | React.ReactNode;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  highlight?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, trend, trendDirection, highlight }) => {
  return (
    <div className={`metric-card ${highlight ? 'highlight' : ''}`}>
      <h3 className="metric-title">{title}</h3>
      <div className="metric-value">{value}</div>
      {trend && (
        <div className={`metric-trend ${trendDirection}`}>
          {trendDirection === 'up' && '↑ '}
          {trendDirection === 'down' && '↓ '}
          {trend}
        </div>
      )}
    </div>
  );
};

export default MetricCard;
