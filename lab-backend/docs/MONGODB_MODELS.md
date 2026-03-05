# MongoDB 模型设计（备选方案）

本项目运行实现采用 **PostgreSQL + Prisma**（见 `prisma/schema.prisma`）。本文件提供 **MongoDB（Mongoose）等价模型设计**，用于你需要切换到 MongoDB 时参考。

> 说明：这里给出的是“模型/集合结构 + 关键索引”的设计稿（含示例 Schema 代码片段），不作为当前可执行代码的一部分，以避免在未引入 `mongoose` 依赖时影响编译。

## 集合：users

字段：
- `_id`: ObjectId
- `email`: string（唯一）
- `passwordHash`: string
- `name`: string?
- `role`: `"ADMIN" | "USER"`
- `createdAt`, `updatedAt`: Date

索引：
- `{ email: 1 } unique`

示例 Schema（伪代码）：

```ts
const UserSchema = new Schema(
  { email: { type: String, unique: true, index: true }, passwordHash: String, name: String, role: String },
  { timestamps: true }
);
```

## 集合：devices

字段：
- `code`: string（唯一）
- `name`: string
- `model`: string?
- `location`: string?
- `status`: `"AVAILABLE" | "MAINTENANCE" | "DISABLED"`
- `description`: string?
- `createdAt`, `updatedAt`

索引：
- `{ code: 1 } unique`
- `{ status: 1 }`

## 集合：reservations

字段：
- `deviceId`: ObjectId（ref devices）
- `userId`: ObjectId（ref users）
- `startTime`: Date
- `endTime`: Date
- `purpose`: string?
- `status`: `"PENDING" | "APPROVED" | "REJECTED" | "CANCELLED"`
- `createdAt`, `updatedAt`

索引建议：
- `{ deviceId: 1, startTime: 1, endTime: 1 }`
- `{ userId: 1, startTime: 1, endTime: 1 }`
- 可选：对 `status` 建索引 `{ status: 1 }`

并发约束建议：
- “已批准（APPROVED）” 的时间段冲突检查，用查询条件 `startTime < newEnd && endTime > newStart`
- 可选用事务（MongoDB session）或用“审批时二次校验”保证一致性

## 集合：inventory_items

字段：
- `sku`: string（唯一）
- `name`: string
- `unit`: string
- `quantity`: number
- `lowStock`: number
- `location`: string?
- `description`: string?
- `createdAt`, `updatedAt`

索引：
- `{ sku: 1 } unique`
- `{ quantity: 1 }`（可选，用于低库存筛选/排序）

## 集合：inventory_ops

字段：
- `itemId`: ObjectId（ref inventory_items）
- `userId`: ObjectId（ref users）
- `delta`: number（正=入库/增加，负=出库/消耗）
- `reason`: string?
- `createdAt`

索引：
- `{ itemId: 1, createdAt: -1 }`

## 集合：file_assets

字段：
- `ownerId`: ObjectId（ref users）
- `original`: string
- `mimeType`: string
- `size`: number
- `path`: string（本地存储路径或对象存储 key）
- `createdAt`

索引：
- `{ ownerId: 1, createdAt: -1 }`

## 集合：refresh_tokens

字段：
- `userId`: ObjectId（ref users）
- `tokenHash`: string（唯一，sha256）
- `expiresAt`: Date
- `revokedAt`: Date?
- `createdAt`

索引：
- `{ tokenHash: 1 } unique`
- `{ userId: 1, expiresAt: 1 }`

