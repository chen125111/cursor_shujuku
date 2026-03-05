import request from "supertest";

describe("Auth", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.resetModules();
  });

  it("registers first user as ADMIN", async () => {
    const prismaMock = {
      user: {
        findUnique: jest.fn(),
        create: jest.fn(),
        count: jest.fn()
      },
      refreshToken: {
        create: jest.fn(),
        findUnique: jest.fn(),
        update: jest.fn(),
        updateMany: jest.fn()
      }
    };
    jest.doMock("../src/db/prisma", () => ({ prisma: prismaMock }));
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { createApp } = require("../src/app");

    prismaMock.user.findUnique.mockResolvedValue(null);
    prismaMock.user.count.mockResolvedValue(0);
    prismaMock.user.create.mockResolvedValue({ id: "u1", email: "a@b.com", role: "ADMIN", name: "A" });
    prismaMock.refreshToken.create.mockResolvedValue({ id: "rt1" });

    const app = createApp();
    const res = await request(app)
      .post("/api/auth/register")
      .send({ email: "a@b.com", password: "password123", name: "A" });

    expect(res.status).toBe(201);
    expect(res.body.user.role).toBe("ADMIN");
    expect(res.body.accessToken).toBeTruthy();
    expect(res.body.refreshToken).toBeTruthy();
  });

  it("rejects duplicate email on register", async () => {
    const prismaMock = {
      user: {
        findUnique: jest.fn(),
        create: jest.fn(),
        count: jest.fn()
      },
      refreshToken: {
        create: jest.fn(),
        findUnique: jest.fn(),
        update: jest.fn(),
        updateMany: jest.fn()
      }
    };
    jest.doMock("../src/db/prisma", () => ({ prisma: prismaMock }));
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { createApp } = require("../src/app");

    prismaMock.user.findUnique.mockResolvedValue({ id: "u1" });
    const app = createApp();
    const res = await request(app)
      .post("/api/auth/register")
      .send({ email: "a@b.com", password: "password123" });
    expect(res.status).toBe(409);
  });
});

