# 架构审查报告：cursor_shujuku 项目

> 审查日期：2026-02-09  
> 项目：气体水合物相平衡查询系统  
> 技术栈：FastAPI + SQLite/MySQL + Vue 3 (CDN) + Redis  
> 代码总量：约 12,000+ 行（后端 ~6,000 行，前端 ~6,000 行）

---

## 一、总体架构评估

### 1.1 当前架构概览

```
workspace/
├── backend/          # 后端 Python 模块（扁平结构）
│   ├── main.py       # 1994 行 - 所有路由 + 中间件 + 业务逻辑
│   ├── database.py   # 数据库 CRUD 操作
│   ├── db.py         # 数据库连接管理
│   ├── models.py     # Pydantic 数据模型
│   ├── auth.py       # 认证模块
│   ├── security.py   # 安全模块（限流/防爬/审计/会话/密码策略）
│   ├── cache.py      # Redis 缓存
│   ├── backup.py     # 数据库备份
│   ├── data_review.py    # 数据审核
│   ├── data_validation.py # 数据校验
│   ├── totp.py       # 两步验证
│   └── config.py     # 基础配置
├── frontend/         # 前端静态文件
│   ├── index.html    # 公开查询页面（952 行）
│   ├── admin/index.html  # 后台管理页面（3334 行）
│   ├── css/style.css
│   └── js/app.js, charts.js
├── migrations/       # SQL 迁移脚本（未编程化使用）
├── scripts/          # 运维脚本
└── [大量散落文件]     # 测试、工具、文档
```

### 1.2 核心问题总结

| 问题类别 | 严重程度 | 影响范围 |
|---------|---------|---------|
| `main.py` 单体路由文件（1994 行） | 🔴 严重 | 可维护性、可测试性 |
| 数据库连接管理不一致（存在资源泄漏风险） | 🔴 严重 | 稳定性、安全性 |
| SQL 注入风险（字符串拼接 SQL） | 🔴 严重 | 安全性 |
| 路由重复定义 | 🟡 中等 | 可维护性 |
| 模块导入时触发数据库初始化 | 🟡 中等 | 可测试性、可预测性 |
| 代码重复（`_ensure_index` 三处重复） | 🟡 中等 | 可维护性 |
| 组分常量硬编码散落各处 | 🟡 中等 | 可维护性 |
| 错误处理不一致 | 🟡 中等 | 可靠性 |
| 配置分散在多个文件中 | 🟡 中等 | 可运维性 |
| 自定义 JWT 实现 | 🟡 中等 | 安全性 |
| 缓存装饰器不支持 async | 🟡 中等 | 功能正确性 |
| 根目录文件散乱 | 🟢 轻微 | 工程规范 |

---

## 二、详细问题分析

### 2.1 🔴 P0 - `main.py` 单体文件问题

**问题**：`main.py` 长达 1994 行，包含了系统所有功能：

- 全部 60+ 个 API 路由定义
- 7 个 Pydantic 请求模型（`LoginRequest`、`BatchDeleteRequest` 等）
- HTTP 安全中间件
- 文件解析逻辑（`parse_import_content`、`parse_import_row`）
- 内联业务逻辑（热力图计算、散点分布、组分查询等）
- 静态文件服务路由
- 应用启动事件

**影响**：
- 多人协作时极易产生合并冲突
- 无法对单个功能模块进行独立测试
- 新增功能只能在同一文件中追加，技术债务持续增长

**重构建议**：

```
backend/
├── routers/              # 路由层（按业务域拆分）
│   ├── __init__.py
│   ├── records.py        # 数据记录 CRUD
│   ├── charts.py         # 图表数据
│   ├── query.py          # 公开查询 API
│   ├── auth.py           # 认证相关路由
│   ├── review.py         # 数据审核路由
│   ├── backup.py         # 备份管理路由
│   ├── security.py       # 安全日志路由
│   ├── import_export.py  # 导入导出路由
│   └── templates.py      # 模板下载
├── schemas/              # 请求/响应模型
│   ├── __init__.py
│   ├── records.py
│   ├── auth.py
│   └── common.py
├── services/             # 业务逻辑层（新增）
│   ├── __init__.py
│   ├── record_service.py
│   ├── chart_service.py
│   ├── import_service.py
│   └── query_service.py
├── repositories/         # 数据访问层（从 database.py 演化）
│   ├── __init__.py
│   ├── gas_mixture_repo.py
│   └── review_repo.py
├── core/                 # 核心基础设施
│   ├── config.py
│   ├── database.py       # 连接管理
│   ├── constants.py      # 全局常量
│   ├── exceptions.py     # 自定义异常
│   └── dependencies.py   # FastAPI 依赖注入
├── middleware/
│   ├── security.py
│   └── cors.py
└── main.py               # 仅负责 app 创建和路由注册（< 100 行）
```

