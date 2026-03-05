# 实验室管理系统 - 部署文档

气体水合物相平衡数据管理系统的完整部署指南。

---

## 目录

1. [系统架构](#系统架构)
2. [环境要求](#环境要求)
3. [快速开始](#快速开始)
4. [Docker 容器化](#docker-容器化)
5. [Docker Compose 编排](#docker-compose-编排)
6. [Nginx 反向代理](#nginx-反向代理)
7. [SSL 证书配置](#ssl-证书配置)
8. [CI/CD 流水线](#cicd-流水线)
9. [监控和日志](#监控和日志)
10. [备份和恢复](#备份和恢复)
11. [故障排查](#故障排查)

---

## 系统架构

```
                    ┌─────────────┐
                    │   用户请求   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │  :80/:443
                    │  反向代理   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌─────▼─────┐    ┌─────▼─────┐
    │ 静态文件 │      │  Backend  │    │  /api/*   │
    │  (可选)  │      │  FastAPI  │    │  代理     │
    └─────────┘      │  :8000    │    └───────────┘
                     └─────┬─────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐  ┌────▼────┐  ┌───▼────┐
         │ SQLite/ │  │  Redis  │  │ MySQL  │
         │  MySQL  │  │  缓存   │  │(可选)  │
         └─────────┘  └─────────┘  └────────┘
```

---

## 环境要求

- **Docker** 20.10+
- **Docker Compose** v2+
- **域名**（生产环境 SSL）
- **2GB+ 内存**（推荐 4GB）

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd <project-directory>
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 设置 SECRET_KEY、ADMIN_PASSWORD 等
```

### 3. 启动服务

```bash
# 基础服务（后端 + Redis + Nginx）
docker compose up -d

# 访问
# 前端: http://localhost
# API 文档: http://localhost/docs
```

### 4. 初始化管理员

首次启动后，通过 API 或管理界面设置管理员密码（见 `ADMIN_PASSWORD` 环境变量）。

---

## Docker 容器化

### 后端镜像

- **Dockerfile**: `docker/backend/Dockerfile`
- **基础镜像**: `python:3.11-slim`
- **端口**: 8000
- **健康检查**: `GET /api/statistics`

构建：

```bash
docker build -f docker/backend/Dockerfile -t lab-backend:latest .
```

### 前端镜像（可选）

- **Dockerfile**: `docker/frontend/Dockerfile`
- **基础镜像**: `nginx:alpine`
- 当前架构下，静态文件由后端或 Nginx 代理提供，前端镜像可用于独立静态部署。

### 数据库

- **SQLite**（默认）: 数据存储在 `./data/` 卷
- **MySQL**（可选）: 使用 `--profile mysql` 启动

---

## Docker Compose 编排

### 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 (内部) | FastAPI 后端 |
| redis | 6379 (内部) | 缓存 |
| nginx | 80, 443 | 反向代理 |
| mysql | 3306 (内部) | 可选数据库 |
| prometheus | 9090 | 监控（profile: monitoring） |
| grafana | 3000 | 可视化（profile: monitoring） |
| loki | 3100 | 日志（profile: monitoring） |
| promtail | - | 日志采集（profile: monitoring） |

### 常用命令

```bash
# 启动基础服务
docker compose up -d

# 启动 MySQL 模式
docker compose --profile mysql up -d

# 启动监控栈
docker compose --profile monitoring up -d

# 查看日志
docker compose logs -f backend

# 停止
docker compose down
```

---

## Nginx 反向代理

### 配置文件

- **HTTP 模式**: `nginx/nginx-http-only.conf`（默认）
- **HTTPS 模式**: `nginx/nginx.conf`（需 SSL 证书）

### 路由规则

- `/api/*` → 后端 8000
- `/docs`, `/openapi.json` → 后端
- `/` → 后端（静态文件）
- `/.well-known/acme-challenge/` → Certbot 验证

### 自定义配置

修改 `nginx/` 下配置文件后，重新加载：

```bash
docker compose exec nginx nginx -s reload
```

---

## SSL 证书配置

### 方式一：Let's Encrypt（生产推荐）

1. **确保域名已解析**到服务器 IP

2. **获取证书**：

```bash
chmod +x scripts/init-letsencrypt.sh
./scripts/init-letsencrypt.sh yourdomain.com admin@yourdomain.com
```

3. **启用 SSL 模式**：

```bash
docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d
```

4. **证书续期**（建议 cron 每日执行）：

```bash
docker run --rm -v $(pwd)/certbot/www:/var/www/certbot \
  -v $(pwd)/certbot/conf:/etc/letsencrypt \
  certbot/certbot renew
docker compose exec nginx nginx -s reload
```

### 方式二：自签名证书（开发/测试）

```bash
chmod +x scripts/ssl-self-signed.sh
./scripts/ssl-self-signed.sh localhost
docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d
```

---

## CI/CD 流水线

### GitHub Actions

- **工作流**: `.github/workflows/deploy.yml`
- **触发**: push 到 `main`/`master`
- **步骤**: Lint → 构建镜像 → 部署

### 部署所需 Secrets

| Secret | 说明 |
|--------|------|
| DEPLOY_HOST | 服务器 IP 或域名 |
| DEPLOY_USER | SSH 用户名 |
| DEPLOY_SSH_KEY | SSH 私钥 |
| DEPLOY_PATH | 项目在服务器上的路径 |

### 配置步骤

1. 仓库 → Settings → Secrets and variables → Actions
2. 添加上述 Secrets
3. 创建 `production` 环境（可选）

---

## 监控和日志

### 启动监控栈

```bash
docker compose --profile monitoring up -d
```

### 访问地址

- **Grafana**: http://localhost:3000（默认 admin/admin）
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100

### Grafana 配置

1. 添加 Prometheus 数据源：`http://prometheus:9090`
2. 添加 Loki 数据源：`http://loki:3100`
3. 导入 Dashboard（可选）

### 日志查看

```bash
# 后端日志
docker compose logs -f backend

# Nginx 访问日志
docker compose exec nginx tail -f /var/log/nginx/access.log
```

---

## 备份和恢复

### 自动备份（应用内）

后端支持 SQLite 自动备份（每 6 小时），备份目录：`./backups/`

### 手动备份脚本

```bash
chmod +x scripts/backup.sh scripts/restore.sh

# 备份
./scripts/backup.sh

# 恢复（会提示确认）
./scripts/restore.sh ./backups/data_20240101_120000.tar.gz
```

### 环境变量

- `BACKUP_DIR`: 备份目录（默认 `./backups`）
- `DATA_DIR`: 数据目录（默认 `./data`）
- `RETENTION_DAYS`: 保留天数（默认 30）

### 定时备份（Cron）

```cron
0 2 * * * cd /path/to/project && ./scripts/backup.sh
```

---

## 故障排查

### 后端无法启动

```bash
docker compose logs backend
# 检查 DATABASE_PATH、SECRET_KEY 等环境变量
```

### Nginx 502 Bad Gateway

- 确认 backend 容器已启动：`docker compose ps`
- 检查 backend 健康：`curl http://localhost:8000/api/statistics`

### SSL 证书错误

- 确认证书路径：`ls certbot/conf/live/`
- 确认符号链接：`ls -la certbot/conf/live/fullchain.pem`

### Redis 连接失败

- 后端会优雅降级，缓存禁用不影响核心功能
- 检查：`docker compose exec redis redis-cli ping`

### 数据持久化

- 数据目录：`./data/`
- 备份目录：`./backups/`
- 确保卷正确挂载：`docker compose config`

---

## 环境变量参考

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SECRET_KEY | JWT 签名密钥 | (必填) |
| ADMIN_USERNAME | 管理员用户名 | admin |
| ADMIN_PASSWORD | 管理员密码 | (必填) |
| DATABASE_PATH | SQLite 路径 | /app/data/gas_data.db |
| DATABASE_URL | MySQL 连接串 | (空=SQLite) |
| REDIS_URL | Redis 连接 | redis://redis:6379/0 |
| BACKUP_DIR | 备份目录 | /app/backups |
| CORS_ORIGINS | CORS 来源 | (空) |
| TZ | 时区 | Asia/Shanghai |

---

## 联系与支持

如有问题，请查阅项目文档或提交 Issue。
