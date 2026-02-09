# 架构优化实施计划

> 基于 PR #2 架构审查报告（ARCHITECTURE_REVIEW.md）  
> 制定日期：2026-02-09  
> 项目：气体水合物相平衡查询系统（cursor_shujuku）  
> 状态：待执行

---

## 一、问题优先级排序

根据架构审查中发现的问题，按照 **安全影响 > 稳定性影响 > 可维护性影响 > 工程规范** 的原则进行优先级排序。

### P0 - 紧急（安全与稳定性，必须立即修复）

| 编号 | 问题 | 严重程度 | 影响范围 | 涉及文件 |
|------|------|---------|---------|---------|
| P0-1 | SQL 注入风险：字符串拼接构建 SQL 查询 | 🔴 严重 | 安全性 | `data_review.py`, `main.py`, `database.py` |
| P0-2 | 数据库连接泄漏：手动 open/close 无异常保护 | 🔴 严重 | 稳定性 | `auth.py`(3处), `totp.py`(8处), `security.py`(12处) |
| P0-3 | 缓存装饰器不兼容 async：缓存 coroutine 对象而非结果 | 🔴 严重 | 功能正确性 | `cache.py`, `main.py` |

### P1 - 高优先级（架构与可维护性）

| 编号 | 问题 | 严重程度 | 影响范围 | 涉及文件 |
|------|------|---------|---------|---------|
| P1-1 | `main.py` 单体路由文件（1994行，60+路由） | 🟡 中等 | 可维护性、可测试性 | `main.py` |
| P1-2 | 路由重复定义（`/api/chart/*` 与 `/api/charts/*`） | 🟡 中等 | 可维护性 | `main.py` |
| P1-3 | 模块导入时触发数据库初始化（副作用） | 🟡 中等 | 可测试性 | `database.py`, `data_review.py`, `totp.py` |
| P1-4 | 代码重复：`_ensure_index` 函数3处重复 | 🟡 中等 | 可维护性 | `database.py`, `security.py`, `data_review.py` |
| P1-5 | 组分常量硬编码散落各处（10+处） | 🟡 中等 | 可维护性 | `main.py`, `database.py`, `data_validation.py` 等 |
| P1-6 | 错误处理不一致（4种不同模式） | 🟡 中等 | 可靠性 | `auth.py`, `security.py`, `main.py` |
| P1-7 | 配置分散在5个文件中 | 🟡 中等 | 可运维性 | `config.py`, `auth.py`, `security.py`, `backup.py`, `cache.py` |
| P1-8 | `security.py` 职责过重（891行，6项职责） | 🟡 中等 | 可维护性 | `security.py` |
| P1-9 | 自定义 JWT 实现 + 默认 SECRET_KEY 风险 | 🟡 中等 | 安全性 | `auth.py` |
| P1-10 | 缓存装饰器与 async 不兼容 | 🟡 中等 | 功能正确性 | `cache.py` |

### P2 - 中优先级（工程化提升）

| 编号 | 问题 | 严重程度 | 影响范围 | 涉及文件 |
|------|------|---------|---------|---------|
| P2-1 | 数据库设计优化（缺少复合索引、全表扫描等） | 🟢 轻微 | 性能 | `database.py`, `data_review.py` |
| P2-2 | 根目录文件散乱（测试、工具、文档混杂） | 🟢 轻微 | 工程规范 | 根目录 |
| P2-3 | 无数据库版本管理工具（Alembic） | 🟢 轻微 | 可运维性 | `migrations/` |
| P2-4 | 缺少单元测试框架和基础测试 | 🟢 轻微 | 质量保障 | 无 |
| P2-5 | 使用 `print` 而非 `logging` 模块 | 🟢 轻微 | 可运维性 | `security.py` 等多处 |
| P2-6 | 前端单体文件（`admin/index.html` 3334行） | 🟢 轻微 | 前端可维护性 | `frontend/admin/index.html` |

---

## 二、分阶段实施计划

### ═══════════════════════════════════════════
### Phase 1：安全与稳定性修复（紧急，1-2天）
### ═══════════════════════════════════════════

