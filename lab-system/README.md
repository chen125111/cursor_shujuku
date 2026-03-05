# 实验室管理系统 (Lab Management System)

现代化的实验室资源管理平台，为高校及科研机构提供设备管理、预约系统、库存管理等一站式解决方案。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + Vite 5 |
| 后端 | Node.js 20 + Express + TypeScript |
| 数据库 | MongoDB 7 / PostgreSQL 16 |
| 缓存 | Redis 7 |
| 实时通信 | Socket.IO |
| 部署 | Docker + Nginx + GitHub Actions CI/CD |

## 功能模块

- **用户管理** — 注册/登录、角色权限 (Admin/Manager/Researcher/Student)
- **设备管理** — 设备台账、状态跟踪、维护记录、统计分析
- **预约系统** — 在线预约、冲突检测、审批流程、日历视图
- **库存管理** — 出入库记录、库存预警、分类统计、总价值管理
- **通知系统** — 实时推送、未读管理、多类型通知模板

## 快速开始

### 开发环境

```bash
# 1. 启动基础设施
docker compose -f docker-compose.dev.yml up -d

# 2. 启动后端 (端口 3000)
cd backend
cp .env.example .env
npm install
npm run dev

# 3. 启动前端 (端口 5173)
cd frontend
cp .env.example .env
npm install
npm run dev
```

### 生产部署

```bash
docker compose up -d --build
```

## 项目结构

```
lab-system/
├── frontend/          # React + TypeScript + Ant Design + Vite
├── backend/           # Node.js + Express + TypeScript
├── docker/            # Dockerfile (前端/后端)
├── docs/              # 架构设计文档
├── .github/workflows/ # CI/CD 配置
├── docker-compose.yml # 生产环境编排
└── docker-compose.dev.yml # 开发基础设施
```

## 文档

- [架构设计文档](docs/ARCHITECTURE.md) — 完整的系统架构、API 设计、数据库设计、部署方案

## License

MIT
