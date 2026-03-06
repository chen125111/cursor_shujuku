# 气体水合物相平衡查询系统 — 架构审查报告

> 审查日期：2026-03-06  
> 审查范围：全部后端（`backend/`）、前端（`frontend/`）、数据库迁移、测试、部署配置

---

## 一、系统概览

| 维度 | 现状 |
|------|------|
| 后端框架 | FastAPI 0.104.1 + Uvicorn |
| 前端 | 原生 HTML/CSS/JS（无构建步骤），CDN 引入 Chart.js / ECharts / jsPDF |
| 数据库 | SQLite（默认） / MySQL（可选），raw SQL |
| 缓存 | Redis（可选），自定义 `@cached` 装饰器 |
| 认证 | 手写 JWT + PBKDF2 + 可选 TOTP |
| 部署 | Docker（Python 3.11-slim），docker-compose |
| 测试 | pytest，分 unit / integration |

**代码规模统计：**

| 文件 | 行数 | 说明 |
|------|------|------|
| `backend/main.py` | **2513** | 路由 + 请求模型 + 业务编排 + 静态文件服务 |
| `backend/security.py` | 889 | 限流、防爬、会话、审计 |
| `backend/data_review.py` | 515 | 重复数据审核 |
| `backend/data_validation.py` | 461 | 数据校验规则 |
| `backend/cache.py` | 471 | Redis 缓存封装 |
| `backend/auth.py` | 413 | JWT、密码、用户管理 |
| `backend/database.py` | 422 | 业务数据 CRUD |
| `backend/backup.py` | 304 | SQLite 备份 |
| `backend/db.py` | 215 | 数据库连接层 |
| `backend/models.py` | 77 | Pydantic 模型 |
| `backend/config.py` | 56 | 配置辅助 |
| `frontend/index.html` | 1987 | 公开查询页 |
| `frontend/admin/index.html` | 3334 | 后台管理页 |
| **合计** | **~11940** | |

---

## 二、代码结构组织

### 2.1 当前结构

```
backend/
├── main.py            # 2513 行「上帝文件」
├── database.py        # 业务 CRUD
├── db.py              # 连接层
├── models.py          # Pydantic 模型（仅 77 行）
├── config.py          # 配置
├── auth.py            # JWT + 用户
├── security.py        # 限流 / 审计 / 会话
├── data_validation.py # 校验
├── data_review.py     # 审核
├── cache.py           # Redis
├── backup.py          # SQLite 备份
└── totp.py            # TOTP
```

### 2.2 核心问题

#### 问题 P1：`main.py` 是 2513 行的「God File」（严重）

所有 60+ 路由、请求模型（`LoginRequest`、`ChangePasswordRequest`、`BatchDeleteRequest` 等）、中间件、文件解析（`parse_import_content`、`parse_import_row`）、热力图计算、启动事件——全部塞在一个文件里。这导致：

- **可读性差**：定位一个端点需要在 2500 行中滚动搜索
- **合并冲突频繁**：任何功能改动都会修改同一文件
- **职责混乱**：路由定义中混杂着业务逻辑（热力图分箱计算 50+ 行）、文件解析逻辑（`parse_import_row` 等）、辅助函数

#### 问题 P2：缺乏分层架构（中等）

当前是「路由直接调用数据库函数」的两层模式，没有明确的 Service 层。路由处理函数中混合了：
- 请求参数组装
- 业务验证
- 数据库操作调用
- 审计日志记录
- 缓存失效
- 响应组装

例如 `api_create_record` 中同时调用 `clean_record`、`validate_record`、`get_soft_warnings`、`create_record`、`invalidate_read_caches`——这些应该封装到 service 层。

#### 问题 P3：请求模型散落在 `main.py` 中（轻微）

`LoginRequest`、`ChangePasswordRequest`、`CreateUserRequest`、`BatchDeleteRequest`、`ApproveRequest`、`HydrateQueryRequest` 等十余个 Pydantic 模型定义在 `main.py` 里（第 92–117 行 + 第 1545–1560 行 + 第 1839–1846 行等），而 `models.py` 只有 77 行。

#### 问题 P4：模块级副作用（中等）

