import { Router } from "express";
import { prismaHealthcheck } from "../db/prisma";

export const healthRouter = Router();

healthRouter.get("/health", async (_req, res) => {
  const db = await prismaHealthcheck();
  res.json({ ok: true, db });
});

