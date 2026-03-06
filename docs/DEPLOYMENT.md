# 部署指南（Docker / 生产建议）

---

## Docker Compose（推荐）

```bash
cp .env.example .env
docker compose up -d --build
```

访问：

- 前端：`http://localhost:8000/`
- API 文档：`http://localhost:8000/docs`

### 数据持久化

默认会映射：

- `./data` → `/app/data`（SQLite 数据库）
- `./backups` → `/app/backups`（备份目录）

### Redis

`docker-compose.yml` 默认包含 Redis 容器（`redis` 服务）。如果你不需要 Redis：

- 将 `.env` 中的 `REDIS_URL` 置空
- 并把 `docker-compose.yml` 中 `gas-app.depends_on.redis` 注释掉（可选）

---

## 生产环境建议

- **密钥与密码**：务必设置强 `SECRET_KEY` 与 `ADMIN_PASSWORD`
- **反向代理**：建议使用 Nginx/Ingress 提供 HTTPS、限流、访问日志
- **CORS**：仅允许可信来源（`CORS_ORIGINS`）
- **数据库**：
  - SQLite：适合单机与小规模；务必开启备份与磁盘监控
  - MySQL：适合多副本与更高并发；建议使用托管 RDS 并启用云备份
- **可观测性**：建议采集 stdout 日志并配置错误率/延迟报警

运维巡检建议见：`ops_checklist.md`

