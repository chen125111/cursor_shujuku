import request from './request';
import type { ApiResponse, User } from '@/types';

export const userApi = {
  getAll: (params?: Record<string, unknown>) =>
    request.get<unknown, ApiResponse<User[]>>('/users', { params }),

  getById: (id: string) =>
    request.get<unknown, ApiResponse<User>>(`/users/${id}`),

  update: (id: string, data: Partial<User>) =>
    request.put<unknown, ApiResponse<User>>(`/users/${id}`, data),

  updateRole: (id: string, role: string) =>
    request.put<unknown, ApiResponse<User>>(`/users/${id}/role`, { role }),

  toggleActive: (id: string) =>
    request.put<unknown, ApiResponse<User>>(`/users/${id}/toggle-active`),

  getDepartments: () =>
    request.get<unknown, ApiResponse<string[]>>('/users/departments'),
};