> **目标**：消除所有安全漏洞和稳定性风险  
> **风险**：低（修改范围小，行为不变）  
> **验证方式**：手动测试关键 API + 现有功能回归

---

#### 任务 1.1：修复 SQL 注入风险
- **对应问题**：P0-1
- **工作量**：1.5 小时
- **优先级**：★★★★★

**具体步骤**：

1. **`data_review.py` - `move_duplicates_to_review()` 函数**
   - 将 `ids_str = ','.join(str(x) for x in dup['ids'])` + `f'''SELECT * FROM gas_mixture WHERE id IN ({ids_str})'''`
   - 改为：`placeholders = ','.join('?' * len(dup['ids']))` + `cursor.execute(f'SELECT * FROM gas_mixture WHERE id IN ({placeholders})', dup['ids'])`

2. **`data_review.py` - `approve_group()` 函数**
   - 将 `ids_str = ','.join(str(x) for x in selected_pressures)` 的字符串拼接
   - 改为参数化占位符模式

3. **`main.py` - `api_available_components()` 函数（约第1429行）**
   - 将 `conditions.append(f"{comp} > 0")` 中的 `comp` 变量
   - 增加白名单验证：确认 `comp` 存在于 `VALID_COMPONENTS` 常量集合中

4. **`main.py` - 其他动态 SQL 构建处（约第1442, 1489, 1499, 1505, 1689行）**
   - 逐一检查并添加白名单验证或参数化查询

**验收标准**：
- [ ] 所有 SQL 查询使用参数化占位符或白名单验证
- [ ] 不存在 f-string 拼接用户输入到 SQL 的代码
- [ ] 原有功能正常（查询、审核、组分筛选）

---

#### 任务 1.2：修复数据库连接泄漏
- **对应问题**：P0-2
- **工作量**：2.5 小时
- **优先级**：★★★★★

**具体步骤**：

1. **`auth.py` - 3处连接泄漏**
   - `_get_user_from_db()`（第80行）：将 `conn = open_security_connection()` 改为 `with get_security_connection() as conn:`
   - `_upsert_user()`（第106行）：同上
   - `list_users()`（第382行）：同上
   - 需在文件头部导入 `get_security_connection`

2. **`totp.py` - 8处连接泄漏**
   - `init_totp_table()`（第104行）
   - `setup_totp()`（第133行）
   - `enable_totp()`（第157行）
   - `disable_totp()`（第181行）
   - `is_totp_enabled()`（第192行）
   - `verify_user_totp()`（第202行）
   - `get_totp_status()`（第240行）
   - `regenerate_backup_codes()`（第271行）
   - 全部改为使用 `with get_security_connection() as conn:` 上下文管理器

3. **`security.py` - 12处连接泄漏**
   - `add_crawler_block()`（第354行）
   - `record_login()`（第379行）
   - `check_login_attempts()`（第448行）
   - `record_login_attempt()`（第502行）
   - `create_session()`（第578行）
   - `validate_session()`（第629行）
   - `revoke_session()`（第643行）
   - `get_user_sessions()`（第669行）
   - `record_audit_log()`（第759行）
   - `get_audit_logs()`（第774行）
   - `record_data_history()`（第815行）
   - `get_data_history()`（第845行）
   - 全部改为使用 `with get_security_connection() as conn:` 上下文管理器

**验收标准**：
- [ ] 项目中不再存在裸 `open_security_connection()` 调用（除 `db.py` 中的定义和 `get_security_connection` 内部使用）
- [ ] 所有数据库连接通过 context manager 管理
- [ ] 异常情况下连接能正确关闭

---

#### 任务 1.3：修复缓存装饰器 async 兼容性
- **对应问题**：P0-3 / P1-10
- **工作量**：1 小时
- **优先级**：★★★★★

**具体步骤**：

1. **修改 `cache.py` 中的 `cached` 装饰器**
   - 检测被装饰函数是否为 async（使用 `asyncio.iscoroutinefunction`）
   - 对 async 函数使用 `await func(*args, **kwargs)` 获取结果
   - 对同步函数保持 `func(*args, **kwargs)`

