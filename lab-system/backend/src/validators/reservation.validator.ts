import { z } from 'zod';

export const createReservationSchema = z.object({
  body: z.object({
    equipment: z.string().min(1, '请选择设备'),
    startTime: z.string().min(1, '请选择开始时间'),
    endTime: z.string().min(1, '请选择结束时间'),
    purpose: z.string().min(1, '请输入使用目的').max(500),
    notes: z.string().max(1000).optional(),
  }),
});

export const updateReservationStatusSchema = z.object({
  body: z.object({
    status: z.enum(['approved', 'rejected', 'cancelled']),
    rejectReason: z.string().optional(),
  }),
  params: z.object({
    id: z.string().min(1),
  }),
});
