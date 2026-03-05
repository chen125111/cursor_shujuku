import { Router } from "express";
import createError from "http-errors";
import { z } from "zod";
import { prisma } from "../db/prisma";
import { validateBody } from "../middleware/validate";
import { hashPassword, verifyPassword } from "../utils/password";
import { requireAuth, type AuthRequest } from "../middleware/auth";
import { signAccessToken, signRefreshToken, tokenHash, verifyRefreshToken } from "../utils/token";

export const authRouter = Router();

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(72),
  name: z.string().min(1).max(100).optional()
});

authRouter.post("/auth/register", validateBody(registerSchema), async (req, res) => {
  const { email, password, name } = req.body as z.infer<typeof registerSchema>;

  const exists = await prisma.user.findUnique({ where: { email } });
  if (exists) throw createError(409, "邮箱已注册");

  const usersCount = await prisma.user.count();
  const passwordHash = await hashPassword(password);
  const user = await prisma.user.create({
    data: { email, passwordHash, name, role: usersCount === 0 ? "ADMIN" : "USER" },
    select: { id: true, email: true, role: true, name: true }
  });

  const jwtUser = { sub: user.id, email: user.email, role: user.role };
  const accessToken = signAccessToken(jwtUser);
  const refresh = signRefreshToken(user.id);

  const decoded = verifyRefreshToken(refresh.token);
  const expiresAt = new Date((decoded as any).exp * 1000);
  await prisma.refreshToken.create({
    data: { userId: user.id, tokenHash: tokenHash(refresh.token), expiresAt }
  });

  res.status(201).json({ user, accessToken, refreshToken: refresh.token });
});

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1)
});

authRouter.post("/auth/login", validateBody(loginSchema), async (req, res) => {
  const { email, password } = req.body as z.infer<typeof loginSchema>;

  const user = await prisma.user.findUnique({ where: { email } });
  if (!user) throw createError(401, "邮箱或密码错误");

  const ok = await verifyPassword(password, user.passwordHash);
  if (!ok) throw createError(401, "邮箱或密码错误");

  const jwtUser = { sub: user.id, email: user.email, role: user.role };
  const accessToken = signAccessToken(jwtUser);
  const refresh = signRefreshToken(user.id);

  const decoded = verifyRefreshToken(refresh.token);
  const expiresAt = new Date((decoded as any).exp * 1000);
  await prisma.refreshToken.create({
    data: { userId: user.id, tokenHash: tokenHash(refresh.token), expiresAt }
  });

  res.json({
    user: { id: user.id, email: user.email, role: user.role, name: user.name },
    accessToken,
    refreshToken: refresh.token
  });
});

const refreshSchema = z.object({
  refreshToken: z.string().min(1)
});

authRouter.post("/auth/refresh", validateBody(refreshSchema), async (req, res) => {
  const { refreshToken } = req.body as z.infer<typeof refreshSchema>;

  let claims: { sub: string; jti: string; exp?: number };
  try {
    claims = verifyRefreshToken(refreshToken) as any;
  } catch {
    throw createError(401, "refresh token 无效或已过期");
  }

  const hashed = tokenHash(refreshToken);
  const record = await prisma.refreshToken.findUnique({ where: { tokenHash: hashed } });
  if (!record || record.revokedAt) throw createError(401, "refresh token 已失效");
  if (record.expiresAt.getTime() < Date.now()) throw createError(401, "refresh token 已过期");

  await prisma.refreshToken.update({
    where: { tokenHash: hashed },
    data: { revokedAt: new Date() }
  });

  const user = await prisma.user.findUnique({ where: { id: claims.sub } });
  if (!user) throw createError(401, "用户不存在");

  const jwtUser = { sub: user.id, email: user.email, role: user.role };
  const accessToken = signAccessToken(jwtUser);

  const nextRefresh = signRefreshToken(user.id);
  const decoded = verifyRefreshToken(nextRefresh.token);
  const expiresAt = new Date((decoded as any).exp * 1000);
  await prisma.refreshToken.create({
    data: { userId: user.id, tokenHash: tokenHash(nextRefresh.token), expiresAt }
  });

  res.json({ accessToken, refreshToken: nextRefresh.token });
});

authRouter.post("/auth/logout", validateBody(refreshSchema), async (req, res) => {
  const { refreshToken } = req.body as z.infer<typeof refreshSchema>;
  const hashed = tokenHash(refreshToken);
  await prisma.refreshToken.updateMany({
    where: { tokenHash: hashed, revokedAt: null },
    data: { revokedAt: new Date() }
  });
  res.json({ ok: true });
});

authRouter.get("/auth/me", requireAuth, async (req: AuthRequest, res) => {
  const userId = req.user!.sub;
  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: { id: true, email: true, role: true, name: true, createdAt: true }
  });
  if (!user) throw createError(404, "用户不存在");
  res.json({ user });
});

