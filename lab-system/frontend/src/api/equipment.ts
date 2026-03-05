import request from './request';
import type { ApiResponse, Equipment } from '@/types';

export const equipmentApi = {
  getAll: (params?: Record<string, unknown>) =>
    request.get<unknown, ApiResponse<Equipment[]>>('/equipment', { params }),

  getById: (id: string) =>
    request.get<unknown, ApiResponse<Equipment>>(`/equipment/${id}`),

  create: (data: Partial<Equipment>) =>
    request.post<unknown, ApiResponse<Equipment>>('/equipment', data),

  update: (id: string, data: Partial<Equipment>) =>
    request.put<unknown, ApiResponse<Equipment>>(`/equipment/${id}`, data),

  delete: (id: string) =>
    request.delete<unknown, ApiResponse>(`/equipment/${id}`),

  addMaintenance: (id: string, data: Record<string, unknown>) =>
    request.post<unknown, ApiResponse<Equipment>>(`/equipment/${id}/maintenance`, data),

  getStatistics: () =>
    request.get<unknown, ApiResponse>('/equipment/statistics'),
};