---

### 2.2 🔴 P0 - 数据库连接管理不一致

**问题**：项目中存在两种数据库连接模式，混合使用导致资源泄漏风险。

**安全模式**（`database.py`、`data_review.py` 使用）：
```python
# ✅ 使用 context manager，自动关闭连接
with get_connection(dict_cursor=True) as conn:
    cursor = conn.cursor()
    # ...
```

**危险模式**（`auth.py`、`totp.py`、`security.py` 使用）：
```python
# ❌ 手动 open/close，异常时可能泄漏
conn = open_security_connection(dict_cursor=True)
cursor = conn.cursor()
# ... 如果这里抛异常 ...
conn.close()  # 永远不会执行
```

**具体位置**：
- `auth.py`：`_get_user_from_db()`、`_upsert_user()`、`list_users()` — 全部使用手动连接
- `totp.py`：`init_totp_table()`、`setup_totp()`、`enable_totp()`、`disable_totp()`、`is_totp_enabled()`、`verify_user_totp()`、`get_totp_status()`、`regenerate_backup_codes()` — 全部使用手动连接
- `security.py`：`add_crawler_block()`、`record_login()`、`get_login_logs()`、`create_session()` 等 — 多处使用手动连接

**修复建议**：统一使用 `get_security_connection()` 上下文管理器。

---

### 2.3 🔴 P0 - SQL 注入风险

**问题**：多处使用 Python 字符串格式化构建 SQL 查询，存在潜在的 SQL 注入风险。

**危险代码示例**：

```python
# data_review.py - move_duplicates_to_review()
ids_str = ','.join(str(x) for x in dup['ids'])
cursor.execute(f'''
    SELECT * FROM gas_mixture WHERE id IN ({ids_str})
''')

# data_review.py - approve_group()
ids_str = ','.join(str(x) for x in selected_pressures)
cursor.execute(f'''
    SELECT * FROM pending_review WHERE id IN ({ids_str}) AND group_id = ?
''', (group_id,))

# main.py - api_available_components()
conditions.append(f"{comp} > 0")  # comp 来自用户请求
cursor.execute(f"SELECT COUNT(*) as count FROM gas_mixture WHERE {where_clause}")
```

虽然 `dup['ids']` 是数字列表、`comp` 来自预定义列表有一定保护，但这种编码习惯非常危险。

**修复建议**：使用参数化占位符：
```python
placeholders = ','.join('?' * len(ids))
cursor.execute(f'SELECT * FROM gas_mixture WHERE id IN ({placeholders})', ids)
```

对于动态列名，应使用白名单验证：
```python
VALID_COMPONENTS = {'x_ch4', 'x_c2h6', ...}
if comp not in VALID_COMPONENTS:
    raise ValueError(f"Invalid component: {comp}")
```

---

### 2.4 🟡 P1 - 路由重复定义

**问题**：`main.py` 中同时存在两套图表 API，功能完全重复：

| 路由 A（`/api/charts/*`）| 路由 B（`/api/chart/*`）| 说明 |
|---|---|---|
| `/api/charts/temperature` | `/api/chart/temperature` | 温度分布 |
| `/api/charts/pressure` | `/api/chart/pressure` | 压力分布 |
| `/api/charts/scatter` | `/api/chart/scatter` | 散点图 |

其中 `/api/charts/*` 系列带有 `@cached` 装饰器，`/api/chart/*` 系列没有。两者返回格式相同但行为不一致。

此外，`api_chart_temperature()` 函数名在两个路由中完全相同（FastAPI 允许但会导致 OpenAPI 文档冲突）。

**修复建议**：保留一套路由（建议 `/api/charts/*`），删除重复定义。

---

### 2.5 🟡 P1 - 模块导入时的副作用

