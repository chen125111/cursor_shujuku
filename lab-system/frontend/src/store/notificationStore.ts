import { create } from 'zustand';
import { notificationApi } from '@/api/notification';
import type { Notification } from '@/types';

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  loading: boolean;
  fetchNotifications: (params?: Record<string, unknown>) => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  addNotification: (notification: Notification) => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  loading: false,

  fetchNotifications: async (params) => {
    set({ loading: true });
    try {
      const res = await notificationApi.getAll(params);
      if (res.success && res.data) {
        set({ notifications: res.data.notifications as Notification[] });
      }
    } finally {
      set({ loading: false });
    }
  },

  fetchUnreadCount: async () => {
    try {
      const res = await notificationApi.getUnreadCount();
      if (res.success && res.data) {
        set({ unreadCount: res.data.count });
      }
    } catch {
      // silently fail
    }
  },

  markAsRead: async (id) => {
    await notificationApi.markAsRead(id);
    const { notifications, unreadCount } = get();
    set({
      notifications: notifications.map((n) =>
        n._id === id ? { ...n, isRead: true } : n
      ),
      unreadCount: Math.max(0, unreadCount - 1),
    });
  },

  markAllAsRead: async () => {
    await notificationApi.markAllAsRead();
    const { notifications } = get();
    set({
      notifications: notifications.map((n) => ({ ...n, isRead: true })),
      unreadCount: 0,
    });
  },

  addNotification: (notification) => {
    const { notifications, unreadCount } = get();
    set({
      notifications: [notification, ...notifications],
      unreadCount: unreadCount + 1,
    });
  },
}));
