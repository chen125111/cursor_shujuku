# 配置说明（环境变量）

系统主要通过环境变量进行配置，推荐使用仓库根目录的 `.env` 文件管理配置（见 `.env.example` 模板）。

---

## 快速开始

```bash
cp .env.example .env
```

在本地将 `.env` 导出为环境变量（bash）：

```bash
set -a
. ./.env
set +a
```

---

## 必配项（生产环境）

- **`SECRET_KEY`**：JWT 签名密钥（必须修改为强随机字符串）
- **`ADMIN_PASSWORD`**：管理员初始密码（未设置则管理员登录禁用）

---

## CORS

- **`CORS_ORIGINS`**：允许的跨域来源列表，英文逗号分隔
  - 示例：`http://localhost:5173,http://127.0.0.1:5173`
  - 留空：不启用跨域（后端会将 `allow_credentials` 设为 false）

---

## 数据库

系统支持 **SQLite（默认）** 与 **MySQL（可选）**：

### SQLite（默认）

- **`DATABASE_PATH`**：业务库文件路径（默认：`./gas_data.db`）
- **`SECURITY_DB_PATH`**：安全库文件路径（默认：`./security.db`）

> 建议放在 `./data/` 下并做好持久化（Docker 默认映射到 `/app/data`）。

### MySQL（可选）

当设置了 **`DATABASE_URL`** 时，后端会优先使用 MySQL。

- **`DATABASE_URL`**：业务库连接字符串（示例）
  - `mysql+pymysql://user:password@127.0.0.1:3306/gas_data`
- **`SECURITY_DATABASE_URL`**：安全库连接字符串（为空时回落到 `DATABASE_URL`）

MySQL 连接池与超时（可选）：

- `DB_POOL_ENABLED`：默认开启（`1`），可设为 `0/false` 关闭
- `DB_POOL_MAX` / `DB_POOL_MIN` / `DB_POOL_MAX_CACHED`
- `DB_CONNECT_TIMEOUT` / `DB_READ_TIMEOUT` / `DB_WRITE_TIMEOUT`
- `DB_CONNECT_RETRIES` / `DB_CONNECT_RETRY_DELAY`

---

## 备份（SQLite）

> 当使用 MySQL（托管数据库）时，系统会提示使用云侧备份能力，文件备份相关接口会自动降级。

- **`BACKUP_ENABLED`**：默认开启（`1`），可设为 `0/false` 禁用
- **`BACKUP_DIR`**：备份目录（默认 `./backups`）

---

## Redis（可选）

Redis主要用于：

- API 限流/封禁（`backend/security.py`）
- 缓存（`backend/cache.py`，可通过 `CACHE_ENABLED` 关闭）
- 会话加速（`backend/security.py` 会话缓存）

推荐：

- **`REDIS_URL`**：形如 `redis://host:6379/0`
- **`REDIS_PREFIX`**：key 前缀（默认 `gasapp`）

缓存模块相关：

- **`CACHE_ENABLED`**：`1` 启用，`0` 禁用（默认启用；测试会强制关闭）
- **`CACHE_DEFAULT_TTL`**：默认 TTL（秒）
- 或使用 `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` / `REDIS_PASSWORD`

