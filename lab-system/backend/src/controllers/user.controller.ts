import { Request, Response, NextFunction } from 'express';
import { User } from '../models';
import { AuthRequest } from '../types';
import { sendSuccess, sendError, sendPaginated } from '../utils/response';

export class UserController {
  static async getAll(req: Request, res: Response, next: NextFunction) {
    try {
      const {
        page = 1,
        limit = 20,
        search,
        role,
        department,
        sortBy = 'createdAt',
        sortOrder = 'desc',
      } = req.query;

      const filter: Record<string, unknown> = {};
      if (search) {
        filter.$or = [
          { username: { $regex: search, $options: 'i' } },
          { displayName: { $regex: search, $options: 'i' } },
          { email: { $regex: search, $options: 'i' } },
        ];
      }
      if (role) filter.role = role;
      if (department) filter.department = department;

      const pageNum = Number(page);
      const limitNum = Number(limit);

      const total = await User.countDocuments(filter);
      const users = await User.find(filter)
        .sort({ [sortBy as string]: sortOrder === 'asc' ? 1 : -1 })
        .skip((pageNum - 1) * limitNum)
        .limit(limitNum);

      sendPaginated(res, users, total, pageNum, limitNum, '获取用户列表成功');
    } catch (error) {
      next(error);
    }
  }

  static async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const user = await User.findById(req.params.id);
      if (!user) {
        sendError(res, '用户不存在', 404);
        return;
      }
      sendSuccess(res, user, '获取用户信息成功');
    } catch (error) {
      next(error);
    }
  }

  static async update(req: AuthRequest, res: Response, next: NextFunction) {
    try {
      const { displayName, department, phone, avatar } = req.body;
      const user = await User.findByIdAndUpdate(
        req.params.id,
        { displayName, department, phone, avatar },
        { new: true, runValidators: true }
      );
      if (!user) {
        sendError(res, '用户不存在', 404);
        return;
      }
      sendSuccess(res, user, '更新用户信息成功');
    } catch (error) {
      next(error);
    }
  }

  static async updateRole(req: Request, res: Response, next: NextFunction) {
    try {
      const { role } = req.body;
      const user = await User.findByIdAndUpdate(
        req.params.id,
        { role },
        { new: true, runValidators: true }
      );
      if (!user) {
        sendError(res, '用户不存在', 404);
        return;
      }
      sendSuccess(res, user, '更新用户角色成功');
    } catch (error) {
      next(error);
    }
  }

  static async toggleActive(req: Request, res: Response, next: NextFunction) {
    try {
      const user = await User.findById(req.params.id);
      if (!user) {
        sendError(res, '用户不存在', 404);
        return;
      }
      user.isActive = !user.isActive;
      await user.save();
      sendSuccess(res, user, user.isActive ? '用户已启用' : '用户已禁用');
    } catch (error) {
      next(error);
    }
  }

  static async getDepartments(_req: Request, res: Response, next: NextFunction) {
    try {
      const departments = await User.distinct('department');
      sendSuccess(res, departments, '获取部门列表成功');
    } catch (error) {
      next(error);
    }
  }
}
