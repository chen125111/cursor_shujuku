import { Request, Response, NextFunction } from 'express';
import { Inventory } from '../models';
import { AuthRequest } from '../types';
import { sendSuccess, sendError, sendPaginated } from '../utils/response';
import { NotificationService } from '../services/notification.service';

export class InventoryController {
  static async getAll(req: Request, res: Response, next: NextFunction) {
    try {
      const {
        page = 1,
        limit = 20,
        search,
        category,
        department,
        lowStock,
        sortBy = 'createdAt',
        sortOrder = 'desc',
      } = req.query;

      const filter: Record<string, unknown> = {};
      if (search) {
        filter.$or = [
          { name: { $regex: search, $options: 'i' } },
          { code: { $regex: search, $options: 'i' } },
        ];
      }
      if (category) filter.category = category;
      if (department) filter.department = department;
      if (lowStock === 'true') {
        filter.$expr = { $lte: ['$quantity', '$minQuantity'] };
      }

      const pageNum = Number(page);
      const limitNum = Number(limit);

      const total = await Inventory.countDocuments(filter);
      const items = await Inventory.find(filter)
        .populate('manager', 'displayName email')
        .sort({ [sortBy as string]: sortOrder === 'asc' ? 1 : -1 })
        .skip((pageNum - 1) * limitNum)
        .limit(limitNum);

      sendPaginated(res, items, total, pageNum, limitNum, '获取库存列表成功');
    } catch (error) {
      next(error);
    }
  }

  static async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const item = await Inventory.findById(req.params.id)
        .populate('manager', 'displayName email')
        .populate('usageRecords.user', 'displayName');
      if (!item) {
        sendError(res, '物品不存在', 404);
        return;
      }
      sendSuccess(res, item, '获取物品详情成功');
    } catch (error) {
      next(error);
    }
  }

  static async create(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const item = new Inventory({
        ...req.body,
        manager: req.user?.userId,
      });
      await item.save();
      sendSuccess(res, item, '创建物品成功', 201);
    } catch (error) {
      next(error);
    }
  }

  static async update(req: Request, res: Response, next: NextFunction) {
    try {
      const item = await Inventory.findByIdAndUpdate(
        req.params.id,
        req.body,
        { new: true, runValidators: true }
      );
      if (!item) {
        sendError(res, '物品不存在', 404);
        return;
      }
      sendSuccess(res, item, '更新物品成功');
    } catch (error) {
      next(error);
    }
  }

  static async delete(req: Request, res: Response, next: NextFunction) {
    try {
      const item = await Inventory.findByIdAndDelete(req.params.id);
      if (!item) {
        sendError(res, '物品不存在', 404);
        return;
      }
      sendSuccess(res, null, '删除物品成功');
    } catch (error) {
      next(error);
    }
  }

  static async recordUsage(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const { quantity, type, notes } = req.body;
      const item = await Inventory.findById(req.params.id);
      if (!item) {
        sendError(res, '物品不存在', 404);
        return;
      }

      if (type === 'out' && item.quantity < quantity) {
        sendError(res, '库存不足', 400);
        return;
      }

      item.quantity += type === 'in' ? quantity : -quantity;
      item.usageRecords.push({
        user: req.user!.userId as any,
        quantity,
        type,
        date: new Date(),
        notes,
      });

      await item.save();

      if (item.quantity <= item.minQuantity) {
        await NotificationService.notifyLowStock(
          item.manager.toString(),
          item.name,
          item.quantity,
          item._id as string
        );
      }

      sendSuccess(res, item, type === 'in' ? '入库成功' : '出库成功');
    } catch (error) {
      next(error);
    }
  }

  static async getStatistics(_req: Request, res: Response, next: NextFunction) {
    try {
      const [categoryStats, lowStockCount, totalValue, totalItems] =
        await Promise.all([
          Inventory.aggregate([
            { $group: { _id: '$category', count: { $sum: 1 }, totalQty: { $sum: '$quantity' } } },
          ]),
          Inventory.countDocuments({ $expr: { $lte: ['$quantity', '$minQuantity'] } }),
          Inventory.aggregate([
            { $group: { _id: null, total: { $sum: { $multiply: ['$quantity', '$unitPrice'] } } } },
          ]),
          Inventory.countDocuments(),
        ]);

      sendSuccess(res, {
        totalItems,
        lowStockCount,
        totalValue: totalValue[0]?.total || 0,
        categoryStats,
      }, '获取库存统计成功');
    } catch (error) {
      next(error);
    }
  }
}
