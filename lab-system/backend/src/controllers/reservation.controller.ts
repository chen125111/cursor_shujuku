import { Request, Response, NextFunction } from 'express';
import { Reservation, Equipment } from '../models';
import { AuthRequest, ReservationStatus } from '../types';
import { sendSuccess, sendError, sendPaginated } from '../utils/response';
import { NotificationService } from '../services/notification.service';

export class ReservationController {
  static async getAll(req: Request, res: Response, next: NextFunction) {
    try {
      const {
        page = 1,
        limit = 20,
        status,
        equipment,
        user,
        startDate,
        endDate,
      } = req.query;

      const filter: Record<string, unknown> = {};
      if (status) filter.status = status;
      if (equipment) filter.equipment = equipment;
      if (user) filter.user = user;
      if (startDate || endDate) {
        filter.startTime = {};
        if (startDate) (filter.startTime as any).$gte = new Date(startDate as string);
        if (endDate) (filter.startTime as any).$lte = new Date(endDate as string);
      }

      const pageNum = Number(page);
      const limitNum = Number(limit);

      const total = await Reservation.countDocuments(filter);
      const reservations = await Reservation.find(filter)
        .populate('equipment', 'name code location')
        .populate('user', 'displayName email department')
        .populate('approvedBy', 'displayName')
        .sort({ createdAt: -1 })
        .skip((pageNum - 1) * limitNum)
        .limit(limitNum);

      sendPaginated(res, reservations, total, pageNum, limitNum, '获取预约列表成功');
    } catch (error) {
      next(error);
    }
  }

  static async getMyReservations(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const { page = 1, limit = 20, status } = req.query;
      const filter: Record<string, unknown> = { user: req.user!.userId };
      if (status) filter.status = status;

      const pageNum = Number(page);
      const limitNum = Number(limit);

      const total = await Reservation.countDocuments(filter);
      const reservations = await Reservation.find(filter)
        .populate('equipment', 'name code location')
        .sort({ createdAt: -1 })
        .skip((pageNum - 1) * limitNum)
        .limit(limitNum);

      sendPaginated(res, reservations, total, pageNum, limitNum);
    } catch (error) {
      next(error);
    }
  }

  static async create(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const { equipment: equipmentId, startTime, endTime, purpose, notes } = req.body;

      const equipmentDoc = await Equipment.findById(equipmentId);
      if (!equipmentDoc) {
        sendError(res, '设备不存在', 404);
        return;
      }

      if (equipmentDoc.status !== 'available') {
        sendError(res, '设备当前不可预约', 400);
        return;
      }

      const conflict = await Reservation.findOne({
        equipment: equipmentId,
        status: { $in: [ReservationStatus.PENDING, ReservationStatus.APPROVED] },
        $or: [
          {
            startTime: { $lt: new Date(endTime) },
            endTime: { $gt: new Date(startTime) },
          },
        ],
      });

      if (conflict) {
        sendError(res, '该时间段已有预约，请选择其他时间', 409);
        return;
      }

      const reservation = new Reservation({
        equipment: equipmentId,
        user: req.user!.userId,
        startTime: new Date(startTime),
        endTime: new Date(endTime),
        purpose,
        notes,
      });
      await reservation.save();

      sendSuccess(res, reservation, '预约提交成功', 201);
    } catch (error) {
      next(error);
    }
  }

  static async updateStatus(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const { status, rejectReason } = req.body;
      const reservation = await Reservation.findById(req.params.id)
        .populate('equipment', 'name');

      if (!reservation) {
        sendError(res, '预约不存在', 404);
        return;
      }

      if (reservation.status !== ReservationStatus.PENDING) {
        sendError(res, '只能处理待审批的预约', 400);
        return;
      }

      reservation.status = status;
      if (status === ReservationStatus.APPROVED) {
        reservation.approvedBy = req.user!.userId as any;
        reservation.approvedAt = new Date();
        await NotificationService.notifyReservationApproved(
          reservation.user.toString(),
          (reservation.equipment as any).name,
          reservation._id as string
        );
      } else if (status === ReservationStatus.REJECTED) {
        reservation.rejectReason = rejectReason;
        await NotificationService.notifyReservationRejected(
          reservation.user.toString(),
          (reservation.equipment as any).name,
          rejectReason || '未说明原因',
          reservation._id as string
        );
      }

      await reservation.save();
      sendSuccess(res, reservation, '预约状态更新成功');
    } catch (error) {
      next(error);
    }
  }

  static async cancel(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const reservation = await Reservation.findOne({
        _id: req.params.id,
        user: req.user!.userId,
      });

      if (!reservation) {
        sendError(res, '预约不存在', 404);
        return;
      }

      if (![ReservationStatus.PENDING, ReservationStatus.APPROVED].includes(
        reservation.status as ReservationStatus
      )) {
        sendError(res, '当前状态无法取消', 400);
        return;
      }

      reservation.status = ReservationStatus.CANCELLED;
      await reservation.save();
      sendSuccess(res, reservation, '预约已取消');
    } catch (error) {
      next(error);
    }
  }

  static async getCalendar(req: Request, res: Response, next: NextFunction) {
    try {
      const { startDate, endDate, equipment } = req.query;
      const filter: Record<string, unknown> = {
        status: { $in: [ReservationStatus.APPROVED, ReservationStatus.PENDING] },
      };

      if (equipment) filter.equipment = equipment;
      if (startDate && endDate) {
        filter.startTime = { $gte: new Date(startDate as string) };
        filter.endTime = { $lte: new Date(endDate as string) };
      }

      const reservations = await Reservation.find(filter)
        .populate('equipment', 'name code')
        .populate('user', 'displayName');

      sendSuccess(res, reservations, '获取日历数据成功');
    } catch (error) {
      next(error);
    }
  }
}
