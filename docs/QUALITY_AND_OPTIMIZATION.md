# 测试套件与优化方案（cursor_shujuku）

本文档总结本项目已落地的**测试体系**与**性能/安全/稳定性/代码质量**优化点，并给出可执行的本地命令与推荐的运行参数。

## 1. 测试（pytest）

已新增 `tests/` 目录，包含：

- **单元测试**：覆盖数据校验（`backend/data_validation.py`）、JWT/密码哈希（`backend/auth.py`）、数据库 CRUD 与筛选/组分查询（`backend/database.py`）。
- **集成测试**：使用 `TestClient` 覆盖登录、受保护写接口、列表/详情、以及统计/图表接口的可用性。

### 运行方式

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 -m pytest
```

### 覆盖率

已在 `pyproject.toml` 中配置 `pytest-cov`，默认执行会输出 `--cov=backend --cov-report=term-missing`。

## 2. 性能优化

### 2.1 缓存机制增强（Redis）

对 `backend/cache.py` 做了增强：

- **支持 async/await**：`@cached(...)` 现在能够正确装饰 `async def` 路由，不再出现返回协程对象导致的运行时错误。
- **统一缓存键前缀为 `cache:`**：便于按模式清理，修复“清理接口无法命中缓存键”的问题。
- **清理缓存使用 `SCAN`**：`clear_pattern()` 使用 `scan_iter` 分批删除，避免 `KEYS` 在大 keyspace 下阻塞。
- **可配置禁用**：支持环境变量 `CACHE_ENABLED=0` 直接禁用缓存（测试环境默认禁用）。

常用环境变量：

- `CACHE_ENABLED=0|1`
- `REDIS_URL`（优先使用）
- 或 `REDIS_HOST/REDIS_PORT/REDIS_DB/REDIS_PASSWORD`
- `CACHE_DEFAULT_TTL`

### 2.2 公共查询端点 SQL 优化

对公开查询相关接口（`/api/components/*`、`/api/query/*`）：

- 将原先的**多次 COUNT 循环（N+1 查询）**优化为**单次聚合查询**（`SUM(CASE WHEN ...)`），减少数据库往返次数。

## 3. 安全加固

- **字段白名单校验**：公共查询端点对组分字段名做白名单验证，防止将用户输入直接拼接入 SQL。
- **SQL 注入修复**：`backend/data_review.py` 中 `IN (...)` 动态拼接已改为参数化占位符，避免通过 ID 列表构造注入。
- **错误信息收敛**：公开查询接口异常时返回通用错误信息（并在服务端日志记录详细堆栈）。

## 4. 错误处理与日志

- 在 `backend/main.py` 增加全局异常处理：
  - `RequestValidationError`：返回 422 并记录校验错误。
  - `Exception`：返回 500 通用错误，避免向客户端泄露内部细节。
- 启动阶段日志由 `print` 调整为 `logging`（仍建议在部署层配置 `LOG_LEVEL`、输出格式与采集）。

## 5. 代码质量（lint / 类型检查）

### 5.1 Ruff

已在 `pyproject.toml` 配置 `ruff`，可运行：

```bash
python3 -m ruff check .
```

说明：为兼容现有代码基线，暂未强制 `E501`（长行）以及 FastAPI 的 `Depends(...)` 误报规则（`B008`）。

### 5.2 Mypy

已在 `pyproject.toml` 配置 `mypy`（当前采用“增量接入”策略，对历史模块先 `ignore_errors`，确保类型检查可在 CI 落地）。

```bash
python3 -m mypy backend tests
```

## 6. 备份行为（测试/生产可控）

`backend/backup.py` 增加 `BACKUP_ENABLED` 开关，可在测试或某些部署环境中关闭自动备份：

- `BACKUP_ENABLED=0`：禁用备份系统初始化与自动备份线程