2. **实现参考**：
   ```python
   import asyncio
   
   def cached(ttl: int = 300, key_prefix: str = "func"):
       def decorator(func: Callable):
           if asyncio.iscoroutinefunction(func):
               @wraps(func)
               async def async_wrapper(*args, **kwargs):
                   # 缓存逻辑...
                   result = await func(*args, **kwargs)
                   # 存储缓存...
                   return result
               return async_wrapper
           else:
               @wraps(func)
               def sync_wrapper(*args, **kwargs):
                   # 缓存逻辑...
                   result = func(*args, **kwargs)
                   # 存储缓存...
                   return result
               return sync_wrapper
       return decorator
   ```

**验收标准**：
- [ ] `@cached` 装饰 async 函数时正确 await 并缓存结果
- [ ] `@cached` 装饰同步函数时行为不变
- [ ] `/api/statistics` 等缓存路由返回正确数据（非 coroutine 对象）

---

#### 任务 1.4：删除重复路由
- **对应问题**：P1-2
- **工作量**：0.5 小时
- **优先级**：★★★★

**具体步骤**：

1. **确认保留哪套路由**：
   - 保留 `/api/charts/*` 系列（有缓存装饰器，约第302-392行）
   - 删除 `/api/chart/*` 系列（约第449-600行）

2. **检查前端调用**：
   - 搜索 `frontend/` 中对 `/api/chart/` 的引用
   - 将所有前端调用统一指向 `/api/charts/`

3. **如果需要向后兼容**：
   - 添加重定向路由：`/api/chart/{path}` → `/api/charts/{path}`

**验收标准**：
- [ ] 不存在功能重复的路由
- [ ] 前端所有图表功能正常
- [ ] OpenAPI 文档无命名冲突

---

### ═══════════════════════════════════════════
### Phase 2：架构重构（核心，1-2周）
### ═══════════════════════════════════════════

> **目标**：建立清晰的分层架构，提升可维护性  
> **风险**：中（涉及文件拆分和重组）  
> **验证方式**：全量 API 功能回归测试 + 前端集成测试

---

#### 任务 2.1：提取公共常量和工具函数
- **对应问题**：P1-4, P1-5
- **工作量**：2 小时
- **优先级**：★★★★
- **前置依赖**：无

**具体步骤**：

1. **创建 `backend/constants.py`**
   ```python
   # 组分字段列表
   COMPONENT_FIELDS = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
   
   # 组分显示名称映射
   COMPONENT_LABELS = {
       'x_ch4': 'CH₄', 'x_c2h6': 'C₂H₆', 'x_c3h8': 'C₃H₈',
       'x_co2': 'CO₂', 'x_n2': 'N₂', 'x_h2s': 'H₂S', 'x_ic4h10': 'iC₄H₁₀'
   }
   
   # 有效组分集合（用于白名单验证）
   VALID_COMPONENT_SET = set(COMPONENT_FIELDS)
   ```

2. **将 `_ensure_index` 函数统一到 `backend/db.py`**
   - 从 `database.py`、`security.py`、`data_review.py` 中删除重复定义
   - 在 `db.py` 中添加统一版本
   - 各文件改为 `from backend.db import ensure_index`

3. **替换所有硬编码的组分列表**
   - 逐文件搜索并替换为 `COMPONENT_FIELDS` 引用

**验收标准**：
- [ ] `_ensure_index` 仅在 `db.py` 中定义一次
- [ ] 组分列表仅在 `constants.py` 中定义一次
- [ ] 全文搜索无硬编码的组分列表

---

#### 任务 2.2：移除模块导入时的数据库初始化副作用
- **对应问题**：P1-3
- **工作量**：1 小时
- **优先级**：★★★★
- **前置依赖**：无

**具体步骤**：

1. **删除模块末尾的自动初始化调用**
   - `database.py` 第421行：删除 `init_database()`
   - `data_review.py` 第504行：删除 `init_review_tables()`
   - `totp.py` 第282行：删除 `init_totp_table()`

2. **在 `main.py` 的 `startup_event()` 中统一调用初始化**
   ```python
   @app.on_event("startup")
   async def startup_event():
       init_database()
       init_review_tables()
       init_totp_table()
       init_security()
       init_backup_system()
   ```

3. **确保导入顺序不影响初始化**

