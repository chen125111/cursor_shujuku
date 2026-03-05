import { Notification } from '../models';
import { NotificationType } from '../types';
import { logger } from '../utils/logger';

export class NotificationService {
  static async create(data: {
    recipient: string;
    sender?: string;
    type: NotificationType;
    title: string;
    content: string;
    relatedId?: string;
    relatedModel?: string;
  }) {
    const notification = new Notification(data);
    await notification.save();

    // TODO: emit via Socket.IO for real-time push
    logger.info(`Notification sent to ${data.recipient}: ${data.title}`);

    return notification;
  }

  static async getUserNotifications(
    userId: string,
    page = 1,
    limit = 20,
    unreadOnly = false
  ) {
    const filter: Record<string, unknown> = { recipient: userId };
    if (unreadOnly) filter.isRead = false;

    const total = await Notification.countDocuments(filter);
    const notifications = await Notification.find(filter)
      .sort({ createdAt: -1 })
      .skip((page - 1) * limit)
      .limit(limit)
      .populate('sender', 'displayName avatar');

    return { notifications, total };
  }

  static async getUnreadCount(userId: string) {
    return Notification.countDocuments({ recipient: userId, isRead: false });
  }

  static async markAsRead(notificationId: string, userId: string) {
    return Notification.findOneAndUpdate(
      { _id: notificationId, recipient: userId },
      { isRead: true, readAt: new Date() },
      { new: true }
    );
  }

  static async markAllAsRead(userId: string) {
    return Notification.updateMany(
      { recipient: userId, isRead: false },
      { isRead: true, readAt: new Date() }
    );
  }

  static async notifyReservationApproved(
    recipientId: string,
    equipmentName: string,
    reservationId: string
  ) {
    return this.create({
      recipient: recipientId,
      type: NotificationType.RESERVATION_APPROVED,
      title: '预约已通过',
      content: `您对设备「${equipmentName}」的预约申请已通过审批。`,
      relatedId: reservationId,
      relatedModel: 'Reservation',
    });
  }

  static async notifyReservationRejected(
    recipientId: string,
    equipmentName: string,
    reason: string,
    reservationId: string
  ) {
    return this.create({
      recipient: recipientId,
      type: NotificationType.RESERVATION_REJECTED,
      title: '预约被拒绝',
      content: `您对设备「${equipmentName}」的预约申请被拒绝。原因：${reason}`,
      relatedId: reservationId,
      relatedModel: 'Reservation',
    });
  }

  static async notifyLowStock(
    managerId: string,
    itemName: string,
    quantity: number,
    inventoryId: string
  ) {
    return this.create({
      recipient: managerId,
      type: NotificationType.INVENTORY_LOW,
      title: '库存不足提醒',
      content: `物品「${itemName}」当前库存为 ${quantity}，已低于最低库存线，请及时补充。`,
      relatedId: inventoryId,
      relatedModel: 'Inventory',
    });
  }
}
