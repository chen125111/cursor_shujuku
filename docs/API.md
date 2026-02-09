# API 文档（静态版）

本项目后端使用 FastAPI 实现，默认提供 OpenAPI 自动文档（推荐优先使用）：

- Swagger UI：`/docs`
- ReDoc：`/redoc`
- OpenAPI JSON：`/openapi.json`

本文档用于补充“调用视角”的说明：鉴权方式、常见错误码、典型调用流程与示例请求。

## 1. 基础信息

- **默认服务地址**：`http://127.0.0.1:8000`
- **API 基础路径**：`/api`
- **数据格式**：请求/响应以 JSON 为主；文件上传使用 `multipart/form-data`

## 2. 认证与鉴权（JWT）

### 2.1 登录获取 Token

- **方法**：`POST`
- **路径**：`/api/auth/login`

请求体（JSON）：

```json
{
  "username": "admin",
  "password": "YOUR_PASSWORD",
  "totp_code": "123456"
}
```

说明：

- 若用户启用了两步验证（TOTP），可能会返回 `require_totp=true`，此时需要再次携带 `totp_code` 登录。

### 2.2 在请求头携带 Token

对需要认证的接口，请在请求头添加：

```http
Authorization: Bearer <token>
```

## 3. 通用响应与错误码

### 3.1 常见响应结构

部分接口使用统一结构：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```

也有部分接口直接返回资源对象或列表（以 `/docs` 为准）。

### 3.2 HTTP 状态码

- `200`：成功
- `400`：参数错误 / 校验失败
- `401`：未认证 / Token 无效或过期
- `403`：权限不足
- `404`：资源不存在
- `429`：触发限流
- `500`：服务端错误

### 3.3 限流与防爬

对 `"/api/"` 下的大部分接口，系统会根据客户端 IP 进行限流；触发限流时返回 `429`。部分明显异常的请求特征可能被判定为爬虫并返回 `403`。

## 4. 核心接口（按业务分组）

以下为常用接口摘要；完整字段、示例与参数约束请以 `/docs` 为准。

### 4.1 Records：数据记录（部分需认证）

- `GET /api/records`：分页获取记录（支持温度/压力范围筛选）
- `GET /api/records/{id}`：获取单条记录
- `POST /api/records`：创建记录（需认证）
- `PUT /api/records/{id}`：更新记录（需认证）
- `DELETE /api/records/{id}`：删除记录（需认证）

### 4.2 Query：相平衡查询（公开）

- `GET /api/query`：按组分查询（支持误差容忍与严格模式）
- `POST /api/query/hydrate`：给定组分 + 温度，返回最匹配相平衡压力（含匹配度评分）
- `POST /api/query/by-components`：按“组分组合 + 温度”查询
- `POST /api/query/range`：按“组分范围 + 温度”查询
- `POST /api/query/match-count`：按组分范围估算匹配数量（用于 UI 引导）
- `POST /api/components/available`：在已选组分基础上，返回可继续添加的组分
- `POST /api/components/ranges`：返回选定组分在库中的实际范围（以及温度范围）

### 4.3 Import/Export：导入导出（导入/导出需认证）

- `GET /api/template/csv`：下载 CSV 模板
- `GET /api/template/excel`：下载 Excel 模板
- `POST /api/import/preview`：导入前预校验（不入库，需认证）
- `POST /api/import`：批量导入（需认证）
- `GET /api/export/csv`：导出 CSV（需认证）
- `GET /api/export/excel`：导出 Excel（需认证）

### 4.4 Review：重复数据审核（管理员）

- `GET /api/review/duplicates`：扫描重复数据
- `POST /api/review/move-duplicates`：迁移至待审核区
- `GET /api/review/pending`：获取待审核分组（分页/筛选）
- `PUT /api/review/pressure/{pending_id}`：修正待审核压力
- `POST /api/review/approve/{group_id}`：审核通过
- `POST /api/review/reject/{group_id}`：拒绝整组
- `POST /api/review/restore/{group_id}`：恢复整组到待审核

### 4.5 Backup：备份（管理员；SQLite 支持更完整）

- `GET /api/backup/status`：备份状态
- `GET /api/backup/list`：备份列表
- `POST /api/backup/create`：创建备份
- `POST /api/backup/restore/{filename}`：恢复备份
- `GET /api/backup/download/{filename}`：下载备份
- `DELETE /api/backup/{filename}`：删除备份

### 4.6 Auth/TOTP/Sessions：用户、两步验证、会话（部分管理员）

- `POST /api/auth/login`：登录
- `GET /api/auth/me`：当前用户
- `POST /api/auth/logout`：退出
- `POST /api/auth/change-password`：改密
- `GET /api/auth/password-policy`：密码策略
- `POST /api/auth/users`：创建用户（管理员）
- `GET /api/auth/users`：用户列表（管理员）
- `POST /api/auth/users/{username}/reset-password`：重置密码（管理员）

TOTP：

- `POST /api/auth/totp/setup`、`/enable`、`/disable`、`/status`、`/backup-codes`

会话：

- `GET /api/auth/sessions`
- `POST /api/auth/sessions/revoke-all`

### 4.7 Security：日志与限流状态

- `GET /api/security/login-logs`：登录日志（管理员可看全部，普通用户仅看自己）
- `GET /api/security/audit-logs`：审计日志（管理员）
- `GET /api/security/rate-limit`：当前 IP 的限流状态（公开）

## 5. 典型调用示例

### 5.1 登录并创建记录（curl）

1) 登录：

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}'
```

2) 假设拿到 token 后创建记录：

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/records" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"temperature":275,"pressure":2.5,"x_ch4":0.9,"x_c2h6":0.1}'
```

### 5.2 水合物相平衡查询（示例）

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/query/hydrate" \
  -H "Content-Type: application/json" \
  -d '{"components":{"x_ch4":0.9,"x_c2h6":0.1},"temperature":275,"tolerance":0.02}'
```

## 6. 进一步阅读

- 简明用户指南：`docs/USER_GUIDE.md`
- 完整用户手册（含截图）：`docs/用户手册.md`

