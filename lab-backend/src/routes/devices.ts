import { Router } from "express";
import createError from "http-errors";
import { z } from "zod";
import { prisma } from "../db/prisma";
import { requireAuth, requireRole, type AuthRequest } from "../middleware/auth";
import { validateBody, validateQuery } from "../middleware/validate";
import { notifyRole } from "../realtime/io";

export const devicesRouter = Router();

const listQuery = z.object({
  status: z.string().optional(),
  q: z.string().optional(),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(100).default(20)
});

devicesRouter.get("/devices", requireAuth, validateQuery(listQuery), async (req, res) => {
  const { status, q, page, pageSize } = req.query as any;

  const where: any = {};
  if (status) where.status = status;
  if (q) {
    where.OR = [
      { code: { contains: q, mode: "insensitive" } },
      { name: { contains: q, mode: "insensitive" } },
      { model: { contains: q, mode: "insensitive" } }
    ];
  }

  const [items, total] = await Promise.all([
    prisma.device.findMany({
      where,
      orderBy: { updatedAt: "desc" },
      skip: (page - 1) * pageSize,
      take: pageSize
    }),
    prisma.device.count({ where })
  ]);

  res.json({ items, page, pageSize, total });
});

const createSchema = z.object({
  code: z.string().min(1).max(50),
  name: z.string().min(1).max(200),
  model: z.string().max(200).optional(),
  location: z.string().max(200).optional(),
  status: z.string().default("AVAILABLE"),
  description: z.string().max(2000).optional()
});

devicesRouter.post(
  "/devices",
  requireAuth,
  requireRole("ADMIN"),
  validateBody(createSchema),
  async (req, res) => {
    const data = req.body as z.infer<typeof createSchema>;
    try {
      const device = await prisma.device.create({ data });
      notifyRole("ADMIN", "device.created", { device });
      res.status(201).json({ device });
    } catch (err: any) {
      if (err?.code === "P2002") throw createError(409, "设备编码已存在");
      throw err;
    }
  }
);

devicesRouter.get("/devices/:id", requireAuth, async (req, res) => {
  const device = await prisma.device.findUnique({ where: { id: req.params.id } });
  if (!device) throw createError(404, "设备不存在");
  res.json({ device });
});

const patchSchema = createSchema.partial();

devicesRouter.patch(
  "/devices/:id",
  requireAuth,
  requireRole("ADMIN"),
  validateBody(patchSchema),
  async (req, res) => {
    try {
      const device = await prisma.device.update({ where: { id: req.params.id }, data: req.body });
      notifyRole("ADMIN", "device.updated", { device });
      res.json({ device });
    } catch (err: any) {
      if (err?.code === "P2025") throw createError(404, "设备不存在");
      if (err?.code === "P2002") throw createError(409, "设备编码已存在");
      throw err;
    }
  }
);

devicesRouter.delete(
  "/devices/:id",
  requireAuth,
  requireRole("ADMIN"),
  async (req: AuthRequest, res) => {
    try {
      const device = await prisma.device.delete({ where: { id: req.params.id } });
      notifyRole("ADMIN", "device.deleted", { id: device.id });
      res.json({ ok: true });
    } catch (err: any) {
      if (err?.code === "P2025") throw createError(404, "设备不存在");
      throw err;
    }
  }
);

