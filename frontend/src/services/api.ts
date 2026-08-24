import { mockTransactions, mockQueue, mockAudit } from '../data/mockData';

// Mock API service for frontend-only mode
export const api = {
  getDashboardMetrics: async () => {
    return new Promise(resolve => setTimeout(() => resolve({
      totalAtRisk: 1245000,
      recovered: 875000,
      recoveryRate: 70.2,
      activeCases: 47
    }), 300));
  },
  
  getTransactions: async () => {
    return new Promise(resolve => setTimeout(() => resolve(mockTransactions), 400));
  },
  
  getRecoveryQueue: async () => {
    return new Promise(resolve => setTimeout(() => resolve(mockQueue), 500));
  },
  
  getAuditTrail: async () => {
    return new Promise(resolve => setTimeout(() => resolve(mockAudit), 300));
  }
};
