import request from "supertest";
import { createApp } from "../src/app";

jest.mock("../src/db/prisma", () => ({
  prismaHealthcheck: jest.fn(async () => true)
}));

describe("GET /api/health", () => {
  it("returns ok", async () => {
    const app = createApp();
    const res = await request(app).get("/api/health");
    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
    expect(res.body.db).toBe(true);
  });
});

