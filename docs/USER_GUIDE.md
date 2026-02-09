# 简明用户指南（User Guide）

如果你是第一次使用本系统，建议先按本文档跑通“登录 → 查询 → 导入/导出 → 备份”的基本流程；需要更详细的截图说明与全量接口列表，请阅读 `docs/用户手册.md`。

## 1. 访问入口

服务启动后，默认地址如下：

- **前端首页**：`http://127.0.0.1:8000/`
- **管理后台**：`http://127.0.0.1:8000/admin`
- **API 文档**：`http://127.0.0.1:8000/docs`

## 2. 最常见操作流程

### 2.1 登录（获取操作权限）

系统的“写入/管理”接口需要 JWT 认证。你可以：

- 在管理后台登录后，由前端自动携带 Token 调用接口
- 或直接调用 API 登录接口，拿到 Token 后自行调用

登录接口：

- `POST /api/auth/login`

示例请求（curl）：

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}'
```

成功后响应中会包含 `access_token`，后续请求在头部带上：

```http
Authorization: Bearer <token>
```

> 若账号启用了两步验证（TOTP），需要额外传入 `totp_code`。

### 2.2 示例查询：给定组分与温度，查询相平衡压力

推荐使用接口：

- `POST /api/query/hydrate`

示例：

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/query/hydrate" \
  -H "Content-Type: application/json" \
  -d '{
    "components": {"x_ch4": 0.90, "x_c2h6": 0.10},
    "temperature": 275,
    "tolerance": 0.02
  }'
```

返回字段通常包含：

- `pressure`：匹配到的相平衡压力（MPa）
- `temperature`：匹配温度（K）
- `match_score`：匹配度评分（0-100）

### 2.3 示例查询：先选“可用组分组合”，再查范围与匹配

当你不确定数据库里有哪些组合时，可按以下顺序调用：

1) 查询还能添加哪些组分：

- `POST /api/components/available`

2) 获取各组分在数据库中的实际范围（以及可用温度范围）：

- `POST /api/components/ranges`

3) 再进行查询：

- `POST /api/query/by-components` 或 `POST /api/query/range`

## 3. 数据导入/导出（批量）

### 3.1 下载导入模板

- `GET /api/template/csv`
- `GET /api/template/excel`

建议从模板开始填数据，以减少字段名不匹配导致的校验失败。

### 3.2 导入前预校验（推荐先做）

- `POST /api/import/preview`（需要认证）

它不会写入数据库，会返回：

- `errors`：阻止导入的错误（格式/缺失字段/超范围等）
- `warnings`：不阻止导入但需要注意的软提示（如压力偏高）

### 3.3 正式导入

- `POST /api/import`（需要认证）

### 3.4 导出数据

- `GET /api/export/csv`（需要认证）
- `GET /api/export/excel`（需要认证）

## 4. 数据审核（管理员）

当存在“同组分同温度下多个压力值”时，可以使用审核模块提升数据一致性：

1) 扫描重复数据：`GET /api/review/duplicates`
2) 迁移到待审核区：`POST /api/review/move-duplicates`
3) 在待审核列表中筛选并处理：
   - 通过：`POST /api/review/approve/{group_id}`
   - 拒绝：`POST /api/review/reject/{group_id}`
   - 恢复：`POST /api/review/restore/{group_id}`

> 若需要人工修正某条待审核记录的压力值，可调用：`PUT /api/review/pressure/{pending_id}?pressure=...`

## 5. 备份与恢复（管理员）

- 查看备份状态：`GET /api/backup/status`
- 创建备份：`POST /api/backup/create`
- 下载备份：`GET /api/backup/download/{filename}`
- 恢复备份：`POST /api/backup/restore/{filename}`

> 浏览器直接下载时无法设置 `Authorization` 请求头，管理后台会使用 `?token=<access_token>` 方式下载备份文件。

> SQLite 环境支持更完整的文件级备份/恢复；MySQL 场景通常由托管备份策略负责。

## 6. 去哪里看更详细的文档？

- **完整用户手册（含截图）**：`docs/用户手册.md`
- **静态 API 文档**：`docs/API.md`
- **开发指南**：`docs/DEVELOPMENT.md`

