import { Transaction, QueueItem, AuditEntry } from '../types';

export const mockTransactions: Transaction[] = [
  { id: 'txn_10293847', amount: 15400, rootCause: 'INSUFFICIENT_FUNDS', status: 'recovered', channel: 'WhatsApp', timestamp: '2023-10-24T10:30:00Z', action: 'Payment Link Sent' },
  { id: 'txn_10293848', amount: 8200, rootCause: 'BANK_TIMEOUT', status: 'pending', channel: 'API Retry', timestamp: '2023-10-24T11:15:00Z', action: 'Auto Retry Scheduled' },
  { id: 'txn_10293849', amount: 45000, rootCause: 'CARD_EXPIRED', status: 'failed', channel: 'Email', timestamp: '2023-10-24T09:00:00Z', action: 'Card Update Request' },
  { id: 'txn_10293850', amount: 2300, rootCause: 'NETWORK_ERROR', status: 'recovered', channel: 'API Retry', timestamp: '2023-10-24T12:05:00Z', action: 'Auto Retry Executed' },
  { id: 'txn_10293851', amount: 112000, rootCause: 'MANDATE_REVOKED', status: 'pending', channel: 'Voice', timestamp: '2023-10-24T14:20:00Z', action: 'Agent Call Scheduled' },
];

export const mockQueue: QueueItem[] = [
  { priority: 1, entityType: 'B2B Invoice', entityId: 'inv_88293', amount: 450000, rootCause: 'BANK_TIMEOUT', confidence: 92, nextAction: 'API Retry', scheduledFor: 'Today, 14:00', attempts: 1, status: 'pending' },
  { priority: 2, entityType: 'Subscription', entityId: 'sub_99211', amount: 1499, rootCause: 'INSUFFICIENT_FUNDS', confidence: 78, nextAction: 'WhatsApp Nudge', scheduledFor: 'Today, 16:30', attempts: 2, status: 'in_progress' },
  { priority: 3, entityType: 'Loan EMI', entityId: 'loan_44122', amount: 15500, rootCause: 'MANDATE_REVOKED', confidence: 45, nextAction: 'Voice Call', scheduledFor: 'Tomorrow, 09:00', attempts: 3, status: 'pending' },
];

export const mockAudit: AuditEntry[] = [
  { timestamp: '2023-10-24T10:30:00Z', entityType: 'Payment', entityId: 'txn_10293847', actionType: 'Message Sent', channel: 'WhatsApp', actor: 'agent', npciWindow: true, attempt: 1, reasoning: 'High probability of balance top-up based on historical patterns.' },
  { timestamp: '2023-10-24T09:15:00Z', entityType: 'Invoice', entityId: 'inv_88293', actionType: 'Retry Executed', channel: 'API', actor: 'agent', npciWindow: true, attempt: 2, reasoning: 'Bank downtime resolved, executing immediate retry.' },
  { timestamp: '2023-10-23T16:45:00Z', entityType: 'Subscription', entityId: 'sub_99211', actionType: 'Human Escalation', channel: 'Internal', actor: 'human', npciWindow: false, attempt: 4, reasoning: 'Customer requested manual callback via SMS reply.' },
];