`database.py` 最后一行 `init_database()`、`data_review.py` 最后一行 `init_review_tables()` 在 **import 时** 就执行数据库初始化。这导致：
- 测试需要 `importlib.reload()` 来重新初始化
- 模块导入顺序变得关键
- 无法在不连数据库的情况下导入这些模块

#### 问题 P5：`_ensure_index` 函数重复定义 3 次（轻微）

`database.py`、`security.py`、`data_review.py` 各自定义了一个完全相同的 `_ensure_index` 函数。

### 2.3 改进建议

**P1 解决方案 — 按领域拆分路由（优先级：高）**

```
backend/
├── routers/
│   ├── __init__.py
│   ├── records.py       # CRUD + batch
│   ├── query.py         # 公开查询 API
│   ├── charts.py        # 图表数据
│   ├── auth.py          # 认证 + TOTP + 会话
│   ├── security.py      # 登录日志 / 审计
│   ├── review.py        # 数据审核
│   ├── import_export.py # 导入 / 导出 / 模板
│   └── backup.py        # 备份
├── schemas/
│   ├── __init__.py
│   ├── records.py       # GasRecord*
│   ├── auth.py          # LoginRequest 等
│   ├── query.py         # HydrateQueryRequest 等
│   └── review.py        # ApproveRequest 等
├── services/
│   ├── record_service.py
│   ├── query_service.py
│   └── import_service.py
├── main.py              # 仅 app 创建 + include_router + 中间件 + startup
└── ...
```

**P2 解决方案 — 引入 Service 层**

路由只做「接收请求 → 调用 service → 返回响应」，service 层封装业务编排（验证 + CRUD + 缓存失效 + 审计）。

**P4 解决方案 — 延迟初始化**

移除模块末尾的 `init_database()` / `init_review_tables()`，改为在 `startup_event` 中显式调用。

---

## 三、API 设计分析

### 3.1 优点

- **一致的 URL 前缀**：所有 API 以 `/api/` 开头
- **资源 CRUD 基本合规**：`GET/POST/PUT/DELETE /api/records/{id}` 符合 REST
- **分页参数标准化**：`page` + `per_page` 查询参数
- **Swagger 自动文档**：FastAPI 原生支持 `/docs`

### 3.2 问题

#### 问题 A1：新旧图表 API 共存（中等）

同时存在 `/api/chart/temperature` 和 `/api/charts/temperature`，两组端点功能完全重复。旧版无缓存、新版有 `@cached`，增加了维护成本和前端困惑。

#### 问题 A2：动词式 URL（轻微）

- `POST /api/review/move-duplicates` — 应为 `POST /api/review/duplicates/actions/move`
- `POST /api/records/batch-delete` — 更 RESTful 的方式是 `DELETE /api/records` + body
- `POST /api/auth/sessions/revoke-all` — 可用 `DELETE /api/auth/sessions`

#### 问题 A3：返回格式不统一（中等）

有些端点用 `ApiResponse(success, message, data)` 包装：

```python
return ApiResponse(success=True, message="创建成功", data={"id": record_id})
```

有些端点直接返回裸 dict：

```python
return {"success": True, "data": user}
```

有些端点直接返回 Pydantic 模型：

```python
return stats  # Statistics model
```

缺乏统一的响应信封（envelope），前端需要兼容多种格式。

#### 问题 A4：版本管理缺失（轻微）

URL 中没有版本号（如 `/api/v1/`），未来 API 变更将无法平滑迁移。

#### 问题 A5：查询 API 设计混乱（中等）

查询相关端点有 6 个，部分功能重叠：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/query` | GET | 按组分查（旧版） |
| `/api/query/by-components` | POST | 按组分+温度查 |
| `/api/query/batch` | POST | 批量温度查 |
| `/api/query/range` | POST | 按组分范围+温度查 |
| `/api/query/match-count` | POST | 匹配计数 |
| `/api/query/hydrate` | POST | 水合物查询（核心功能） |

其中 `/api/query`（GET）与 `/api/query/hydrate`（POST）功能高度重叠，应统一为一个入口。

#### 问题 A6：`DELETE /api/auth/sessions/{session_id}` 是空实现（严重）

```python
@app.delete("/api/auth/sessions/{session_id}", tags=["Sessions"])
async def api_revoke_session(session_id: int, user: dict = Depends(require_auth)):
    return {"success": True, "message": "会话已撤销"}  # 未实际执行任何操作！
