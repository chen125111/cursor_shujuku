# 气体混合物数据管理系统（cursor_shujuku）

本项目是一个面向**气体水合物/相平衡实验数据**的 B/S（浏览器/服务器）系统：提供数据的存储、检索、批量导入导出、审核与安全管理能力，并内置 FastAPI 的交互式 API 文档，便于二次开发与集成。

> 备注：仓库中已包含更完整的长文档与截图，推荐从 `docs/用户手册.md` 开始阅读。

## 主要能力

- **数据管理**：气体混合物记录的增删改查（温度、压力、7 种组分摩尔分数）。
- **智能查询**：按组分/温度进行相平衡点检索与匹配（对输入误差可容忍）。
- **批量导入导出**：支持 CSV/Excel 导入、预校验、模板下载；支持 CSV/Excel 导出。
- **数据审核**：检测同组分同温度下多个压力值的重复数据，支持迁移到待审核区、通过/拒绝/恢复。
- **安全增强**：JWT 登录、可选 TOTP 两步验证、API 限流与基础反爬、登录日志与审计日志、会话管理。
- **备份恢复**：SQLite 文件备份/恢复/下载（MySQL 由托管备份策略负责）。
- **缓存**：可选 Redis 缓存（未连接时自动降级，不影响核心功能）。

## 架构概览

- **前端**：静态页面（`frontend/`，含管理后台 `frontend/admin/`）
- **后端**：FastAPI（`backend/main.py`）
- **数据库**：默认 SQLite（文件），可切换 MySQL（通过环境变量连接）
- **可选组件**：Redis（用于缓存与限流状态存储的优雅增强）

项目架构图见：`docs/architecture.png`。

## 快速开始

### 方式 A：Docker Compose（推荐）

1. 准备环境变量文件（`docker-compose.yml` 会读取 `.env`）：

```bash
cp .env.example .env 2>/dev/null || true
```

如果没有 `.env.example`，也可以直接在 `.env` 中至少设置：

```bash
ADMIN_PASSWORD=请设置一个强密码
SECRET_KEY=请设置一个随机且足够长的密钥
```

2. 启动服务：

```bash
docker-compose up -d --build
```

3. 访问：

- 前端首页：`http://127.0.0.1:8000/`
- 管理后台：`http://127.0.0.1:8000/admin`
- API 文档（Swagger UI）：`http://127.0.0.1:8000/docs`
- API 文档（ReDoc）：`http://127.0.0.1:8000/redoc`

### 方式 B：本地运行（Python）

1. 安装依赖（根目录与 `backend/requirements.txt` 内容一致）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 初始化数据库（首次运行建议执行）：

```bash
python init_db.py
```

3. 启动后端：

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

或直接运行：

```bash
python -m backend.main
```

## 使用指南（最常用路径）

- **交互式 API 文档**：打开 `/docs`，可直接 “Try it out” 发起请求
- **登录获取 Token**：`POST /api/auth/login`
- **携带 Token 调用受保护接口**：请求头 `Authorization: Bearer <token>`
- **相平衡查询（示例）**：`POST /api/query/hydrate`

更详细的操作步骤、界面说明与示例查询见：

- `docs/USER_GUIDE.md`（简明用户指南）
- `docs/用户手册.md`（完整版用户手册，含截图与完整 API 列表）

## API 文档

本项目已启用 FastAPI 自动 OpenAPI 文档：

- `/docs`：Swagger UI
- `/redoc`：ReDoc
- `/openapi.json`：OpenAPI JSON（可导入 Postman/Apifox 生成集合或 SDK）

同时仓库提供了“可读性更强”的静态 API 文档：

- `docs/API.md`

## 开发与贡献

- 开发环境配置：`docs/DEVELOPMENT.md`
- 贡献指南与规范：`docs/CONTRIBUTING.md`
- 迁移/运维参考：`docs/db_migration.md`、`docs/ops_checklist.md`、`docs/sae_deploy.md`

## 目录结构（节选）

```text
backend/     # FastAPI 后端（接口、安全、校验、备份、缓存等）
frontend/    # 静态前端（含 admin 后台）
docs/        # 文档（用户手册、开发指南、API 文档、截图等）
migrations/  # 数据库迁移 SQL
scripts/     # 迁移/运行脚本
```

## 许可证

仓库未单独提供 LICENSE 文件时，默认不对外授予许可；如需开源/商用授权请补充 LICENSE 并在此处更新说明。

