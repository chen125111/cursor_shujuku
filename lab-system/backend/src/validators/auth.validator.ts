import { z } from 'zod';

export const loginSchema = z.object({
  body: z.object({
    email: z.string().email('请输入有效的邮箱地址'),
    password: z.string().min(6, '密码至少6个字符'),
  }),
});

export const registerSchema = z.object({
  body: z.object({
    username: z
      .string()
      .min(3, '用户名至少3个字符')
      .max(30, '用户名最多30个字符')
      .regex(/^[a-zA-Z0-9_]+$/, '用户名只能包含字母、数字和下划线'),
    email: z.string().email('请输入有效的邮箱地址'),
    password: z
      .string()
      .min(6, '密码至少6个字符')
      .max(50, '密码最多50个字符'),
    displayName: z.string().min(1, '请输入显示名称'),
    department: z.string().min(1, '请选择部门'),
    phone: z.string().optional(),
  }),
});

export const refreshTokenSchema = z.object({
  body: z.object({
    refreshToken: z.string().min(1, '请提供刷新令牌'),
  }),
});

export const changePasswordSchema = z.object({
  body: z.object({
    currentPassword: z.string().min(6),
    newPassword: z.string().min(6).max(50),
  }),
});
