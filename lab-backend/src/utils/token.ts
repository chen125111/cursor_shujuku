import jwt from "jsonwebtoken";
import { createHash, randomUUID } from "crypto";
import { env } from "../config/env";
import type { JwtUser } from "../middleware/auth";

export type RefreshClaims = {
  sub: string;
  jti: string;
};

export function signAccessToken(user: JwtUser) {
  const expiresIn = env.JWT_ACCESS_EXPIRES_IN as unknown as jwt.SignOptions["expiresIn"];
  return jwt.sign({ sub: user.sub, email: user.email, role: user.role }, env.JWT_ACCESS_SECRET, {
    expiresIn
  });
}

export function signRefreshToken(userId: string) {
  const jti = randomUUID();
  const expiresIn = env.JWT_REFRESH_EXPIRES_IN as unknown as jwt.SignOptions["expiresIn"];
  const token = jwt.sign({ sub: userId, jti } satisfies RefreshClaims, env.JWT_REFRESH_SECRET, {
    expiresIn
  });
  return { token, jti };
}

export function verifyRefreshToken(token: string) {
  return jwt.verify(token, env.JWT_REFRESH_SECRET) as RefreshClaims;
}

export function tokenHash(token: string) {
  return createHash("sha256").update(token).digest("hex");
}

