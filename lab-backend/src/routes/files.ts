import { Router } from "express";
import createError from "http-errors";
import multer from "multer";
import path from "path";
import fs from "fs/promises";
import { createReadStream } from "fs";
import { env } from "../config/env";
import { prisma } from "../db/prisma";
import { requireAuth, type AuthRequest } from "../middleware/auth";

export const filesRouter = Router();

const storage = multer.diskStorage({
  destination: async (_req, _file, cb) => {
    try {
      await fs.mkdir(env.UPLOAD_DIR, { recursive: true });
      cb(null, env.UPLOAD_DIR);
    } catch (err) {
      cb(err as any, env.UPLOAD_DIR);
    }
  },
  filename: (_req, file, cb) => {
    const safeBase = path
      .basename(file.originalname)
      .replace(/[^\w.\-()]/g, "_")
      .slice(0, 80);
    const name = `${Date.now()}-${Math.random().toString(16).slice(2)}-${safeBase}`;
    cb(null, name);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: env.MAX_UPLOAD_MB * 1024 * 1024 }
});

filesRouter.post("/files", requireAuth, upload.single("file"), async (req: AuthRequest, res) => {
  const f = req.file;
  if (!f) throw createError(400, "缺少文件字段 file");

  const asset = await prisma.fileAsset.create({
    data: {
      ownerId: req.user!.sub,
      original: f.originalname,
      mimeType: f.mimetype,
      size: f.size,
      path: f.path
    }
  });

  res.status(201).json({ file: asset });
});

filesRouter.get("/files/:id", requireAuth, async (req: AuthRequest, res) => {
  const asset = await prisma.fileAsset.findUnique({ where: { id: req.params.id } });
  if (!asset) throw createError(404, "文件不存在");
  if (req.user!.role !== "ADMIN" && asset.ownerId !== req.user!.sub) throw createError(403, "权限不足");

  res.setHeader("content-type", asset.mimeType);
  res.setHeader("content-disposition", `attachment; filename="${encodeURIComponent(asset.original)}"`);
  createReadStream(asset.path).pipe(res);
});