**验收标准**：
- [ ] `import backend.database` 不再触发数据库操作
- [ ] 应用启动时所有表正确创建
- [ ] 启动顺序可控

---

#### 任务 2.3：拆分 `main.py` 为多个 Router 模块
- **对应问题**：P1-1
- **工作量**：5 小时
- **优先级**：★★★★
- **前置依赖**：任务 2.1、2.2

**具体步骤**：

1. **创建 `backend/routers/` 目录**

2. **按业务域拆分路由**：

   | 路由模块 | 包含路由 | 预计行数 |
   |---------|---------|---------|
   | `routers/records.py` | 数据记录 CRUD（`/api/records/*`） | ~200行 |
   | `routers/charts.py` | 图表数据（`/api/charts/*`） | ~200行 |
   | `routers/query.py` | 公开查询（`/api/query/*`, `/api/components/*`） | ~250行 |
   | `routers/auth.py` | 认证（`/api/login`, `/api/users/*`） | ~150行 |
   | `routers/review.py` | 数据审核（`/api/review/*`） | ~100行 |
   | `routers/backup.py` | 备份管理（`/api/backup/*`） | ~100行 |
   | `routers/security_routes.py` | 安全日志（`/api/security/*`） | ~100行 |
   | `routers/import_export.py` | 导入导出（`/api/import`, `/api/export`） | ~250行 |

3. **提取请求模型到 `backend/schemas/`**
   - 将 `main.py` 中内联定义的 `LoginRequest`、`BatchDeleteRequest` 等 Pydantic 模型
   - 移到 `backend/schemas/` 下按模块组织

4. **精简 `main.py`**
   - 仅保留 FastAPI app 创建、中间件配置、路由注册
   - 目标行数：< 100 行

5. **使用 `APIRouter`**
   ```python
   # routers/records.py
   from fastapi import APIRouter
   router = APIRouter(prefix="/api", tags=["Records"])
   
   @router.get("/records")
   async def get_records(...): ...
   ```

**验收标准**：
- [ ] `main.py` 行数 < 100
- [ ] 每个 router 文件职责单一
- [ ] 所有 API 端点功能不变
- [ ] OpenAPI 文档正确展示所有路由

---

#### 任务 2.4：统一配置管理
- **对应问题**：P1-7
- **工作量**：3 小时
- **优先级**：★★★
- **前置依赖**：任务 2.1

**具体步骤**：

1. **扩展 `backend/config.py`，使用 Pydantic BaseSettings**
   ```python
   from pydantic_settings import BaseSettings
   
   class Settings(BaseSettings):
       # 数据库
       database_path: str = "gas_data.db"
       database_url: str = ""
       security_db_path: str = "security.db"
       security_database_url: str = ""
       
       # 认证
       secret_key: str = "your-super-secret-key-change-in-production-2024"
       access_token_expire_minutes: int = 1440
       admin_username: str = "admin"
       admin_password: str = ""
       
       # 限流
       rate_limit_window: int = 60
       rate_limit_max_requests: int = 60
       rate_limit_block_duration: int = 300
       
       # 登录限制
       login_max_attempts: int = 5
       login_block_duration: int = 900
       
       # 密码策略
       password_min_length: int = 8
       password_require_uppercase: bool = True
       password_require_lowercase: bool = True
       password_require_digit: bool = True
       password_require_special: bool = False
       
       # 会话
       session_max_age: int = 86400
       session_max_per_user: int = 5
       
       # Redis
       redis_host: str = "localhost"
       redis_port: int = 6379
       redis_db: int = 0
       redis_password: str = ""
       
       # 备份
       backup_dir: str = "backups"
       max_backups: int = 10
       backup_interval: int = 21600
       
       # CORS
       cors_origins: str = ""
       
       class Config:
           env_file = ".env"
           env_file_encoding = "utf-8"
   
   settings = Settings()
   ```

2. **逐个替换各文件中的硬编码配置**
   - `auth.py`：`SECRET_KEY`、`ACCESS_TOKEN_EXPIRE_MINUTES`、`ADMIN_USERNAME` 等
   - `security.py`：`RATE_LIMIT_WINDOW`、`LOGIN_MAX_ATTEMPTS` 等
   - `backup.py`：`MAX_BACKUPS`、`BACKUP_INTERVAL`
   - `cache.py`：Redis 连接参数

