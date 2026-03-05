import pino from "pino";
import { env } from "./config/env";

export const logger = pino({
  level: env.NODE_ENV === "production" ? "info" : "debug",
  redact: {
    paths: ["req.headers.authorization", "password", "*.password", "token", "*.token"],
    remove: true
  }
});

