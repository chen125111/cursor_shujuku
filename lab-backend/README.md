# 实验室管理系统后端（Node.js + Express + TypeScript）

该目录是一个**独立服务**：`lab-backend/`，不会影响仓库里现有的 Python 项目。

## 主要能力

- RESTful API：用户认证、设备管理、预约管理、库存管理、文件上传
- 数据库：PostgreSQL（Prisma）
- 实时通知：WebSocket（Socket.io，基于 JWT 鉴权）
- 日志与错误处理：Pino + 统一错误中间件
- API 文档：Swagger UI（`/docs`）
- 测试：Jest + Supertest（以 mock Prisma 为主，避免强依赖外部数据库）

## 快速启动（PostgreSQL）

1) 启动 Postgres：

```bash
cd lab-backend
docker compose up -d
```

2) 配置环境变量：

```bash
cp .env.example .env
```

3) 初始化 Prisma（首次）：

```bash
npm install
npm run prisma:generate
npm run prisma:migrate
```

4) 启动开发服务：

```bash
npm run dev
```

默认端口：`4000`  
文档地址：`http://localhost:4000/docs`

## 管理员账号

为方便本地体验：**第一个成功注册的用户会被自动设置为 `ADMIN`**（后续注册为 `USER`）。

## WebSocket（Socket.io）

连接时传入 access token：

```js
import { io } from "socket.io-client";
const socket = io("http://localhost:4000", { auth: { token: accessToken } });
socket.on("device.created", console.log);
```

## 目录结构

- `src/app.ts`：Express 应用（中间件、路由、Swagger）
- `src/server.ts`：HTTP + Socket.io 启动入口
- `src/routes/*`：业务路由
- `prisma/schema.prisma`：PostgreSQL 数据模型

