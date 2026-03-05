process.env.NODE_ENV = "test";
process.env.PORT = "4001";
process.env.APP_NAME = "lab-management-backend-test";
process.env.DATABASE_URL = process.env.DATABASE_URL ?? "postgresql://user:pass@localhost:5432/lab?schema=public";
process.env.JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET ?? "012345678901234567890123456789";
process.env.JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET ?? "012345678901234567890123456789";
process.env.JWT_ACCESS_EXPIRES_IN = process.env.JWT_ACCESS_EXPIRES_IN ?? "15m";
process.env.JWT_REFRESH_EXPIRES_IN = process.env.JWT_REFRESH_EXPIRES_IN ?? "7d";
process.env.CORS_ORIGIN = process.env.CORS_ORIGIN ?? "*";
process.env.UPLOAD_DIR = process.env.UPLOAD_DIR ?? "./.test-uploads";
process.env.MAX_UPLOAD_MB = process.env.MAX_UPLOAD_MB ?? "5";

