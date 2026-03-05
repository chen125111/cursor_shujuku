import request from './request';
import type { ApiResponse, Notification } from '@/types';

export const notificationApi = {
  getAll: (params?: Record<string, unknown>) =>
    request.get<unknown, ApiResponse<{ notifications: Notification[]; meta: unknown }>>('/notifications', { params }),

  getUnreadCount: () =>
    request.get<unknown, ApiResponse<{ count: number }>>('/notifications/unread-count'),

  markAsRead: (id: string) =>
    request.put<unknown, ApiResponse>(`/notifications/${id}/read`),

  markAllAsRead: () =>
    request.put<unknown, ApiResponse>('/notifications/read-all'),
};
