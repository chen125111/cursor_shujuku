# 气体水合物相平衡查询系统（Gas Hydrate Phase Equilibrium Query System）

本项目提供一个面向气体水合物研究/工程应用的**相平衡实验数据管理与查询系统**，后端基于 **FastAPI** 提供 REST API，前端提供浏览器界面，支持多组分体系在不同温度下的相平衡压力数据的录入、检索与分析。

---

## 主要能力

- **相平衡查询**：按组分+温度匹配压力（含容差/范围模式/批量查询），提供水合物相平衡智能匹配接口
- **数据管理**：记录增删改查、分页筛选、统计与图表数据接口
- **批量导入导出**：CSV/Excel 导入、预校验、模板下载、导出
- **数据质量与审核**：重复记录检测、待审核区管理、操作审计与历史追踪
- **安全增强**：JWT 登录、TOTP 两步验证、限流/防爬虫、会话管理、审计日志
- **部署与运维**：Docker/Compose 一键启动、健康检查、SQLite 备份/恢复

---

## 技术栈与目录结构

- **后端**：FastAPI + Pydantic（`backend/`）
- **前端**：静态页面（`frontend/`）
- **文档**：用户手册/运维与本README对应的开发文档（`docs/`）
- **测试**：pytest（`tests/`）

建议从以下入口了解项目：

- 快速上手：`START_HERE.md`
- 用户手册：`docs/用户手册.md`
- 代码文档：`docs/系统代码文档.md`

---

## 安装与运行（本地）

### 环境要求

- Python 3.12+（推荐；项目在 CI/本环境已验证）
- 可选：Redis（用于缓存/限流/会话加速）

### 安装依赖

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt  # 可选：运行测试/覆盖率/代码质量
```

### 配置（推荐使用 `.env`）

复制模板并按需修改：

```bash
cp .env.example .env
```

将 `.env` 导出为环境变量（bash）：

```bash
set -a
. ./.env
set +a
```

> 生产环境务必设置强 `SECRET_KEY`，并配置 `ADMIN_PASSWORD`，否则管理员登录会被禁用。

### 启动服务

```bash
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

访问入口：

- 前端页面：`http://127.0.0.1:8000/`
- 后台管理：`http://127.0.0.1:8000/admin`
- API 文档（Swagger UI）：`http://127.0.0.1:8000/docs`
- OpenAPI：`http://127.0.0.1:8000/openapi.json`

---

## Docker 一键启动

```bash
cp .env.example .env
docker compose up -d --build
```

查看健康状态：

```bash
docker compose ps
```

停止并清理：

```bash
docker compose down
```

---

## 使用指南（快速示例）

### 1) 登录获取 Token（管理操作需要）

```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "User-Agent: demo" \
  -d '{"username":"admin","password":"'"$ADMIN_PASSWORD"'"}'
```

### 2) 水合物相平衡查询（无需登录）

```bash
curl -X POST "http://127.0.0.1:8000/api/query/hydrate" \
  -H "Content-Type: application/json" \
  -H "User-Agent: demo" \
  -d '{
    "components": {"x_ch4": 0.9, "x_c2h6": 0.1},
    "temperature": 275,
    "tolerance": 0.02
  }'
```

---

## API 文档

- **在线交互式文档**：启动服务后访问 `/docs`
- **离线文档**：见 `docs/API.md`

项目 API 大致分组：

- Records：`/api/records*`（增删改查/批量）
- Query / Public Query：`/api/query/*`、`/api/components/*`（相平衡查询）
- Auth / Sessions / TOTP：认证、会话、两步验证
- Import/Export/Template：导入导出与模板
- Review：重复数据审核工作流
- Backup：SQLite 备份/恢复/下载

---

## 测试

运行全部单元测试与集成测试：

```bash
python3 -m pytest
```

带覆盖率：

```bash
python3 -m pytest --cov
```

---

## 贡献指南

请先阅读 `CONTRIBUTING.md`，其中包含开发约定、分支/提交规范、测试要求与安全注意事项。

---

## 许可证

本项目采用 MIT License，详见 `LICENSE`。