```

这是一个假实现，对外暴露的 API 实际上不做任何事情。

### 3.3 改进建议

1. **移除旧版 `/api/chart/*` 端点**，只保留 `/api/charts/*`
2. **统一响应格式**：所有端点使用 `{"success": bool, "message": str, "data": ...}` 信封
3. **添加 API 版本前缀**：`/api/v1/`
4. **合并查询入口**：保留 `/api/query/hydrate` 作为核心，将 `/api/query` GET 作为兼容别名
5. **修复空实现的会话撤销端点**

---

## 四、数据库设计分析

### 4.1 当前表结构

**核心表 `gas_mixture`：**
```sql
gas_mixture (
    id INTEGER PRIMARY KEY,
    temperature REAL NOT NULL,       -- 温度 (K)
    x_ch4 REAL DEFAULT 0,            -- 7 个组分摩尔分数
    x_c2h6 REAL DEFAULT 0,
    x_c3h8 REAL DEFAULT 0,
    x_co2 REAL DEFAULT 0,
    x_n2 REAL DEFAULT 0,
    x_h2s REAL DEFAULT 0,
    x_ic4h10 REAL DEFAULT 0,
    pressure REAL NOT NULL,          -- 压力 (MPa)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### 4.2 优点

- **索引合理**：对 temperature、pressure、temperature+pressure 组合以及各组分字段建了索引
- **SQLite/MySQL 双支持**：通过 `_CursorProxy` 统一 `?` / `%s` 占位符差异
- **连接池**：MySQL 使用 DBUtils PooledDB

### 4.3 问题

#### 问题 D1：无数据来源追踪（中等）

`gas_mixture` 缺少 `source`（数据来源，如文献、实验）、`reference`（参考文献）等字段。对于科学数据系统，这是关键元数据。

#### 问题 D2：无 ORM，raw SQL 拼接（中等）

所有数据库操作使用 f-string 拼接 SQL，虽然参数部分使用了占位符（避免了注入），但索引名、表名、列名依然是拼接的：

```python
query = f"UPDATE gas_mixture SET {', '.join(fields)} WHERE id = ?"
cursor.execute(f'DELETE FROM gas_mixture WHERE id IN ({placeholders})', ids)
```

这种模式易出错，且 SQLite/MySQL 的差异处理散落在各个函数中（如 `FLOOR` vs `CAST`、`RAND()` vs `RANDOM()`、`GROUP_CONCAT`、`INSERT OR REPLACE` vs `ON DUPLICATE KEY UPDATE`）。

#### 问题 D3：两个数据库文件的管理复杂（轻微）

业务数据和安全数据分布在 `gas_data.db` 和 `security.db` 两个文件中，但备份模块只备份 `gas_data.db`，安全数据库（包含用户账户、登录日志、审计日志）没有被备份。

#### 问题 D4：`pending_review` 使用 `GROUP_CONCAT` 不可移植（轻微）

`find_duplicate_pressure_records()` 中使用了 `GROUP_CONCAT(id)` 和 `GROUP_CONCAT(pressure)`，这在 MySQL 中有长度限制（默认 1024 字节），大数据量时会截断。

#### 问题 D5：每次操作独立连接（中等）

SQLite 模式下，每个函数调用都创建新连接（`get_connection` context manager）。虽然 SQLite 连接很轻量，但频繁的创建/关闭在高并发时仍有开销。更重要的是，跨函数操作无法使用同一事务，例如 `api_create_record` 中的 `create_record` + 审计日志是两个独立事务。

#### 问题 D6：缺少数据库迁移版本管理（中等）

虽然有 `migrations/` 目录和 `scripts/migrate_db.py`，但代码中的 DDL 同时也在各模块（`database.py`、`security.py`、`data_review.py`）中以 `CREATE TABLE IF NOT EXISTS` 形式维护。两套 DDL 可能不同步，无法保证迁移的幂等性和顺序性。

### 4.4 改进建议

1. **引入轻量 ORM（如 SQLModel）或至少用 Repository 模式封装 SQL**
2. **统一迁移管理**：使用 Alembic 或确保单一 DDL 来源
3. **备份模块应同时备份安全数据库**
4. **增加数据溯源字段**：`source`、`reference`、`imported_by`

---

## 五、错误处理机制

### 5.1 优点

- **全局异常处理器**：`RequestValidationError` → 422、未捕获异常 → 500
- **结构化 HTTP 错误**：正确使用 400/401/403/404/429/500 状态码
- **异常重新抛出**：路由中 `except HTTPException: raise` 避免被通用 except 吞掉

### 5.2 问题

#### 问题 E1：大量 bare `except Exception` 吞错误（严重）

在 `security.py`、`auth.py`、`totp.py` 中，数据库操作的异常被静默吞掉：

```python
# auth.py:101
def _get_user_from_db(username: str) -> Optional[Dict]:
    try:
        ...
    except Exception:
        return None  # 数据库连接失败？表不存在？字段错误？全部返回 None

# security.py:386
def record_login(username, ip, user_agent, success, failure_reason=None):
    try:
        ...
    except Exception as e:
        print(f"[Security] 记录登录日志失败: {e}")  # 仅 print，不记日志

# auth.py:400
def list_users() -> list:
    try:
        ...
    except Exception:
        pass  # 完全静默！
```

这会导致：
- **故障不可见**：数据库异常被静默，运维无法感知
- **逻辑错误**：`_get_user_from_db` 返回 `None` 时，调用者无法区分「用户不存在」和「数据库故障」
- **print 替代 logger**：`security.py` 大量使用 `print()` 而非 `logger`

#### 问题 E2：缺少自定义异常类（轻微）

没有定义 `UserNotFoundError`、`DuplicateRecordError`、`InvalidCompositionError` 等业务异常。所有错误都通过 `HTTPException` 传递，service 层与 HTTP 层耦合。

#### 问题 E3：422 错误格式暴露内部信息（轻微）

`RequestValidationError` 处理器直接返回 `exc.errors()`，其中可能包含模型字段名、类型信息等内部细节。

### 5.3 改进建议

1. **消除 bare except**：区分可恢复/不可恢复异常，不可恢复的应向上传播
2. **统一使用 `logger`**：替换所有 `print()` 调用
3. **定义业务异常类**：`BusinessError`、`NotFoundError`、`ConflictError` 等
4. **异常处理器中过滤敏感信息**

---

## 六、安全性分析

### 6.1 优点

- **PBKDF2 密码加密**：100000 次迭代 + 随机 salt，符合 OWASP 推荐
- **JWT 使用 HMAC-SHA256 签名**，支持过期时间校验
- **Rate Limiting**：内存/Redis 双模式限流
- **爬虫检测 + IP 封禁**
- **TOTP 两步验证**
- **安全响应头**：X-Content-Type-Options、X-Frame-Options、X-XSS-Protection

### 6.2 问题

#### 问题 S1：手写 JWT 实现（严重）

`auth.py` 完全手写了 JWT 的编码、解码、签名验证。与成熟库（`PyJWT`、`python-jose`）相比：
- 不支持 `alg: none` 攻击防护
- 不支持 `kid`（key rotation）
- 缺少 `nbf`（not before）、`iss`（issuer）、`aud`（audience）声明
- header 的 `alg` 字段未校验（接受任何算法声明）

#### 问题 S2：默认 SECRET_KEY 硬编码（严重）

```python
DEFAULT_SECRET_KEY = "your-super-secret-key-change-in-production-2024"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
```

虽然有 `is_using_default_secret_key()` 的警告，但默认值允许启动且不阻止登录，生产环境可能遗漏配置。

#### 问题 S3：内存中的管理员账户（中等）

`auth.py` 中 `ADMIN_USERS` 字典在内存中保存管理员信息，且 `change_password` 对内存用户的修改在重启后丢失：

```python
# auth.py:356
user["password_hash"] = hash_password(new_password)  # 仅更新内存 dict！
```

#### 问题 S4：`detect_crawler` 误封正常用户（轻微）

```python
CRAWLER_USER_AGENTS = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
                        'python-requests', 'scrapy', 'httpclient', 'java',
                        'axios', 'node-fetch', 'go-http-client']
```

包含 `axios`、`node-fetch`——正常的前端 SSR 或 BFF 请求也会被封禁。

#### 问题 S5：备份文件下载缺少路径遍历防护（中等）

```python
@app.get("/api/backup/download/{filename}")
async def api_download_backup(filename: str, ...):
    filepath = os.path.join(backup_dir, filename)
    return FileResponse(filepath, ...)
```

`filename` 若为 `../../etc/passwd` 可能造成目录遍历。应校验 `filename` 不含路径分隔符。

### 6.3 改进建议

1. **使用 `PyJWT` 替代手写实现**
2. **强制 SECRET_KEY 配置**：未设置时拒绝启动
3. **备份下载添加路径遍历防护**：`os.path.basename(filename)` 或白名单校验
4. **从爬虫黑名单中移除 `axios`、`node-fetch`**

---

## 七、可扩展性分析

### 7.1 当前可扩展点（好的方面）

- **数据库可切换**：SQLite（开发）→ MySQL（生产），通过环境变量配置
- **缓存可选**：Redis 不可用时自动降级为无缓存
- **Docker 部署**：容器化，便于水平扩展
- **校验规则可配置**：`GAS_MIXTURE_RULES` 列表式定义

### 7.2 问题

#### 问题 X1：新增组分需改动 10+ 处（严重）

若要添加新的气体组分（如 `x_c5h12`），需要修改：

1. `database.py` → `CREATE TABLE`、`INSERT`、`UPDATE`、`get_chart_data` 等
2. `models.py` → `GasRecordBase`、`GasRecordUpdate`
3. `data_validation.py` → `GAS_MIXTURE_RULES`、`validate_record` 中的摩尔分数列表
4. `data_review.py` → `pending_review` 建表、`find_duplicate_pressure_records`、`approve_group` 等
5. `main.py` → `parse_import_row`、`api_chart_composition`、`PUBLIC_COMPONENT_COLUMNS` 等
6. `frontend/index.html` → 组分输入表单
7. `frontend/admin/index.html` → 管理表格列

**组分列表在代码中至少硬编码了 15+ 次**。应定义为单一来源（Single Source of Truth），其余地方引用。

#### 问题 X2：单进程 + 内存状态（中等）

限流计数器 (`request_counter`)、封禁列表 (`blocked_ips`)、活跃会话 (`active_sessions`)、登录尝试 (`login_attempts`) 全部保存在内存中。多进程部署（如 `uvicorn --workers 4`）时这些状态不共享，限流形同虚设。虽然有 Redis 模式可选，但默认模式无法水平扩展。

#### 问题 X3：同步数据库操作阻塞异步事件循环（中等）

所有数据库操作（`create_record`、`get_all_records` 等）都是同步函数，但被 `async` 路由直接调用。FastAPI 虽然会自动将同步依赖放到线程池执行，但路由函数中直接调用同步函数时，是在事件循环线程中阻塞执行的（因为路由是 `async def`）。

示例：

```python
@app.get("/api/records", ...)
async def api_get_records(...):
    result = get_all_records(...)  # 同步阻塞！在 async 函数中会阻塞事件循环
    return result
```

应改为 `def`（让 FastAPI 自动线程池化）或使用 `run_in_executor`。

#### 问题 X4：前端无组件化、无构建流程（中等）

`index.html`（1987 行）和 `admin/index.html`（3334 行）都是单文件巨型 HTML，JS 全部内嵌。这导致：
- 无法复用组件
- 无法使用 TypeScript 类型检查
- 无法 tree-shaking / 代码分割
- CDN 依赖无法本地缓存管理

### 7.3 改进建议

1. **抽取组分常量为 Single Source of Truth**：
   ```python
   # backend/constants.py
   COMPONENT_FIELDS = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
   COMPONENT_LABELS = {'x_ch4': 'CH₄', 'x_c2h6': 'C₂H₆', ...}
   ```
2. **将 `async def` 路由改为 `def`**，或在 async 路由中使用 `await run_in_executor(None, sync_func)`
3. **若需多进程**：强制开启 Redis 模式用于共享状态

---

## 八、其他问题

### 8.1 `auth.py` 中使用 `open_security_connection()` 而非 context manager（中等）

```python
def _get_user_from_db(username: str):
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    ...
    conn.close()  # 异常时不会执行！
```

应使用 `with get_security_connection(...) as conn:` 确保连接释放。`auth.py` 中至少有 4 处类似问题（`_get_user_from_db`、`_upsert_user`、`list_users`）。`security.py` 中也有多处相同问题（`add_crawler_block`、`record_login`、`create_session`、`get_login_logs` 等）。

### 8.2 `@app.on_event("startup")` 已弃用（轻微）

FastAPI 推荐使用 `lifespan` 上下文管理器替代 `@app.on_event("startup/shutdown")`。

### 8.3 `datetime.utcnow()` 已弃用（轻微）

Python 3.12+ 中 `datetime.utcnow()` 已弃用，应使用 `datetime.now(timezone.utc)`。

### 8.4 缓存序列化使用 pickle（安全风险）

`cache.py` 中使用 `pickle.loads()` 反序列化 Redis 中的值。如果 Redis 被攻击者控制，可以构造恶意 pickle payload 执行任意代码。应改用 JSON 序列化或 `msgpack`。

---

## 九、重构优先级总览

### 🔴 高优先级（影响安全/正确性）

| # | 问题 | 所在文件 | 建议 |
|---|------|----------|------|
| S1 | 手写 JWT | `auth.py` | 替换为 PyJWT |
| S2 | 默认 SECRET_KEY | `auth.py` | 未设置时拒绝启动 |
| S5 | 备份路径遍历 | `main.py` | 校验 filename |
| E1 | bare except 吞异常 | `auth.py`, `security.py` | 区分异常类型，使用 logger |
| A6 | 会话撤销空实现 | `main.py:1284-1288` | 补全逻辑 |

### 🟡 中优先级（影响可维护性/性能）

| # | 问题 | 所在文件 | 建议 |
|---|------|----------|------|
| P1 | main.py 上帝文件 | `main.py` | 拆分为 routers/ |
| P2 | 缺 Service 层 | 全局 | 引入 services/ |
| P4 | 模块级副作用 | `database.py`, `data_review.py` | 延迟初始化 |
| A3 | 返回格式不统一 | `main.py` | 统一信封 |
| X1 | 组分硬编码 15+ 处 | 全局 | 抽取常量 |
| X3 | 同步阻塞事件循环 | `main.py` | 改为 def 或 run_in_executor |
| 8.1 | 连接不使用 context manager | `auth.py`, `security.py` | 改为 with 语句 |
| D5 | 跨函数无事务 | `database.py` 等 | 支持事务传递 |
| 8.4 | pickle 反序列化 | `cache.py` | 改为 JSON |

### 🟢 低优先级（改进体验/规范性）

| # | 问题 | 所在文件 | 建议 |
|---|------|----------|------|
| A1 | 新旧图表 API 共存 | `main.py` | 移除旧版 |
| A2 | 动词式 URL | `main.py` | 渐进式改为名词化 |
| A4 | 无版本前缀 | `main.py` | 添加 /api/v1/ |
| P3 | 请求模型散落 | `main.py` | 移入 schemas/ |
| P5 | _ensure_index 重复 | 3 个文件 | 提取到 db.py |
| D1 | 缺数据溯源字段 | `database.py` | 增加 source/reference |
| D6 | DDL 双来源 | `database.py` + `migrations/` | 统一管理 |
| 8.2 | 弃用的 on_event | `main.py` | 改用 lifespan |
| 8.3 | 弃用的 utcnow | `auth.py` | 改用 now(utc) |

---

## 十、总结

本系统作为一个科学数据查询系统，**功能覆盖面较全**（查询、管理、审核、备份、安全一应俱全），**安全意识较强**（限流、防爬、TOTP、审计日志），技术选型（FastAPI + SQLite/MySQL）也比较务实。

**最核心的改进方向**按优先级排序：

1. **修复安全漏洞**：替换手写 JWT、强制 SECRET_KEY、修复路径遍历
2. **修复错误处理**：消除静默吞异常、统一使用 logger、修复数据库连接泄漏
3. **拆分 main.py**：从 2513 行的上帝文件拆分为按领域组织的路由模块
4. **引入 Service 层**：解耦路由与业务逻辑
5. **抽取组分常量**：消除 15+ 处硬编码，使添加新组分成为配置级变更
6. **修复异步/同步混用问题**：避免在 async 路由中直接调用同步 DB 操作
