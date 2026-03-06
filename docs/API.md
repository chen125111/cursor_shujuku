# API 文档（概览）

本系统基于 FastAPI，启动后可访问交互式 API 文档：

- Swagger UI：`/docs`
- OpenAPI JSON：`/openapi.json`

本文档提供**接口概览 + 常用示例**，详细参数以 `/docs` 为准。

---

## 约定

### 认证

需要登录的接口在请求头携带：

```http
Authorization: Bearer <token>
```

### 通用响应

部分接口返回统一结构：

```json
{ "success": true, "message": "xxx", "data": {} }
```

校验失败/未认证等也可能返回 FastAPI 默认结构：

```json
{ "detail": "错误信息" }
```

---

## 核心接口分组

### Records（数据记录）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/records` | 分页列表（可筛选温度/压力区间） | 否 |
| GET | `/api/records/{id}` | 单条详情 | 否 |
| POST | `/api/records` | 创建记录 | 是 |
| PUT | `/api/records/{id}` | 更新记录（部分字段） | 是 |
| DELETE | `/api/records/{id}` | 删除记录 | 是 |
| POST | `/api/records/batch-delete` | 批量删除 | 是（admin） |
| POST | `/api/records/batch-update` | 批量更新 | 是（admin） |

### Statistics / Charts（统计与图表）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/statistics` | 统计信息（缓存 60s） |
| GET | `/api/charts/temperature` | 温度分布（缓存 5min） |
| GET | `/api/charts/pressure` | 压力分布（缓存 5min） |
| GET | `/api/charts/scatter` | 温度-压力散点（缓存 5min） |
| GET | `/api/chart/heatmap` | 温度-压力热力图（按分箱） |

### Public Query（相平衡查询）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/query` | 按组分摩尔分数反查记录（支持 strict/tolerance） |
| POST | `/api/query/by-components` | 组分组合 + 温度 → 压力（温度允许 ±5K） |
| POST | `/api/query/batch` | 批量（组分组合 + 多温度）查询 |
| POST | `/api/query/range` | 组分范围 + 温度 → 压力 |
| POST | `/api/query/match-count` | 组分范围匹配条数估算（模糊档位） |
| POST | `/api/query/hydrate` | 水合物相平衡智能匹配（返回 match_score） |
| POST | `/api/components/available` | 选定组分下还可追加哪些组分 |
| POST | `/api/components/ranges` | 选定组分在库中的 min/max + 温度范围 |

### Auth / Sessions / TOTP（认证与会话）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录（可选 TOTP） |
| POST | `/api/auth/logout` | 退出登录 |
| GET | `/api/auth/me` | 当前用户 |
| POST | `/api/auth/change-password` | 修改密码（含策略校验） |
| GET | `/api/auth/users` | 用户列表（admin） |
| POST | `/api/auth/users` | 创建用户（admin） |
| POST | `/api/auth/users/{username}/reset-password` | 重置密码（admin） |
| GET | `/api/auth/sessions` | 当前用户会话列表 |
| POST | `/api/auth/sessions/revoke-all` | 撤销除当前外的所有会话 |

TOTP：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/totp/setup` | 生成密钥与 URI |
| POST | `/api/auth/totp/enable` | 启用 |
| POST | `/api/auth/totp/disable` | 禁用 |
| GET | `/api/auth/totp/status` | 状态 |
| POST | `/api/auth/totp/backup-codes` | 备用码 |

### Import / Export / Template（导入导出）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/import` | 导入 CSV/Excel（写入） | 是 |
| POST | `/api/import/preview` | 导入预览（不写入） | 是 |
| GET | `/api/export/csv` | 导出 CSV | 是 |
| GET | `/api/export/excel` | 导出 Excel | 是 |
| GET | `/api/template/csv` | CSV 模板 | 否 |
| GET | `/api/template/excel` | Excel 模板 | 否 |

### Review（重复数据审核）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/review/duplicates` | 查重 | 是（admin） |
| POST | `/api/review/move-duplicates` | 移至待审核 | 是（admin） |
| GET | `/api/review/pending` | 待审核分页 | 是（admin） |
| POST | `/api/review/approve/{group_id}` | 通过 | 是（admin） |
| POST | `/api/review/reject/{group_id}` | 拒绝 | 是（admin） |
| POST | `/api/review/restore/{group_id}` | 恢复 | 是（admin） |

### Backup（备份，仅 SQLite）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/backup/status` | 备份状态 | 是 |
| GET | `/api/backup/list` | 备份列表 | 是 |
| POST | `/api/backup/create` | 创建备份 | 是（admin） |
| POST | `/api/backup/restore/{filename}` | 恢复备份 | 是（admin） |
| GET | `/api/backup/download/{filename}` | 下载备份 | 是 |
| DELETE | `/api/backup/{filename}` | 删除备份 | 是（admin） |

---

## 常用示例

### 登录

```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "User-Agent: cli" \
  -d '{"username":"admin","password":"AdminPass123!"}'
```

### 创建记录

```bash
curl -X POST "http://127.0.0.1:8000/api/records" \
  -H "Content-Type: application/json" \
  -H "User-Agent: cli" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "temperature": 300,
    "pressure": 10,
    "x_ch4": 0.8,
    "x_c2h6": 0.1,
    "x_c3h8": 0.05,
    "x_co2": 0.03,
    "x_n2": 0.01,
    "x_h2s": 0.005,
    "x_ic4h10": 0.005
  }'
```

### 水合物相平衡查询

```bash
curl -X POST "http://127.0.0.1:8000/api/query/hydrate" \
  -H "Content-Type: application/json" \
  -H "User-Agent: cli" \
  -d '{
    "components": {"x_ch4": 0.9, "x_c2h6": 0.1},
    "temperature": 275,
    "tolerance": 0.02
  }'
```

