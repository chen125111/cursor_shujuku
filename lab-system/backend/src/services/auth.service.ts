import jwt from 'jsonwebtoken';
import { config } from '../config';
import { User, IUser } from '../models';
import { JwtPayload, UserRole } from '../types';
import { AppError } from '../middleware/errorHandler';

export class AuthService {
  static generateTokens(user: IUser) {
    const payload: JwtPayload = {
      userId: user._id as string,
      email: user.email,
      role: user.role,
    };

    const accessToken = jwt.sign(payload, config.jwt.secret, {
      expiresIn: config.jwt.expiresIn,
    });

    const refreshToken = jwt.sign(payload, config.jwt.refreshSecret, {
      expiresIn: config.jwt.refreshExpiresIn,
    });

    return { accessToken, refreshToken };
  }

  static async register(data: {
    username: string;
    email: string;
    password: string;
    displayName: string;
    department: string;
    phone?: string;
  }) {
    const existingUser = await User.findOne({
      $or: [{ email: data.email }, { username: data.username }],
    });

    if (existingUser) {
      throw new AppError('邮箱或用户名已存在', 409);
    }

    const user = new User({
      ...data,
      role: UserRole.STUDENT,
    });
    await user.save();

    const tokens = this.generateTokens(user);
    user.refreshToken = tokens.refreshToken;
    await user.save();

    return { user, ...tokens };
  }

  static async login(email: string, password: string) {
    const user = await User.findOne({ email, isActive: true }).select(
      '+password +refreshToken'
    );

    if (!user || !(await user.comparePassword(password))) {
      throw new AppError('邮箱或密码错误', 401);
    }

    const tokens = this.generateTokens(user);
    user.refreshToken = tokens.refreshToken;
    user.lastLoginAt = new Date();
    await user.save();

    return { user, ...tokens };
  }

  static async refreshToken(token: string) {
    try {
      const decoded = jwt.verify(token, config.jwt.refreshSecret) as JwtPayload;
      const user = await User.findById(decoded.userId).select('+refreshToken');

      if (!user || user.refreshToken !== token) {
        throw new AppError('无效的刷新令牌', 401);
      }

      const tokens = this.generateTokens(user);
      user.refreshToken = tokens.refreshToken;
      await user.save();

      return tokens;
    } catch {
      throw new AppError('无效的刷新令牌', 401);
    }
  }

  static async logout(userId: string) {
    await User.findByIdAndUpdate(userId, { refreshToken: null });
  }

  static async changePassword(
    userId: string,
    currentPassword: string,
    newPassword: string
  ) {
    const user = await User.findById(userId).select('+password');
    if (!user) throw new AppError('用户不存在', 404);

    if (!(await user.comparePassword(currentPassword))) {
      throw new AppError('当前密码错误', 400);
    }

    user.password = newPassword;
    await user.save();
  }
}
