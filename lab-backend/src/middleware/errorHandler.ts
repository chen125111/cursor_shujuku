import type { NextFunction, Request, Response } from "express";
import { ZodError } from "zod";
import createError from "http-errors";
import { logger } from "../logger";

export function notFound(req: Request, _res: Response, next: NextFunction) {
  next(createError(404, `Route not found: ${req.method} ${req.path}`));
}

export function errorHandler(err: any, req: Request, res: Response, _next: NextFunction) {
  const status = err.statusCode || err.status || 500;
  const requestId = (req as any).requestId;

  if (err instanceof ZodError) {
    return res.status(400).json({
      requestId,
      error: "VALIDATION_ERROR",
      message: "请求参数校验失败",
      issues: err.issues
    });
  }

  if (status >= 500) {
    logger.error({ err, requestId }, "Unhandled error");
  }

  res.status(status).json({
    requestId,
    error: err.name || "INTERNAL_ERROR",
    message: err.message || "服务器内部错误"
  });
}