3. **添加 `.env.example` 文件**

**验收标准**：
- [ ] 所有配置项集中在 `config.py` 的 `Settings` 类中
- [ ] 各模块通过 `from backend.config import settings` 获取配置
- [ ] `.env` 文件可覆盖所有配置项
- [ ] 提供 `.env.example` 示例文件

---

#### 任务 2.5：建立统一错误处理机制
- **对应问题**：P1-6
- **工作量**：2 小时
- **优先级**：★★★
- **前置依赖**：任务 2.3

**具体步骤**：

1. **创建 `backend/core/exceptions.py`**
   ```python
   class AppError(Exception):
       def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
           self.message = message
           self.code = code
           self.status_code = status_code
   
   class NotFoundError(AppError):
       def __init__(self, message: str = "资源不存在"):
           super().__init__(message, "NOT_FOUND", 404)
   
   class ValidationError(AppError):
       def __init__(self, message: str):
           super().__init__(message, "VALIDATION_ERROR", 422)
   
   class AuthenticationError(AppError):
       def __init__(self, message: str = "认证失败"):
           super().__init__(message, "AUTH_ERROR", 401)
   
   class PermissionError(AppError):
       def __init__(self, message: str = "权限不足"):
           super().__init__(message, "PERMISSION_ERROR", 403)
   ```

2. **注册全局异常处理器**（在 `main.py` 中）
   ```python
   @app.exception_handler(AppError)
   async def app_error_handler(request, exc):
       return JSONResponse(
           status_code=exc.status_code,
           content={"success": False, "detail": exc.message, "code": exc.code}
       )
   ```

3. **逐步替换各模块中的错误处理**
   - `auth.py`：将 `except Exception: return None` 改为具体异常或日志记录
   - `security.py`：将 `except Exception: print(...)` 改为 `logger.error(...)`
   - 统一返回格式

**验收标准**：
- [ ] 不存在 `except Exception: pass` 或 `except Exception: return None` 的静默吞错
- [ ] 所有错误使用 `logging` 模块记录
- [ ] API 错误响应格式统一

---

#### 任务 2.6：拆分 `security.py` 为独立子模块
- **对应问题**：P1-8
- **工作量**：2.5 小时
- **优先级**：★★★
- **前置依赖**：任务 2.4

**具体步骤**：

1. **创建 `backend/security/` 包**

2. **按职责拆分**：

   | 新文件 | 原 `security.py` 函数 | 行数 |
   |--------|---------------------|------|
   | `security/__init__.py` | 导出所有公开接口 | ~30行 |
   | `security/rate_limiter.py` | `check_rate_limit()`, `get_rate_limit_status()` | ~100行 |
   | `security/anti_crawler.py` | `detect_crawler()`, `add_crawler_block()` | ~80行 |
   | `security/login_tracker.py` | `record_login()`, `check_login_attempts()`, `record_login_attempt()`, `get_login_logs()` | ~120行 |
   | `security/session_manager.py` | `create_session()`, `validate_session()`, `revoke_session()`, `get_user_sessions()`, `revoke_all_user_sessions()` | ~150行 |
   | `security/password_policy.py` | `validate_password()`, `get_password_policy()` | ~80行 |
   | `security/audit.py` | `record_audit_log()`, `get_audit_logs()`, `record_data_history()`, `get_data_history()` | ~150行 |

3. **保持 `__init__.py` 中的导入兼容**
   ```python
   # security/__init__.py
   from .rate_limiter import check_rate_limit, get_rate_limit_status
   from .anti_crawler import detect_crawler, add_crawler_block
   # ... 保持现有导入接口不变
   ```

4. **将 `init_security()` 函数保留在 `__init__.py` 中，协调各子模块初始化**

**验收标准**：
- [ ] `from backend.security import ...` 的现有导入全部兼容
- [ ] 每个子模块职责单一、行数 < 200
- [ ] `security.py` 原文件删除

---

### ═══════════════════════════════════════════
### Phase 3：工程化提升（持续改进，2-4周）
### ═══════════════════════════════════════════

