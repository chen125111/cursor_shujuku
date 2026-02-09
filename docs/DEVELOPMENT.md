# 开发指南（Development）

本文档面向希望在本地进行二次开发、调试与扩展功能的开发者，涵盖环境准备、启动方式、配置项与常见开发流程。

## 1. 仓库结构速览

```text
backend/           FastAPI 后端（主要入口：backend/main.py）
frontend/          静态前端（首页 + admin 后台）
docs/              项目文档与截图
migrations/        SQL 迁移脚本（SQLite/MySQL）
scripts/           辅助脚本（迁移/本地运行等）
requirements.txt   Python 依赖（与 backend/requirements.txt 一致）
docker-compose.yml 容器编排（推荐用于快速跑通）
```

## 2. 开发环境准备

### 2.1 Python 版本

- **最低要求**：Python 3.8+
- **推荐**：Python 3.10+（类型提示与依赖生态更稳定）

### 2.2 创建虚拟环境并安装依赖

在仓库根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 注意：`requirements.txt` 与 `backend/requirements.txt` 当前一致，任选其一安装即可。

### 2.3 可选组件：Redis

如果你希望启用缓存（以及更稳定的限流计数存储），可在本地启动 Redis，并设置环境变量：

```bash
export REDIS_URL="redis://127.0.0.1:6379/0"
```

未配置 Redis 时系统会自动降级，不影响核心业务接口。

## 3. 运行与调试

### 3.1 初始化数据库

首次启动建议初始化数据库（会创建必要的表结构）：

```bash
python init_db.py
```

### 3.2 启动后端（开发模式）

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

启动后常用入口：

- 前端首页：`http://127.0.0.1:8000/`
- 管理后台：`http://127.0.0.1:8000/admin`
- Swagger：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

### 3.3 以脚本方式启动

仓库提供了若干便捷脚本（以实际文件为准）：

- `start_server.py`：启动服务（可被 `run_system.sh` 调用）
- `run_system.sh`：带检查流程的完整启动脚本
- `scripts/run_local.sh`：本地运行辅助脚本（如存在）

## 4. 配置与环境变量

后端会读取环境变量以决定数据库、密钥与跨域等行为。常见变量如下（以 `docs/用户手册.md` 中列表为准）：

- **认证与安全**
  - `SECRET_KEY`：JWT 签名密钥（生产环境必须设置为随机强密钥）
  - `ADMIN_USERNAME`：管理员用户名（默认 `admin`）
  - `ADMIN_PASSWORD`：管理员密码（不设置则管理员登录会被禁用）
- **数据库**
  - `DATABASE_PATH`：SQLite 主库文件路径（默认 `gas_data.db`）
  - `SECURITY_DB_PATH`：安全库文件路径（默认 `security.db`）
  - `DATABASE_URL`：MySQL 连接字符串（设置后优先使用 MySQL）
- **备份**
  - `BACKUP_DIR`：备份目录（默认 `backups`）
- **跨域**
  - `CORS_ORIGINS`：允许的来源列表（逗号分隔）
- **缓存**
  - `REDIS_URL`：Redis 连接地址
  - `REDIS_PREFIX`：Redis key 前缀（默认 `gasapp`）

## 5. 常见开发任务

### 5.1 增加/修改接口

1. 在 `backend/main.py` 增加路由函数（建议补充详细 docstring，FastAPI 会展示在 `/docs`）
2. 如涉及数据结构，优先在 `backend/models.py` 中补充/调整 Pydantic 模型
3. 如涉及数据库操作，集中在 `backend/database.py`（并补充单元级注释与边界处理）

### 5.2 数据迁移（SQLite ↔ MySQL）

- 迁移说明：`docs/db_migration.md`
- 迁移脚本：`scripts/migrate_sqlite_to_mysql.py`、`scripts/migrate_db.py`（以实际脚本内容为准）

### 5.3 运行“现有测试脚本”

仓库中有若干可直接运行的测试脚本（并非 pytest 套件）：

```bash
python minimal_test.py
python test_backend_api.py
python test_cache.py
python test_review.py
```

> 若你希望引入标准化测试框架（pytest）与 CI，可在此基础上扩展。

## 6. 文档维护规范（建议）

- **面向用户**的内容放在 `docs/USER_GUIDE.md` 与 `docs/用户手册.md`
- **面向开发者**的内容放在 `docs/DEVELOPMENT.md` 与 `docs/API.md`
- 每次新增/修改接口后，确保：
  - `/docs` 中的接口说明清晰（路由函数 docstring、参数描述完整）
  - `docs/API.md` 的关键调用示例同步更新（尤其是认证、错误码与示例查询）

