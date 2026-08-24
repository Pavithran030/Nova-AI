export interface Transaction {
  id: string;
  amount: number;
  rootCause: string;
  status: 'recovered' | 'failed' | 'pending';
  channel: string;
  timestamp: string;
  action: string;
}

export interface QueueItem {
  priority: number;
  entityType: string;
  entityId: string;
  amount: number;
  rootCause: string;
  confidence: number;
  nextAction: string;
  scheduledFor: string;
  attempts: number;
  status: 'pending' | 'in_progress' | 'failed' | 'recovered';
}

export interface AuditEntry {
  timestamp: string;
  entityType: string;
  entityId: string;
  actionType: string;
  channel: string;
  actor: 'agent' | 'human';
  npciWindow: boolean;
  attempt: number;
  reasoning: string;
}