> **目标**：提升项目的专业度和长期可维护性  
> **风险**：中低（可逐步推进）  
> **验证方式**：单元测试 + CI 自动化

---

#### 任务 3.1：引入标准 JWT 库替换自定义实现
- **对应问题**：P1-9
- **工作量**：2.5 小时
- **优先级**：★★★

**具体步骤**：
1. 安装 `PyJWT` 或 `python-jose` 库
2. 重写 `auth.py` 中的 `_jwt_encode()`、`_jwt_decode()`、`create_access_token()`、`get_current_user()`
3. 添加启动检测：如 `SECRET_KEY` 为默认值且非开发模式，打印警告或拒绝启动
4. 确保 token 格式向后兼容（或提供迁移窗口）

**验收标准**：
- [ ] JWT 操作使用标准库
- [ ] 默认密钥在生产环境有明确警告
- [ ] 现有 token 认证流程不受影响

---

#### 任务 3.2：引入 `logging` 模块替代 `print`
- **对应问题**：P2-5
- **工作量**：1.5 小时
- **优先级**：★★★

**具体步骤**：
1. 创建 `backend/core/logging_config.py`，配置日志格式和级别
2. 全局搜索 `print(` 替换为 `logger.info/warning/error`
3. 配置日志输出到文件和控制台

**验收标准**：
- [ ] 无生产代码使用 `print()` 输出
- [ ] 日志格式统一，包含时间戳、级别、模块名
- [ ] 支持通过环境变量控制日志级别

---

#### 任务 3.3：整理根目录文件结构
- **对应问题**：P2-2
- **工作量**：1 小时
- **优先级**：★★

**具体步骤**：
1. **移动工具脚本**：
   - `check_database.py`, `check_duplicates.py`, `convert_code_doc.py`, `convert_to_docx.py`, `gen_arch_img.py`, `rebuild_manual.py` → `scripts/`
2. **移动测试文件**：
   - `test_backend_api.py`, `test_cache.py`, `test_cursor_token.py`, `test_review.py`, `minimal_test.py` → `tests/`
3. **整理文档文件**：
   - `CURSOR_TASK.md`, `MODEL_TASKS.md`, `PROJECT_STATUS.md`, `cursor_commands_*.md`, `cursor_quick_test.md` → `docs/` 或删除
4. **更新 `.gitignore`**：
   - 添加 `date.csv`、`*.db` 等数据文件

**验收标准**：
- [ ] 根目录仅保留核心配置文件（README, Dockerfile, docker-compose.yml, requirements.txt 等）
- [ ] 测试文件在 `tests/` 目录下
- [ ] 工具脚本在 `scripts/` 目录下

---

#### 任务 3.4：数据库优化
- **对应问题**：P2-1
- **工作量**：2 小时
- **优先级**：★★

**具体步骤**：
1. **添加复合索引**：为常见查询模式（组分+温度）创建复合索引
2. **优化 `_get_next_group_number`**：
   - 将 `SELECT group_id FROM pending_review`（全表扫描）
   - 改为 `SELECT MAX(CAST(SUBSTR(group_id, 2) AS INTEGER)) FROM pending_review`
3. **评估 `pending_review` 表设计**：考虑使用状态字段替代独立表

**验收标准**：
- [ ] 常见查询有复合索引支持
- [ ] 无全表扫描获取最大编号
- [ ] 查询性能提升可测量

---

#### 任务 3.5：引入 Alembic 数据库迁移管理
- **对应问题**：P2-3
- **工作量**：4 小时
- **优先级**：★★

**具体步骤**：
1. 安装 `alembic`
2. 初始化 Alembic 配置
3. 创建初始迁移脚本（基于当前表结构）
4. 将 `migrations/` 目录下的手动 SQL 迁移转为 Alembic 迁移
5. 在部署流程中集成 `alembic upgrade head`

**验收标准**：
- [ ] 数据库变更通过 Alembic 管理
- [ ] 支持版本回滚
- [ ] 部署脚本包含迁移步骤

---

#### 任务 3.6：添加单元测试框架和基础测试
- **对应问题**：P2-4
- **工作量**：8 小时
- **优先级**：★★

