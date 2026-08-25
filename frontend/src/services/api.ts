import { mockTransactions, mockQueue, mockAudit } from '../data/mockData';

const BASE_URL = 'http://localhost:8000';

// Helper for HTTP requests with automatic mock fallback
async function fetchWithFallback<T>(url: string, mockFallback: T): Promise<T> {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(2000) });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (err) {
    console.warn(`[Nova API] Backend unavailable at ${url}. Falling back to mock data.`, err);
    return mockFallback;
  }
}

export const api = {
  getDashboardMetrics: async () => {
    const mockDefault = {
      totalAtRisk: 1245000,
      recovered: 875000,
      recoveryRate: 70.2,
      activeCases: 47
    };
    return fetchWithFallback(`${BASE_URL}/reports/summary`, mockDefault);
  },

  getTransactions: async () => {
    return fetchWithFallback(`${BASE_URL}/reports/summary`, mockTransactions);
  },

  getRecoveryQueue: async () => {
    return fetchWithFallback(`${BASE_URL}/recovery/queue`, mockQueue);
  },

  getAuditTrail: async () => {
    return fetchWithFallback(`${BASE_URL}/audit/log`, mockAudit);
  },

  getBaselineComparison: async () => {
    const mockComparison = {
      baseline: { total_recovered: 450000, recovery_rate: 36.0 },
      agent: { total_recovered: 875000, recovery_rate: 70.2 },
      delta: { revenue_delta: 425000, rate_delta: 34.2 }
    };
    return fetchWithFallback(`${BASE_URL}/reports/baseline-vs-agent`, mockComparison);
  },

  getStrategyPerformance: async () => {
    return fetchWithFallback(`${BASE_URL}/reports/strategy-performance`, []);
  }
};