**问题**：三个模块在导入时自动执行数据库初始化操作：

```python
# database.py 末尾（第 421 行）
init_database()

# data_review.py 末尾（第 504 行）
init_review_tables()

# totp.py 末尾（第 282 行）
init_totp_table()
```

**影响**：
- 单元测试时 `import backend.database` 会自动连接并修改真实数据库
- 导入顺序影响行为，增加调试难度
- 无法在不同环境中使用不同初始化策略

**修复建议**：将所有初始化移到 `startup_event()` 中统一管理：
```python
@app.on_event("startup")
async def startup_event():
    init_database()
    init_review_tables()
    init_totp_table()
    init_security()
    # ...
```

---

### 2.6 🟡 P1 - 代码重复

#### 2.6.1 `_ensure_index` 函数重复 3 次

完全相同的函数出现在：
- `backend/database.py`（第 11-27 行）
- `backend/security.py`（第 103-119 行）
- `backend/data_review.py`（第 10-26 行）

**修复**：提取到 `backend/db.py` 中统一导入。

#### 2.6.2 组分列表硬编码

`['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']` 这个列表至少出现在 **10+ 处**：

- `main.py`：4 处
- `database.py`：1 处
- `data_review.py`：多处隐含
- `data_validation.py`：2 处
- `models.py`：隐含在模型定义中

**修复**：创建 `constants.py`：
```python
COMPONENT_FIELDS = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
COMPONENT_LABELS = {'x_ch4': 'CH₄', 'x_c2h6': 'C₂H₆', ...}
```

#### 2.6.3 记录插入/读取 SQL 重复

`gas_mixture` 表的 INSERT 语句在 `database.py`（`create_record`、`batch_create_records`）和 `data_review.py`（`approve_group`）中重复出现。

---

### 2.7 🟡 P1 - 错误处理不一致

当前项目存在 **4 种不同的错误处理模式**：

| 模式 | 使用位置 | 问题 |
|------|---------|------|
| `except Exception: return None` | `auth.py` `_get_user_from_db()` | 吞掉所有错误，隐藏真正的bug |
| `except Exception: pass` | `auth.py` `list_users()` | 数据库完全不可用也不报错 |
| `except Exception as e: print(...)` | `security.py` 多处 | 日志不规范，生产环境难以追踪 |
| `raise HTTPException` | `main.py` 路由层 | 正确但不够统一 |

**修复建议**：

1. 创建自定义异常体系：
```python
# exceptions.py
class AppError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code

class NotFoundError(AppError): ...
class ValidationError(AppError): ...
class AuthenticationError(AppError): ...
```

2. 使用 FastAPI 全局异常处理器：
```python
@app.exception_handler(AppError)
async def app_error_handler(request, exc):
    return JSONResponse(status_code=..., content={"detail": exc.message, "code": exc.code})
```

3. 使用标准 `logging` 替代 `print`。

---

### 2.8 🟡 P1 - 配置管理分散

当前配置散落在 5 个不同文件中：

| 文件 | 配置项 |
|------|--------|
| `config.py` | 数据库路径、CORS、备份目录 |
| `auth.py` | SECRET_KEY、TOKEN 过期时间、管理员账户 |
| `security.py` | 限流参数、登录限制、密码策略、会话配置、爬虫规则、Redis |
| `backup.py` | 备份间隔、最大备份数 |
| `cache.py` | Redis 连接参数 |

**修复建议**：统一到 `config.py` 或使用 Pydantic `BaseSettings`：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_path: str = "gas_data.db"
    database_url: str = ""
    
    # Security
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 1440
    rate_limit_window: int = 60
    rate_limit_max_requests: int = 60
    
    # Redis
    redis_url: str = ""
    
    # Backup
    backup_dir: str = "backups"
    max_backups: int = 10
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

### 2.9 🟡 P1 - 安全问题

#### 2.9.1 自定义 JWT 实现
`auth.py` 手写了完整的 JWT 编码/解码/验证逻辑（约 80 行）。虽然实现看起来正确，但自行实现密码学相关代码始终存在风险。

**建议**：使用成熟的 `python-jose` 或 `PyJWT` 库。

#### 2.9.2 默认 SECRET_KEY
```python
DEFAULT_SECRET_KEY = "your-super-secret-key-change-in-production-2024"
```
如果用户忘记配置环境变量，系统会使用此默认值运行，所有 JWT token 可被伪造。

