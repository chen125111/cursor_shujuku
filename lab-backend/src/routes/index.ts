import { Router } from "express";
import { authRouter } from "./auth";
import { devicesRouter } from "./devices";
import { reservationsRouter } from "./reservations";
import { inventoryRouter } from "./inventory";
import { filesRouter } from "./files";
import { healthRouter } from "./health";

export const apiRouter = Router();

apiRouter.use(healthRouter);
apiRouter.use(authRouter);
apiRouter.use(devicesRouter);
apiRouter.use(reservationsRouter);
apiRouter.use(inventoryRouter);
apiRouter.use(filesRouter);

