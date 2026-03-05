import type { Server as HttpServer } from "http";
import { Server } from "socket.io";
import jwt from "jsonwebtoken";
import { env } from "../config/env";
import { logger } from "../logger";

type SocketUser = { sub: string; role: "ADMIN" | "USER"; email?: string };

let io: Server | undefined;

export function initIo(server: HttpServer) {
  io = new Server(server, {
    cors: {
      origin: env.CORS_ORIGIN === "*" ? true : env.CORS_ORIGIN.split(",").map((s) => s.trim()),
      credentials: true
    }
  });

  io.use((socket, next) => {
    const token =
      socket.handshake.auth?.token ||
      (typeof socket.handshake.headers.authorization === "string" &&
      socket.handshake.headers.authorization.startsWith("Bearer ")
        ? socket.handshake.headers.authorization.slice("Bearer ".length)
        : undefined);

    if (!token) return next(new Error("UNAUTHORIZED"));

    try {
      const payload = jwt.verify(token, env.JWT_ACCESS_SECRET) as any;
      socket.data.user = { sub: payload.sub, role: payload.role, email: payload.email } satisfies SocketUser;
      return next();
    } catch {
      return next(new Error("UNAUTHORIZED"));
    }
  });

  io.on("connection", (socket) => {
    const user = socket.data.user as SocketUser | undefined;
    if (!user) return;

    socket.join(`user:${user.sub}`);
    socket.join(`role:${user.role}`);

    socket.on("disconnect", (reason) => {
      logger.debug({ reason, userId: user.sub }, "socket disconnected");
    });
  });

  return io;
}

export function getIo() {
  if (!io) throw new Error("Socket.io not initialized");
  return io;
}

export function notifyUser(userId: string, event: string, payload: unknown) {
  if (!io) return;
  io.to(`user:${userId}`).emit(event, payload);
}

export function notifyRole(role: "ADMIN" | "USER", event: string, payload: unknown) {
  if (!io) return;
  io.to(`role:${role}`).emit(event, payload);
}

