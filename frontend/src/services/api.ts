import {
  mockSummary,
  mockQueue,
  mockAudit,
  mockComparison,
  mockStrategy,
} from '../data/mockData';
import type {
  ReportSummary,
  RecoveryQueueResponse,
  AuditLogResponse,
  BaselineComparisonResponse,
  StrategyPerformanceResponse,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper for HTTP requests with automatic mock fallback
async function fetchWithFallback<T>(url: string, mockFallback: T): Promise<T> {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(4000) });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (err) {
    console.warn(`[Nova API] Backend unavailable at ${url}. Falling back to mock data.`, err);
    return mockFallback;
  }
}

export const api = {
  getDashboardSummary: async (): Promise<ReportSummary> => {
    return fetchWithFallback(`${BASE_URL}/reports/summary`, mockSummary);
  },

  getRecoveryQueue: async (): Promise<RecoveryQueueResponse> => {
    return fetchWithFallback(`${BASE_URL}/recovery/queue`, mockQueue);
  },

  getAuditTrail: async (page = 1, pageSize = 20): Promise<AuditLogResponse> => {
    return fetchWithFallback(
      `${BASE_URL}/audit/log?page=${page}&page_size=${pageSize}`,
      mockAudit
    );
  },

  getBaselineComparison: async (): Promise<BaselineComparisonResponse> => {
    return fetchWithFallback(`${BASE_URL}/reports/baseline-vs-agent`, mockComparison);
  },

  getStrategyPerformance: async (): Promise<StrategyPerformanceResponse> => {
    return fetchWithFallback(`${BASE_URL}/reports/strategy-performance`, mockStrategy);
  },

  executeRecoveryAction: async (entityType: string, id: string) => {
    const response = await fetch(`${BASE_URL}/recovery/${entityType}/${id}/execute`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.json();
  },
};
