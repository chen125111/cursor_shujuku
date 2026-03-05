import request from './request';
import type { ApiResponse, InventoryItem } from '@/types';

export const inventoryApi = {
  getAll: (params?: Record<string, unknown>) =>
    request.get<unknown, ApiResponse<InventoryItem[]>>('/inventory', { params }),

  getById: (id: string) =>
    request.get<unknown, ApiResponse<InventoryItem>>(`/inventory/${id}`),

  create: (data: Partial<InventoryItem>) =>
    request.post<unknown, ApiResponse<InventoryItem>>('/inventory', data),

  update: (id: string, data: Partial<InventoryItem>) =>
    request.put<unknown, ApiResponse<InventoryItem>>(`/inventory/${id}`, data),

  delete: (id: string) =>
    request.delete<unknown, ApiResponse>(`/inventory/${id}`),

  recordUsage: (id: string, data: { quantity: number; type: 'in' | 'out'; notes?: string }) =>
    request.post<unknown, ApiResponse<InventoryItem>>(`/inventory/${id}/usage`, data),

  getStatistics: () =>
    request.get<unknown, ApiResponse>('/inventory/statistics'),
};
