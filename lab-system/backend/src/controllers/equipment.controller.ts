import { Request, Response, NextFunction } from 'express';
import { Equipment } from '../models';
import { AuthRequest } from '../types';
import { sendSuccess, sendError, sendPaginated } from '../utils/response';
import { cacheGet, cacheSet, cacheDel } from '../config/redis';

const CACHE_PREFIX = 'equipment';

export class EquipmentController {
  static async getAll(req: Request, res: Response, next: NextFunction) {
    try {
      const {
        page = 1,
        limit = 20,
        search,
        category,
        status,
        department,
        sortBy = 'createdAt',
        sortOrder = 'desc',
      } = req.query;

      const cacheKey = `${CACHE_PREFIX}:list:${JSON.stringify(req.query)}`;
      const cached = await cacheGet<{ data: any[]; total: number }>(cacheKey);
      if (cached) {
        return sendPaginated(
          res,
          cached.data,
          cached.total,
          Number(page),
          Number(limit)
        );
      }

      const filter: Record<string, unknown> = {};
      if (search) {
        filter.$or = [
          { name: { $regex: search, $options: 'i' } },
          { code: { $regex: search, $options: 'i' } },
        ];
      }
      if (category) filter.category = category;
      if (status) filter.status = status;
      if (department) filter.department = department;

      const pageNum = Number(page);
      const limitNum = Number(limit);

      const total = await Equipment.countDocuments(filter);
      const equipments = await Equipment.find(filter)
        .populate('manager', 'displayName email')
        .sort({ [sortBy as string]: sortOrder === 'asc' ? 1 : -1 })
        .skip((pageNum - 1) * limitNum)
        .limit(limitNum);

      await cacheSet(cacheKey, { data: equipments, total }, 300);
      sendPaginated(res, equipments, total, pageNum, limitNum, '获取设备列表成功');
    } catch (error) {
      next(error);
    }
  }

  static async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const cacheKey = `${CACHE_PREFIX}:${req.params.id}`;
      const cached = await cacheGet(cacheKey);
      if (cached) {
        return sendSuccess(res, cached);
      }

      const equipment = await Equipment.findById(req.params.id)
        .populate('manager', 'displayName email');
      if (!equipment) {
        sendError(res, '设备不存在', 404);
        return;
      }

      await cacheSet(cacheKey, equipment, 600);
      sendSuccess(res, equipment, '获取设备详情成功');
    } catch (error) {
      next(error);
    }
  }

  static async create(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const equipment = new Equipment({
        ...req.body,
        manager: req.user?.userId,
      });
      await equipment.save();
      await cacheDel(`${CACHE_PREFIX}:list:*`);
      sendSuccess(res, equipment, '创建设备成功', 201);
    } catch (error) {
      next(error);
    }
  }

  static async update(req: Request, res: Response, next: NextFunction) {
    try {
      const equipment = await Equipment.findByIdAndUpdate(
        req.params.id,
        req.body,
        { new: true, runValidators: true }
      );
      if (!equipment) {
        sendError(res, '设备不存在', 404);
        return;
      }
      await cacheDel(`${CACHE_PREFIX}:*`);
      sendSuccess(res, equipment, '更新设备成功');
    } catch (error) {
      next(error);
    }
  }

  static async delete(req: Request, res: Response, next: NextFunction) {
    try {
      const equipment = await Equipment.findByIdAndDelete(req.params.id);
      if (!equipment) {
        sendError(res, '设备不存在', 404);
        return;
      }
      await cacheDel(`${CACHE_PREFIX}:*`);
      sendSuccess(res, null, '删除设备成功');
    } catch (error) {
      next(error);
    }
  }

  static async addMaintenance(req: Request, res: Response, next: NextFunction) {
    try {
      const equipment = await Equipment.findById(req.params.id);
      if (!equipment) {
        sendError(res, '设备不存在', 404);
        return;
      }

      equipment.maintenanceRecords.push({
        ...req.body,
        date: new Date(),
      });
      await equipment.save();
      await cacheDel(`${CACHE_PREFIX}:${req.params.id}`);
      sendSuccess(res, equipment, '添加维护记录成功');
    } catch (error) {
      next(error);
    }
  }

  static async getStatistics(_req: Request, res: Response, next: NextFunction) {
    try {
      const [statusStats, categoryStats, total] = await Promise.all([
        Equipment.aggregate([
          { $group: { _id: '$status', count: { $sum: 1 } } },
        ]),
        Equipment.aggregate([
          { $group: { _id: '$category', count: { $sum: 1 } } },
        ]),
        Equipment.countDocuments(),
      ]);

      sendSuccess(res, { total, statusStats, categoryStats }, '获取设备统计成功');
    } catch (error) {
      next(error);
    }
  }
}
