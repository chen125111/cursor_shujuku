import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";
import createError from "http-errors";
import { env } from "../config/env";

export type JwtUser = { sub: string; role: "ADMIN" | "USER"; email: string };

export interface AuthRequest extends Request {
  user?: JwtUser;
}

export function requireAuth(req: AuthRequest, _res: Response, next: NextFunction) {
  const auth = req.header("authorization");
  const token = auth?.startsWith("Bearer ") ? auth.slice("Bearer ".length) : undefined;
  if (!token) return next(createError(401, "缺少访问令牌"));

  try {
    const payload = jwt.verify(token, env.JWT_ACCESS_SECRET) as any;
    req.user = { sub: payload.sub, role: payload.role, email: payload.email };
    return next();
  } catch {
    return next(createError(401, "访问令牌无效或已过期"));
  }
}

export function requireRole(role: JwtUser["role"]) {
  return (req: AuthRequest, _res: Response, next: NextFunction) => {
    if (!req.user) return next(createError(401, "未登录"));
    if (req.user.role !== role) return next(createError(403, "权限不足"));
    next();
  };
}

