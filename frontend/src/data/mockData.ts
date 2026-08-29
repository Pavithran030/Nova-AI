// Fallback data used only when the backend is unreachable (see
// services/api.ts's fetchWithFallback). Shaped identically to the real
// API responses so components never need to branch on "is this mock or
// real data" — that was the bug in the previous version of this file.

import type {
  ReportSummary,
  RecoveryQueueResponse,
  AuditLogResponse,
  BaselineComparisonResponse,
  StrategyPerformanceResponse,
} from '../types';

export const mockSummary: ReportSummary = {
  total_at_risk: 1245000,
  total_recovered: 875000,
  recovery_rate: 70.2,
  active_cases: 47,
  by_root_cause: {
    INSUFFICIENT_FUNDS: { at_risk: 320000, recovered: 224000, count: 18, rate: 70.0 },
    BANK_TIMEOUT: { at_risk: 280000, recovered: 238000, count: 15, rate: 85.0 },
    CARD_EXPIRED: { at_risk: 210000, recovered: 73500, count: 9, rate: 35.0 },
    MANDATE_REVOKED: { at_risk: 150000, recovered: 37500, count: 6, rate: 25.0 },
  },
  trend: [
    { date: '2026-08-23', at_risk: 150000, recovered: 100000 },
    { date: '2026-08-24', at_risk: 180000, recovered: 140000 },
    { date: '2026-08-25', at_risk: 120000, recovered: 90000 },
    { date: '2026-08-26', at_risk: 200000, recovered: 150000 },
    { date: '2026-08-27', at_risk: 250000, recovered: 200000 },
    { date: '2026-08-28', at_risk: 170000, recovered: 130000 },
    { date: '2026-08-29', at_risk: 140000, recovered: 110000 },
  ],
  recent_actions: [
    { timestamp: '2026-08-29T10:30:00Z', transaction_id: 'txn_10293847', amount: 15400, root_cause: 'INSUFFICIENT_FUNDS', action_type: 'delay_retry', channel: 'api_retry', outcome: 'SUCCESS' },
    { timestamp: '2026-08-29T11:15:00Z', transaction_id: 'txn_10293848', amount: 8200, root_cause: 'BANK_TIMEOUT', action_type: 'immediate_retry_with_backoff', channel: 'api_retry', outcome: 'FAILED' },
    { timestamp: '2026-08-29T09:00:00Z', transaction_id: 'txn_10293849', amount: 45000, root_cause: 'CARD_EXPIRED', action_type: 'send_update_link', channel: 'whatsapp', outcome: 'SUCCESS' },
  ],
};

export const mockQueue: RecoveryQueueResponse = {
  total: 3,
  items: [
    { id: 'inv_88293', entity_type: 'invoice', entity_id: 'inv_88293', amount: 450000, root_cause: 'OVERDUE', confidence: 0.85, status: 'overdue', next_action: 'b2b_follow_up', scheduled_for: null, attempt_count: 1, max_attempts: 3, customer_id: 'cust_0012', created_at: '2026-08-20T00:00:00Z', expected_recovery_value: 310000, days_overdue: 9 },
    { id: 'sub_99211', entity_type: 'transaction', entity_id: 'sub_99211', amount: 1499, root_cause: 'INSUFFICIENT_FUNDS', confidence: 0.78, status: 'failed', next_action: 'delay_retry', scheduled_for: null, attempt_count: 2, max_attempts: 4, customer_id: 'cust_0044', created_at: '2026-08-28T16:30:00Z' },
    { id: 'loan_44122', entity_type: 'transaction', entity_id: 'loan_44122', amount: 15500, root_cause: 'MANDATE_REVOKED', confidence: 0.45, status: 'failed', next_action: 'trigger_reauth', scheduled_for: null, attempt_count: 3, max_attempts: 4, customer_id: 'cust_0091', created_at: '2026-08-27T09:00:00Z' },
  ],
};

export const mockAudit: AuditLogResponse = {
  total: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
  items: [
    { id: 'a1', entity_type: 'transaction', entity_id: 'txn_10293847', action_type: 'delay_retry', reasoning: 'Matches insufficient funds pattern', actor: 'agent', npci_window: 'valid', attempt_number: 1, timestamp: '2026-08-29T10:30:00Z' },
    { id: 'a2', entity_type: 'invoice', entity_id: 'inv_88293', action_type: 'b2b_follow_up', reasoning: 'Status is overdue', actor: 'agent', npci_window: null, attempt_number: 2, timestamp: '2026-08-29T09:15:00Z' },
    { id: 'a3', entity_type: 'transaction', entity_id: 'sub_99211', action_type: 'ESCALATE_TO_HUMAN', reasoning: 'ML classifier predicted BANK_TIMEOUT with 28.0% confidence — below threshold, escalating to human review', actor: 'agent', npci_window: 'invalid', attempt_number: 4, timestamp: '2026-08-28T16:45:00Z' },
  ],
};

export const mockComparison: BaselineComparisonResponse = {
  baseline: { total_recovered: 450000, recovery_rate: 36.0, retries_outside_window: 12, wasted_attempts: 18, avg_days_to_recovery_b2b: 15.2, by_root_cause: { INSUFFICIENT_FUNDS: { recovered: 90000, rate: 22.8 } } },
  agent: { total_recovered: 875000, recovery_rate: 70.2, retries_outside_window: 0, wasted_attempts: 0, avg_days_to_recovery_b2b: 7.8, by_root_cause: { INSUFFICIENT_FUNDS: { recovered: 262500, rate: 80.0 } } },
  delta: { revenue_delta: 425000, rate_delta: 34.2, window_violations_eliminated: 12, days_saved_b2b: 7.4 },
};

export const mockStrategy: StrategyPerformanceResponse = {
  channels: [
    { channel: 'whatsapp', attempts: 42, successes: 26, revenue_recovered: 320000, success_rate: 62.2, roi: 2.3 },
    { channel: 'email', attempts: 38, successes: 15, revenue_recovered: 180000, success_rate: 39.5, roi: 1.5 },
    { channel: 'api_retry', attempts: 55, successes: 39, revenue_recovered: 210000, success_rate: 71.0, roi: 3.1 },
  ],
};
