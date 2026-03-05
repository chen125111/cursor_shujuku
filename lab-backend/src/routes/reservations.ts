import { Router } from "express";
import createError from "http-errors";
import { z } from "zod";
import { prisma } from "../db/prisma";
import { requireAuth, requireRole, type AuthRequest } from "../middleware/auth";
import { validateBody, validateQuery } from "../middleware/validate";
import { notifyRole, notifyUser } from "../realtime/io";

export const reservationsRouter = Router();

const listQuery = z.object({
  deviceId: z.string().optional(),
  status: z.string().optional(),
  from: z.string().datetime().optional(),
  to: z.string().datetime().optional(),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(100).default(20)
});

reservationsRouter.get("/reservations", requireAuth, validateQuery(listQuery), async (req: AuthRequest, res) => {
  const { deviceId, status, from, to, page, pageSize } = req.query as any;

  const where: any = {};
  if (deviceId) where.deviceId = deviceId;
  if (status) where.status = status;
  if (from || to) {
    where.AND = [];
    if (from) where.AND.push({ endTime: { gte: new Date(from) } });
    if (to) where.AND.push({ startTime: { lte: new Date(to) } });
  }

  if (req.user!.role !== "ADMIN") {
    where.userId = req.user!.sub;
  }

  const [items, total] = await Promise.all([
    prisma.reservation.findMany({
      where,
      include: { device: true, user: { select: { id: true, email: true, name: true } } },
      orderBy: { startTime: "desc" },
      skip: (page - 1) * pageSize,
      take: pageSize
    }),
    prisma.reservation.count({ where })
  ]);

  res.json({ items, page, pageSize, total });
});

const createSchema = z.object({
  deviceId: z.string().min(1),
  startTime: z.string().datetime(),
  endTime: z.string().datetime(),
  purpose: z.string().max(2000).optional()
});

reservationsRouter.post("/reservations", requireAuth, validateBody(createSchema), async (req: AuthRequest, res) => {
  const { deviceId, startTime, endTime, purpose } = req.body as z.infer<typeof createSchema>;
  const start = new Date(startTime);
  const end = new Date(endTime);
  if (!(start.getTime() < end.getTime())) throw createError(400, "开始时间必须早于结束时间");

  const device = await prisma.device.findUnique({ where: { id: deviceId } });
  if (!device) throw createError(404, "设备不存在");

  const overlap = await prisma.reservation.findFirst({
    where: {
      deviceId,
      status: "APPROVED",
      startTime: { lt: end },
      endTime: { gt: start }
    }
  });
  if (overlap) throw createError(409, "该时间段已被预约");

  const reservation = await prisma.reservation.create({
    data: {
      deviceId,
      userId: req.user!.sub,
      startTime: start,
      endTime: end,
      purpose
    },
    include: { device: true }
  });

  notifyRole("ADMIN", "reservation.created", { reservation });
  res.status(201).json({ reservation });
});

reservationsRouter.get("/reservations/:id", requireAuth, async (req: AuthRequest, res) => {
  const reservation = await prisma.reservation.findUnique({
    where: { id: req.params.id },
    include: { device: true, user: { select: { id: true, email: true, name: true } } }
  });
  if (!reservation) throw createError(404, "预约不存在");
  if (req.user!.role !== "ADMIN" && reservation.userId !== req.user!.sub) throw createError(403, "权限不足");
  res.json({ reservation });
});

reservationsRouter.post(
  "/reservations/:id/cancel",
  requireAuth,
  async (req: AuthRequest, res) => {
    const reservation = await prisma.reservation.findUnique({ where: { id: req.params.id } });
    if (!reservation) throw createError(404, "预约不存在");
    if (req.user!.role !== "ADMIN" && reservation.userId !== req.user!.sub) throw createError(403, "权限不足");
    if (["CANCELLED", "REJECTED"].includes(reservation.status)) return res.json({ reservation });

    const updated = await prisma.reservation.update({
      where: { id: reservation.id },
      data: { status: "CANCELLED" }
    });

    notifyRole("ADMIN", "reservation.cancelled", { reservation: updated });
    notifyUser(updated.userId, "reservation.cancelled", { reservation: updated });
    res.json({ reservation: updated });
  }
);

reservationsRouter.post(
  "/reservations/:id/approve",
  requireAuth,
  requireRole("ADMIN"),
  async (req, res) => {
    const reservation = await prisma.reservation.findUnique({ where: { id: req.params.id } });
    if (!reservation) throw createError(404, "预约不存在");
    if (reservation.status !== "PENDING") throw createError(400, "只能审批待处理预约");

    const overlap = await prisma.reservation.findFirst({
      where: {
        deviceId: reservation.deviceId,
        status: "APPROVED",
        startTime: { lt: reservation.endTime },
        endTime: { gt: reservation.startTime }
      }
    });
    if (overlap) throw createError(409, "审批失败：该时间段已被其它预约占用");

    const updated = await prisma.reservation.update({
      where: { id: reservation.id },
      data: { status: "APPROVED" },
      include: { device: true }
    });

    notifyRole("ADMIN", "reservation.approved", { reservation: updated });
    notifyUser(updated.userId, "reservation.approved", { reservation: updated });
    res.json({ reservation: updated });
  }
);

const rejectSchema = z.object({ reason: z.string().max(1000).optional() });

reservationsRouter.post(
  "/reservations/:id/reject",
  requireAuth,
  requireRole("ADMIN"),
  validateBody(rejectSchema),
  async (req, res) => {
    const reservation = await prisma.reservation.findUnique({ where: { id: req.params.id } });
    if (!reservation) throw createError(404, "预约不存在");
    if (reservation.status !== "PENDING") throw createError(400, "只能审批待处理预约");

    const updated = await prisma.reservation.update({
      where: { id: reservation.id },
      data: { status: "REJECTED", purpose: reservation.purpose } // 保持字段不变
    });

    notifyRole("ADMIN", "reservation.rejected", { reservation: updated, reason: (req.body as any).reason });
    notifyUser(updated.userId, "reservation.rejected", { reservation: updated, reason: (req.body as any).reason });
    res.json({ reservation: updated });
  }
);

