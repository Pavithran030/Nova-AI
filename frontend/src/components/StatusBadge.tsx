import './StatusBadge.css';

interface StatusBadgeProps {
  status: string;
  type?: 'status' | 'cause';
}

const StatusBadge = ({ status, type = 'status' }: StatusBadgeProps) => {
  let className = 'status-badge ';
  
  if (type === 'status') {
    switch (status.toLowerCase()) {
      case 'recovered':
      case 'success':
        className += 'badge-success';
        break;
      case 'failed':
      case 'error':
        className += 'badge-danger';
        break;
      case 'pending':
      case 'in_progress':
      case 'warning':
        className += 'badge-warning';
        break;
      default:
        className += 'badge-default';
    }
  } else {
    // Cause badges
    className += 'badge-cause';
  }

  const formatText = (text: string) => {
    return text.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <span className={className}>
      {formatText(status)}
    </span>
  );
};

export default StatusBadge;
