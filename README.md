# 气体水合物相平衡查询系统

一个用于**查询气体混合物在不同温度/压力条件下相平衡数据**的 Web 应用（前后端分离）。

## 功能概览

- 相平衡数据查询与筛选
- 基础统计与数据展示
- 前端页面（HTML/CSS/JS）
- 后端 API（FastAPI）
- 支持 Docker 部署

## 技术栈

- 后端：FastAPI（Python）
- 数据库：SQLite（默认）
- 前端：HTML / CSS / JavaScript
- 容器：Docker / docker-compose

## 快速开始（本地）

### 1) 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) 启动后端

```bash
cd backend
uvicorn main:app --reload
```

### 3) 打开前端

直接用浏览器打开 `frontend/index.html`（或使用你习惯的静态文件服务器）。

## 使用 Docker

```bash
docker compose up --build
```

## 目录结构

- `backend/`：后端 API 与业务逻辑
- `frontend/`：前端静态页面与脚本
- `migrations/`：数据库迁移 SQL
- `docs/`：用户手册、架构与运维文档
- `tests/`：测试用例

## 更多文档

- `START_HERE.md`：快速开始与协作入口
- `docs/用户手册.md`：用户手册
- `docs/系统代码文档.md`：系统代码文档