**具体步骤**：
1. 安装 `pytest`, `pytest-asyncio`, `httpx`（用于 FastAPI TestClient）
2. 创建 `tests/` 目录结构
3. 创建 `conftest.py`：测试数据库 fixtures、测试客户端
4. 为核心模块编写测试：
   - `tests/test_database.py`：CRUD 操作测试
   - `tests/test_auth.py`：认证流程测试
   - `tests/test_api_records.py`：记录 API 端点测试
   - `tests/test_data_validation.py`：数据校验测试
5. 目标：核心业务逻辑测试覆盖率 > 60%

**验收标准**：
- [ ] `pytest` 配置完成
- [ ] 核心模块有基础测试
- [ ] 测试可在 CI 中自动运行

---

#### 任务 3.7：增加 Service 层分离业务逻辑
- **对应问题**：P1-1（深度重构）
- **工作量**：8 小时
- **优先级**：★★
- **前置依赖**：任务 2.3

**具体步骤**：
1. 创建 `backend/services/` 目录
2. 从 router 中提取复杂业务逻辑：
   - `services/record_service.py`：记录管理业务逻辑
   - `services/chart_service.py`：图表数据计算逻辑
   - `services/import_service.py`：文件解析和导入逻辑
   - `services/query_service.py`：查询和筛选逻辑
3. Router 只负责：接收请求 → 调用 Service → 返回响应

**验收标准**：
- [ ] Router 层不包含复杂业务逻辑
- [ ] Service 层可独立测试
- [ ] 业务逻辑变更不需要修改路由代码

---

## 三、工作量总结

### 按阶段汇总

| 阶段 | 任务数 | 总工作量 | 建议周期 | 参与人数 |
|------|--------|---------|---------|---------|
| **Phase 1** - 安全与稳定性修复 | 4 | **5.5 小时** | 1-2 天 | 1人 |
| **Phase 2** - 架构重构 | 6 | **15.5 小时** | 1-2 周 | 1-2人 |
| **Phase 3** - 工程化提升 | 7 | **27 小时** | 2-4 周 | 1-2人 |
| **总计** | **17** | **~48 小时** | **4-8 周** | - |

### 按任务明细

| 编号 | 任务 | 工作量 | 阶段 |
|------|------|--------|------|
| 1.1 | 修复 SQL 注入风险 | 1.5h | Phase 1 |
| 1.2 | 修复数据库连接泄漏 | 2.5h | Phase 1 |
| 1.3 | 修复缓存装饰器 async 兼容性 | 1h | Phase 1 |
| 1.4 | 删除重复路由 | 0.5h | Phase 1 |
| 2.1 | 提取公共常量和工具函数 | 2h | Phase 2 |
| 2.2 | 移除模块导入时的数据库初始化副作用 | 1h | Phase 2 |
| 2.3 | 拆分 main.py 为多个 Router 模块 | 5h | Phase 2 |
| 2.4 | 统一配置管理 | 3h | Phase 2 |
| 2.5 | 建立统一错误处理机制 | 2h | Phase 2 |
| 2.6 | 拆分 security.py 为独立子模块 | 2.5h | Phase 2 |
| 3.1 | 引入标准 JWT 库 | 2.5h | Phase 3 |
| 3.2 | 引入 logging 替代 print | 1.5h | Phase 3 |
| 3.3 | 整理根目录文件结构 | 1h | Phase 3 |
| 3.4 | 数据库优化 | 2h | Phase 3 |
| 3.5 | 引入 Alembic 数据库迁移 | 4h | Phase 3 |
| 3.6 | 添加单元测试框架和基础测试 | 8h | Phase 3 |
| 3.7 | 增加 Service 层分离业务逻辑 | 8h | Phase 3 |

---

## 四、执行检查清单

### Phase 1 检查清单（安全与稳定性）

- [ ] **1.1** SQL 注入风险已修复
  - [ ] `data_review.py` 中所有 SQL 使用参数化查询
  - [ ] `main.py` 中动态 SQL 使用白名单验证
  - [ ] `database.py` 中动态查询已修复