**建议**：
- 启动时如检测到默认值，在非开发模式下拒绝启动
- 或自动生成随机密钥（但需注意多实例场景）

#### 2.9.3 内存中的管理员凭据
```python
ADMIN_USERS = {
    ADMIN_USERNAME: {
        "password_hash": None,
        ...
    }
}
```
管理员密码哈希存储在 Python 字典中，进程内存可被读取。且这个字典与数据库中的用户表形成了双重来源（dual source of truth）。

---

### 2.10 🟡 P1 - 缓存装饰器与 async 不兼容

`cache.py` 中的 `cached` 装饰器：

```python
def cached(ttl: int = 300, key_prefix: str = "func"):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):  # ← 普通函数，非 async
            ...
            result = func(*args, **kwargs)  # ← 对 async 函数返回 coroutine 而非结果
            ...
```

但在 `main.py` 中用于装饰 `async` 函数：
```python
@app.get("/api/statistics")
@cached(ttl=60)
async def api_statistics():  # ← async 函数
```

这会导致 `func(*args, **kwargs)` 返回一个 coroutine 对象而非实际结果，缓存的是 coroutine 而非数据。

**修复**：使用 `asyncio` 感知的装饰器或使用 `fastapi-cache2` 等专用库。

---

### 2.11 🟡 P1 - `security.py` 模块职责过重

`security.py`（891 行）承担了 **6 项完全不同的职责**：

1. API 限流（rate limiting）
2. 防爬虫检测
3. 登录日志记录
4. 会话管理（创建/验证/撤销）
5. 密码策略验证
6. 审计日志 + 数据修改历史

**修复建议**：按职责拆分为独立模块：
```
backend/security/
├── __init__.py
├── rate_limiter.py      # API 限流
├── anti_crawler.py      # 防爬虫
├── session_manager.py   # 会话管理
├── password_policy.py   # 密码策略
├── audit.py             # 审计日志
└── login_tracker.py     # 登录日志
```

---

### 2.12 🟢 P2 - 数据库设计评估

#### 合理之处
- `gas_mixture` 表设计简洁，字段清晰
- 索引覆盖了主要查询维度（温度、压力、各组分）
- 使用 `created_at` / `updated_at` 时间戳追踪变更
- 审核流程设计（`pending_review` 表）思路合理

#### 可改进之处

1. **缺少复合索引优化**：常见查询模式 "按组分组合 + 温度查询" 缺少针对性复合索引
2. **`pending_review` 表与 `gas_mixture` 字段完全重复**：可考虑使用状态字段在同一表中管理，或者通过外键引用
3. **`_get_next_group_number` 性能问题**：当前实现扫描全表来获取最大编号：
   ```python
   cursor.execute('SELECT group_id FROM pending_review')  # 全表扫描
   ```
   应改为：`SELECT MAX(CAST(SUBSTR(group_id, 2) AS INTEGER)) FROM pending_review`
4. **无数据库版本管理**：`migrations/` 目录存在 SQL 文件，但无迁移工具集成（如 Alembic）
5. **双数据库设计** (`gas_data.db` + `security.db`) 增加了运维复杂度，但隔离性好，可接受

---

### 2.13 🟢 P2 - 根目录文件散乱

根目录包含大量不应暴露或位置不当的文件：

```
# 应移入 scripts/ 或 tools/
check_database.py, check_duplicates.py, convert_code_doc.py, convert_to_docx.py
gen_arch_img.py, rebuild_manual.py, start_cursor_collaboration.py

# 应移入 tests/
test_backend_api.py, test_cache.py, test_cursor_token.py, test_review.py, minimal_test.py

# 应移入 docs/ 或删除
CURSOR_TASK.md, MODEL_TASKS.md, PROJECT_STATUS.md, README_CURSOR.md
cursor_commands_20260209_095744.md, cursor_quick_test.md, CURSOR_TOKEN_ISSUE_REPORT.md
CURSOR_WORKFLOW.md, START_HERE.md

# 数据文件应在 .gitignore
date.csv
```

---

### 2.14 🟢 P2 - 前端架构

