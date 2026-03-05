import { Router } from "express";
import createError from "http-errors";
import { z } from "zod";
import { prisma } from "../db/prisma";
import { requireAuth, requireRole, type AuthRequest } from "../middleware/auth";
import { validateBody, validateQuery } from "../middleware/validate";
import { notifyRole } from "../realtime/io";

export const inventoryRouter = Router();

const listQuery = z.object({
  q: z.string().optional(),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(100).default(20)
});

inventoryRouter.get("/inventory/items", requireAuth, validateQuery(listQuery), async (req, res) => {
  const { q, page, pageSize } = req.query as any;
  const where: any = {};
  if (q) {
    where.OR = [
      { sku: { contains: q, mode: "insensitive" } },
      { name: { contains: q, mode: "insensitive" } }
    ];
  }

  const [items, total] = await Promise.all([
    prisma.inventoryItem.findMany({
      where,
      orderBy: { updatedAt: "desc" },
      skip: (page - 1) * pageSize,
      take: pageSize
    }),
    prisma.inventoryItem.count({ where })
  ]);

  res.json({ items, page, pageSize, total });
});

const createSchema = z.object({
  sku: z.string().min(1).max(64),
  name: z.string().min(1).max(200),
  unit: z.string().min(1).max(32).default("pcs"),
  quantity: z.number().int().min(0).default(0),
  lowStock: z.number().int().min(0).default(0),
  location: z.string().max(200).optional(),
  description: z.string().max(2000).optional()
});

inventoryRouter.post(
  "/inventory/items",
  requireAuth,
  requireRole("ADMIN"),
  validateBody(createSchema),
  async (req, res) => {
    const data = req.body as z.infer<typeof createSchema>;
    try {
      const item = await prisma.inventoryItem.create({ data });
      notifyRole("ADMIN", "inventory.itemCreated", { item });
      res.status(201).json({ item });
    } catch (err: any) {
      if (err?.code === "P2002") throw createError(409, "SKU 已存在");
      throw err;
    }
  }
);

const patchSchema = createSchema.partial().omit({ quantity: true });

inventoryRouter.patch(
  "/inventory/items/:id",
  requireAuth,
  requireRole("ADMIN"),
  validateBody(patchSchema),
  async (req, res) => {
    try {
      const item = await prisma.inventoryItem.update({ where: { id: req.params.id }, data: req.body });
      notifyRole("ADMIN", "inventory.itemUpdated", { item });
      res.json({ item });
    } catch (err: any) {
      if (err?.code === "P2025") throw createError(404, "库存物料不存在");
      if (err?.code === "P2002") throw createError(409, "SKU 已存在");
      throw err;
    }
  }
);

inventoryRouter.get("/inventory/items/:id", requireAuth, async (req, res) => {
  const item = await prisma.inventoryItem.findUnique({ where: { id: req.params.id } });
  if (!item) throw createError(404, "库存物料不存在");
  res.json({ item });
});

const adjustSchema = z.object({
  delta: z.number().int(),
  reason: z.string().max(1000).optional()
});

inventoryRouter.post(
  "/inventory/items/:id/adjust",
  requireAuth,
  validateBody(adjustSchema),
  async (req: AuthRequest, res) => {
    const { delta, reason } = req.body as z.infer<typeof adjustSchema>;
    if (delta === 0) throw createError(400, "delta 不能为 0");

    const result = await prisma.$transaction(async (tx) => {
      const item = await tx.inventoryItem.findUnique({ where: { id: req.params.id } });
      if (!item) throw createError(404, "库存物料不存在");
      const nextQty = item.quantity + delta;
      if (nextQty < 0) throw createError(400, "库存不足");

      const updated = await tx.inventoryItem.update({
        where: { id: item.id },
        data: { quantity: nextQty }
      });
      const op = await tx.inventoryOp.create({
        data: { itemId: item.id, userId: req.user!.sub, delta, reason }
      });
      return { item: updated, op };
    });

    notifyRole("ADMIN", "inventory.adjusted", result);
    if (result.item.lowStock > 0 && result.item.quantity <= result.item.lowStock) {
      notifyRole("ADMIN", "inventory.lowStock", { item: result.item });
    }
    res.json(result);
  }
);

inventoryRouter.get(
  "/inventory/items/:id/ops",
  requireAuth,
  validateQuery(z.object({ page: z.coerce.number().int().min(1).default(1), pageSize: z.coerce.number().int().min(1).max(100).default(20) })),
  async (req, res) => {
    const { page, pageSize } = req.query as any;
    const where = { itemId: req.params.id };
    const [items, total] = await Promise.all([
      prisma.inventoryOp.findMany({
        where,
        orderBy: { createdAt: "desc" },
        skip: (page - 1) * pageSize,
        take: pageSize,
        include: { user: { select: { id: true, email: true, name: true } } }
      }),
      prisma.inventoryOp.count({ where })
    ]);
    res.json({ items, page, pageSize, total });
  }
);