- [ ] **1.2** 数据库连接泄漏已修复
  - [ ] `auth.py` 中 3 处已改为 context manager
  - [ ] `totp.py` 中 8 处已改为 context manager
  - [ ] `security.py` 中 12 处已改为 context manager
- [ ] **1.3** 缓存装饰器支持 async
  - [ ] `cached` 装饰器区分 sync/async 函数
  - [ ] 缓存路由返回正确数据
- [ ] **1.4** 重复路由已删除
  - [ ] `/api/chart/*` 系列已移除或重定向
  - [ ] 前端调用已更新
- [ ] **Phase 1 回归测试通过**

### Phase 2 检查清单（架构重构）

- [ ] **2.1** 公共常量和工具函数已提取
  - [ ] `constants.py` 创建完成
  - [ ] `_ensure_index` 统一到 `db.py`
  - [ ] 硬编码组分列表已替换
- [ ] **2.2** 模块导入副作用已移除
  - [ ] 三个模块末尾的自动初始化已删除
  - [ ] `startup_event()` 统一管理初始化
- [ ] **2.3** `main.py` 路由拆分完成
  - [ ] `routers/` 目录创建完成
  - [ ] `main.py` 行数 < 100
  - [ ] 所有 API 端点功能正常
- [ ] **2.4** 配置管理已统一
  - [ ] `Settings` 类定义完成
  - [ ] 各模块使用统一配置
  - [ ] `.env.example` 已创建
- [ ] **2.5** 统一错误处理已建立
  - [ ] 自定义异常体系定义完成
  - [ ] 全局异常处理器注册
  - [ ] 静默吞错已消除
- [ ] **2.6** `security.py` 拆分完成
  - [ ] 各子模块职责单一
  - [ ] 导入兼容性保持
- [ ] **Phase 2 回归测试通过**

### Phase 3 检查清单（工程化提升）

- [ ] **3.1** 标准 JWT 库已集成
- [ ] **3.2** logging 模块全面替代 print
- [ ] **3.3** 根目录文件已整理
- [ ] **3.4** 数据库查询已优化
- [ ] **3.5** Alembic 迁移管理已集成
- [ ] **3.6** 单元测试框架和基础测试已完成
- [ ] **3.7** Service 层已建立

---

## 五、风险评估与缓解措施

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| 路由拆分导致功能缺失 | 中 | 高 | 拆分前后对比 OpenAPI 文档，确保端点一致 |
| 配置迁移遗漏 | 中 | 中 | 创建配置映射表，逐项核对 |
| 数据库初始化顺序错误 | 低 | 高 | 编写启动检查脚本，验证表结构 |
| 前端调用路由变更 | 中 | 高 | 拆分路由时保持原有路径不变 |
| JWT 库迁移导致已有 token 失效 | 中 | 中 | 提供向后兼容的 token 验证逻辑 |
| 测试环境与生产环境差异 | 低 | 中 | 使用 Docker 保持环境一致 |

---

## 六、依赖关系图

```
Phase 1（可并行执行）
├── 1.1 修复 SQL 注入 ─────────────────────┐
├── 1.2 修复连接泄漏 ─────────────────────┤
├── 1.3 修复缓存装饰器 ───────────────────┤
└── 1.4 删除重复路由 ─────────────────────┤
                                           ▼
Phase 2                                    
├── 2.1 提取常量和工具 ──────────┐
├── 2.2 移除导入副作用 ──────────┤
│                                ├──→ 2.3 拆分 main.py ──→ 2.5 错误处理
├── 2.4 统一配置管理 ────────────┘                         2.6 拆分 security.py
│                                                          
Phase 3（可按需执行）
├── 3.1 标准 JWT 库（依赖 2.4）
├── 3.2 logging 替代 print
├── 3.3 整理根目录
├── 3.4 数据库优化
├── 3.5 Alembic 迁移（依赖 3.4）
├── 3.6 单元测试（依赖 2.3）
└── 3.7 Service 层（依赖 2.3）
```

---

> **文档维护说明**：每完成一个任务，请在对应的检查清单项前打 ✅，并更新完成日期。  
> **下一步行动**：立即开始 Phase 1 的四个任务（可并行执行，无依赖关系）。