- `admin/index.html` 为 3334 行的单体文件，所有 HTML/CSS/JS 混合
- 使用 Vue 3 CDN 模式，无构建系统、无组件化
- 对于当前项目规模勉强可接受，但如需持续迭代建议迁移到 Vite + Vue SFC

---

## 三、重构优先级排序

### Phase 1 - 安全与稳定性修复（立即执行）

| 序号 | 任务 | 工作量 | 风险 |
|------|------|--------|------|
| 1.1 | 修复数据库连接泄漏（`auth.py`、`totp.py`、`security.py` 统一使用 context manager） | 2h | 低 |
| 1.2 | 修复 SQL 注入风险（`data_review.py`、`main.py` 使用参数化查询） | 1h | 低 |
| 1.3 | 修复缓存装饰器 async 兼容性 | 1h | 低 |
| 1.4 | 删除重复路由（`/api/chart/*`） | 0.5h | 低 |

### Phase 2 - 架构优化（1-2 周）

| 序号 | 任务 | 工作量 | 风险 |
|------|------|--------|------|
| 2.1 | 拆分 `main.py` 为多个 Router 模块 | 4h | 中 |
| 2.2 | 提取公共常量和工具函数（消除代码重复） | 2h | 低 |
| 2.3 | 统一配置管理（`Pydantic BaseSettings`） | 3h | 中 |
| 2.4 | 建立统一错误处理机制 | 2h | 低 |
| 2.5 | 移除模块导入时的数据库初始化副作用 | 1h | 中 |
| 2.6 | 拆分 `security.py` 为独立子模块 | 2h | 低 |

### Phase 3 - 工程化提升（持续改进）

| 序号 | 任务 | 工作量 | 风险 |
|------|------|--------|------|
| 3.1 | 引入标准 JWT 库替换自定义实现 | 2h | 中 |
| 3.2 | 引入 Alembic 数据库迁移管理 | 4h | 中 |
| 3.3 | 整理根目录文件结构 | 1h | 低 |
| 3.4 | 添加单元测试框架和基础测试 | 8h | 低 |
| 3.5 | 引入 logging 模块替代 print | 1h | 低 |
| 3.6 | 增加 Service 层分离业务逻辑 | 8h | 中 |

---

## 四、推荐的目标架构

```
backend/
├── main.py                 # 应用入口（仅注册路由和中间件，< 80 行）
├── core/
│   ├── config.py           # 统一配置（Pydantic BaseSettings）
│   ├── constants.py        # 全局常量（组分列表、字段映射等）
│   ├── database.py         # 连接管理 + 通用 DB 工具
│   ├── exceptions.py       # 自定义异常
│   ├── dependencies.py     # FastAPI 依赖注入（认证、分页等）
│   └── logging.py          # 日志配置
├── models/
│   ├── schemas.py          # Pydantic 请求/响应模型
│   └── domain.py           # 业务领域模型
├── routers/
│   ├── records.py          # /api/records
│   ├── charts.py           # /api/charts
│   ├── query.py            # /api/query, /api/components
│   ├── auth.py             # /api/auth
│   ├── review.py           # /api/review
│   ├── backup.py           # /api/backup
│   ├── security_routes.py  # /api/security
│   └── import_export.py    # /api/import, /api/export, /api/template
├── services/
│   ├── record_service.py
│   ├── chart_service.py
│   ├── import_service.py
│   ├── query_service.py
│   └── review_service.py
├── repositories/
│   ├── gas_mixture_repo.py
│   ├── review_repo.py
│   └── base.py
├── security/
│   ├── auth.py             # JWT + 密码加密
│   ├── totp.py
│   ├── rate_limiter.py
│   ├── session.py
│   ├── audit.py
│   └── password_policy.py
├── middleware/
│   ├── security.py
│   └── error_handler.py
├── cache/
│   └── redis_cache.py
└── backup/
    └── backup_manager.py
```

---

## 五、结论

该项目功能实现完整（CRUD、认证、TOTP、数据审核、备份、缓存等），已具备较好的业务能力。但在架构层面存在以下核心瓶颈：

1. **单体路由文件**是当前最大的可维护性障碍
2. **数据库连接管理不一致**是最大的稳定性风险
3. **缺少分层架构**限制了可测试性和可扩展性

建议按照 Phase 1 → Phase 2 → Phase 3 的优先级逐步重构，每个 Phase 完成后均可独立部署验证，风险可控。
