import { Response, NextFunction } from 'express';
import { AuthRequest } from '../types';
import { sendSuccess } from '../utils/response';
import { NotificationService } from '../services/notification.service';

export class NotificationController {
  static async getAll(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const { page = 1, limit = 20, unreadOnly } = req.query;
      const { notifications, total } = await NotificationService.getUserNotifications(
        req.user!.userId,
        Number(page),
        Number(limit),
        unreadOnly === 'true'
      );

      sendSuccess(res, {
        notifications,
        meta: {
          page: Number(page),
          limit: Number(limit),
          total,
          totalPages: Math.ceil(total / Number(limit)),
        },
      }, '获取通知列表成功');
    } catch (error) {
      next(error);
    }
  }

  static async getUnreadCount(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const count = await NotificationService.getUnreadCount(req.user!.userId);
      sendSuccess(res, { count }, '获取未读数量成功');
    } catch (error) {
      next(error);
    }
  }

  static async markAsRead(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      await NotificationService.markAsRead(req.params.id, req.user!.userId);
      sendSuccess(res, null, '已标记为已读');
    } catch (error) {
      next(error);
    }
  }

  static async markAllAsRead(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      await NotificationService.markAllAsRead(req.user!.userId);
      sendSuccess(res, null, '已全部标记为已读');
    } catch (error) {
      next(error);
    }
  }
}
