// These mirror the ACTUAL backend response shapes (snake_case, matching
// the Pydantic/dict responses in backend/app/api/*.py and
// backend/app/schemas/*.py) rather than an idealized camelCase shape that
// drifted from what the API really returns.

export interface RootCauseBreakdown {
  at_risk: number;
  recovered: number;
  count: number;
  rate: number;
}

export interface RecentAction {
  timestamp: string | null;
  transaction_id: string;
  amount: number;
  root_cause: string | null;
  action_type: string;
  channel: string | null;
  outcome: string | null;
}

export interface ReportSummary {
  total_at_risk: number;
  total_recovered: number;
  recovery_rate: number;
  active_cases: number;
  by_root_cause: Record<string, RootCauseBreakdown>;
  trend: { date: string; at_risk: number; recovered: number }[];
  recent_actions: RecentAction[];
}

export interface QueueItem {
  id: string;
  entity_type: 'transaction' | 'invoice';
  entity_id: string;
  amount: number;
  root_cause: string | null;
  confidence: number | null;
  status: string;
  next_action: string | null;
  scheduled_for: string | null;
  attempt_count: number;
  max_attempts: number;
  customer_id: string;
  created_at: string;
  expected_recovery_value?: number;
  days_overdue?: number;
}

export interface RecoveryQueueResponse {
  items: QueueItem[];
  total: number;
}

export interface AuditLogEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action_type: string;
  reasoning: string | null;
  actor: string;
  npci_window: string | null;
  attempt_number: number | null;
  timestamp: string;
}

export interface AuditLogResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ComparisonSide {
  total_recovered: number;
  recovery_rate: number;
  retries_outside_window: number;
  wasted_attempts: number;
  avg_days_to_recovery_b2b: number;
  by_root_cause: Record<string, { recovered: number; rate: number }>;
}

export interface BaselineComparisonResponse {
  baseline: ComparisonSide;
  agent: ComparisonSide;
  delta: {
    revenue_delta: number;
    rate_delta: number;
    window_violations_eliminated: number;
    days_saved_b2b: number;
  };
}

export interface ChannelPerformance {
  channel: string;
  attempts: number;
  successes: number;
  revenue_recovered: number;
  success_rate: number;
  roi: number;
}

export interface StrategyPerformanceResponse {
  channels: ChannelPerformance[];
}
