import "express-async-errors";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import pinoHttp from "pino-http";
import swaggerUi from "swagger-ui-express";
import YAML from "yamljs";
import path from "path";
import { env } from "./config/env";
import { logger } from "./logger";
import { requestId } from "./middleware/requestId";
import { apiRouter } from "./routes";
import { errorHandler, notFound } from "./middleware/errorHandler";

export function createApp() {
  const app = express();

  app.set("trust proxy", true);

  app.use(requestId);
  app.use(
    pinoHttp({
      logger,
      customProps: (req) => ({ requestId: (req as any).requestId })
    })
  );

  app.use(helmet());
  app.use(
    cors({
      origin: env.CORS_ORIGIN === "*" ? true : env.CORS_ORIGIN.split(",").map((s) => s.trim()),
      credentials: true
    })
  );
  app.use(express.json({ limit: "2mb" }));

  const openapiPath = path.join(__dirname, "..", "openapi.yaml");
  const openapiDoc = YAML.load(openapiPath);
  app.use("/docs", swaggerUi.serve, swaggerUi.setup(openapiDoc));

  app.get("/", (_req, res) => res.json({ name: env.APP_NAME, ok: true }));
  app.use("/api", apiRouter);

  app.use(notFound);
  app.use(errorHandler);
  return app;
}

