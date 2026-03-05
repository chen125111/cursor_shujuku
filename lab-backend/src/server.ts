import http from "http";
import fs from "fs/promises";
import { createApp } from "./app";
import { env } from "./config/env";
import { logger } from "./logger";
import { initIo } from "./realtime/io";

async function main() {
  await fs.mkdir(env.UPLOAD_DIR, { recursive: true });

  const app = createApp();
  const server = http.createServer(app);
  initIo(server);

  server.listen(env.PORT, () => {
    logger.info({ port: env.PORT }, "server started");
  });
}

main().catch((err) => {
  logger.error({ err }, "fatal");
  process.exit(1);
});

