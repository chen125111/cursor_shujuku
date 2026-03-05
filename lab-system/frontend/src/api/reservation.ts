import request from './request';
import type { ApiResponse, Reservation } from '@/types';

export const reservationApi = {
  getAll: (params?: Record<string, unknown>) =>
    request.get<unknown, ApiResponse<Reservation[]>>('/reservations', { params }),

  getMyReservations: (params?: Record<string, unknown>) =>
    request.get<unknown, ApiResponse<Reservation[]>>('/reservations/my', { params }),

  create: (data: {
    equipment: string;
    startTime: string;
    endTime: string;
    purpose: string;
    notes?: string;
  }) =>
    request.post<unknown, ApiResponse<Reservation>>('/reservations', data),

  updateStatus: (id: string, data: { status: string; rejectReason?: string }) =>
    request.put<unknown, ApiResponse<Reservation>>(`/reservations/${id}/status`, data),

  cancel: (id: string) =>
    request.put<unknown, ApiResponse<Reservation>>(`/reservations/${id}/cancel`),

  getCalendar: (params: { startDate: string; endDate: string; equipment?: string }) =>
    request.get<unknown, ApiResponse<Reservation[]>>('/reservations/calendar', { params }),
};
