# 实验室管理系统 - 架构设计文档

## 1. 系统概述

### 1.1 项目简介

实验室管理系统（Laboratory Management System, LMS）是一套现代化的 Web 应用，旨在为高校和科研机构提供全面的实验室资源管理解决方案。系统涵盖用户管理、设备管理、预约系统、库存管理和通知系统五大核心模块。

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| **高可用** | 99.9% SLA，支持服务自动恢复 |
| **可扩展** | 模块化架构，支持水平扩展 |
| **安全性** | JWT 认证 + RBAC 权限 + 数据加密 |
| **响应快** | 核心接口 < 200ms，支持 Redis 缓存 |
| **易维护** | TypeScript 全栈类型安全，完善的日志和监控 |

### 1.3 技术选型

| 层级 | 技术栈 | 说明 |
|------|--------|------|
| **前端框架** | React 18 + TypeScript | 类型安全的组件化开发 |
| **UI 组件库** | Ant Design 5 | 企业级 UI 组件，内置中文支持 |
| **构建工具** | Vite 5 | 极速开发服务器与构建 |
| **状态管理** | Zustand | 轻量级状态管理，无模板代码 |
| **路由** | React Router v6 | 声明式路由配置 |
| **后端框架** | Node.js + Express | 成熟的 REST API 框架 |
| **主数据库** | MongoDB 7 | 灵活的文档数据库 |
| **备选数据库** | PostgreSQL 16 | 强一致性关系型数据库 |
| **缓存** | Redis 7 | 高性能 KV 缓存 |
| **实时通信** | Socket.IO | WebSocket 封装，支持实时推送 |
| **容器化** | Docker + Docker Compose | 标准化部署 |
| **Web 服务器** | Nginx | 反向代理 + 静态资源服务 |
| **CI/CD** | GitHub Actions | 自动化测试、构建和部署 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌──────────────────────────────────────────────────────────┐
│                        客户端层                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  PC 浏览器   │  │ 移动端浏览器 │  │  平板设备    │      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │
└─────────┼────────────────┼────────────────┼──────────────┘
          │                │                │
          ▼                ▼                ▼
┌──────────────────────────────────────────────────────────┐
│                     Nginx 网关层                          │
│  ┌───────────────────────────────────────────────────┐   │
│  │  • 反向代理          • SSL 终止                    │   │
│  │  • Gzip 压缩         • 静态资源缓存                │   │
│  │  • 负载均衡          • WebSocket 代理              │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────┬───────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼                         ▼
┌─────────────────┐     ┌─────────────────────────────────┐
│    前端应用层    │     │          后端 API 层              │
│ ┌─────────────┐ │     │ ┌─────────────────────────────┐ │
│ │ React SPA   │ │     │ │   Express.js Application    │ │
│ │ + TypeScript│ │     │ │                             │ │
│ │ + Ant Design│ │     │ │ ┌─────────┐ ┌───────────┐  │ │
│ │ + Vite      │ │     │ │ │ Router  │ │ Middleware │  │ │
│ └─────────────┘ │     │ │ └────┬────┘ └─────┬─────┘  │ │
└─────────────────┘     │ │      ▼             ▼        │ │
                        │ │ ┌──────────────────────┐    │ │
                        │ │ │    Controllers       │    │ │
                        │ │ └──────────┬───────────┘    │ │
                        │ │            ▼                │ │
                        │ │ ┌──────────────────────┐    │ │
                        │ │ │     Services         │    │ │
                        │ │ └──────────┬───────────┘    │ │
                        │ │            ▼                │ │
                        │ │ ┌──────────────────────┐    │ │
                        │ │ │ Models (Mongoose/PG) │    │ │
                        │ │ └──────────────────────┘    │ │
                        │ └─────────────────────────────┘ │
                        └──────────────┬──────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │   MongoDB    │  │    Redis     │  │  PostgreSQL  │
            │  (主数据库)   │  │   (缓存)     │  │   (备选)     │
            └──────────────┘  └──────────────┘  └──────────────┘
```

### 2.2 前端架构

```
前端 (React + TypeScript + Ant Design + Vite)
├── api/                   # API 服务层 - Axios 封装
│   ├── request.ts         #   统一请求拦截器（Token 自动注入、刷新、错误处理）
│   ├── auth.ts            #   认证 API
│   ├── equipment.ts       #   设备 API
│   ├── reservation.ts     #   预约 API
│   ├── inventory.ts       #   库存 API
│   ├── notification.ts    #   通知 API
│   └── user.ts            #   用户 API
├── components/            # 通用组件
│   ├── common/            #   ProtectedRoute 等
│   └── layout/            #   MainLayout 侧边栏布局
├── hooks/                 # 自定义 Hooks
├── pages/                 # 页面组件（路由级）
│   ├── Login/             #   登录/注册页
│   ├── Dashboard/         #   仪表盘
│   ├── Users/             #   用户管理
│   ├── Equipment/         #   设备管理
│   ├── Reservations/      #   预约系统
│   ├── Inventory/         #   库存管理
│   └── Notifications/     #   通知中心
├── store/                 # Zustand 状态管理
│   ├── authStore.ts       #   认证状态
│   └── notificationStore.ts #  通知状态
├── types/                 # TypeScript 类型定义
├── utils/                 # 工具函数
├── styles/                # 全局样式
├── App.tsx                # 应用入口 + 路由配置
└── main.tsx               # 渲染入口
```

### 2.3 后端架构

```
后端 (Node.js + Express + TypeScript)
├── config/                # 配置层
│   ├── index.ts           #   环境变量配置
│   ├── database.ts        #   MongoDB + PostgreSQL 连接
│   └── redis.ts           #   Redis 连接 + 缓存工具
├── controllers/           # 控制器层 - 处理 HTTP 请求/响应
│   ├── auth.controller.ts
│   ├── user.controller.ts
│   ├── equipment.controller.ts
│   ├── reservation.controller.ts
│   ├── inventory.controller.ts
│   └── notification.controller.ts
├── middleware/            # 中间件层
│   ├── auth.ts            #   JWT 认证 + RBAC 鉴权
│   ├── errorHandler.ts    #   全局错误处理
│   └── validate.ts        #   Zod 请求校验
├── models/                # 数据模型层 (Mongoose ODM)
│   ├── User.ts
│   ├── Equipment.ts
│   ├── Reservation.ts
│   ├── Inventory.ts
│   └── Notification.ts
├── routes/                # 路由层
│   ├── auth.routes.ts
│   ├── user.routes.ts
│   ├── equipment.routes.ts
│   ├── reservation.routes.ts
│   ├── inventory.routes.ts
│   └── notification.routes.ts
├── services/              # 业务逻辑层
│   ├── auth.service.ts    #   认证业务（注册/登录/Token 刷新）
│   └── notification.service.ts  #  通知服务 + 模板
├── validators/            # 数据校验层 (Zod Schemas)
│   ├── auth.validator.ts
│   ├── equipment.validator.ts
│   └── reservation.validator.ts
├── types/                 # TypeScript 类型 + 枚举
├── utils/                 # 工具层
│   ├── logger.ts          #   Winston 日志
│   └── response.ts        #   统一响应格式
└── app.ts                 # 应用入口
```

---

## 3. 功能模块设计

### 3.1 用户管理模块

**数据模型：**
- 字段：username, email, password(bcrypt), role, displayName, department, phone, avatar, isActive
- 角色体系（RBAC）：

| 角色 | 权限范围 |
|------|----------|
| `admin` | 全部权限：用户管理、系统配置、数据导出 |
| `manager` | 设备管理、预约审批、库存管理、维护记录 |
| `researcher` | 设备预约、库存领用、个人信息维护 |
| `student` | 设备预约、查看设备/库存信息 |

**核心功能：**
- 用户注册与登录（JWT + Refresh Token）
- 基于角色的访问控制（中间件级拦截）
- 用户状态管理（启用/禁用）
- 个人信息维护

### 3.2 设备管理模块

**数据模型：**
- 字段：name, code(唯一), category, brand, model, specifications, location, status, purchaseDate, purchasePrice, warrantyExpiry, manager, images, maintenanceRecords

**核心功能：**
- 设备 CRUD（管理员/主任权限）
- 多维度搜索和筛选（名称、编号、分类、状态、部门）
- 设备状态管理：可用 → 使用中 → 维护中 → 已报废
- 维护记录管理（维护类型、费用、技术员）
- 设备统计（按状态/分类分组）
- Redis 缓存层（5分钟 TTL）

### 3.3 预约系统

**数据模型：**
- 字段：equipment, user, startTime, endTime, purpose, status, approvedBy, rejectReason

**核心功能：**
- 预约申请（自动冲突检测）
- 审批流程：pending → approved/rejected
- 日历视图查询（按设备/时间范围）
- 自动通知（审批通过/拒绝推送）
- 我的预约管理（查看/取消）

**冲突检测逻辑：**
```
检查时间段 [startTime, endTime] 是否与已有预约重叠：
WHERE equipment = :equipmentId
  AND status IN ('pending', 'approved')
  AND startTime < :newEndTime
  AND endTime > :newStartTime
```

### 3.4 库存管理模块

**数据模型：**
- 字段：name, code, category, specifications, unit, quantity, minQuantity, location, supplier, unitPrice, expiryDate, usageRecords

**核心功能：**
- 物品 CRUD
- 出入库记录（记录用户、数量、类型、时间）
- 库存预警（quantity ≤ minQuantity 自动推送通知）
- 分类统计（试剂、耗材、玻璃器具、仪器、安全用品）
- 总价值计算（quantity × unitPrice）

### 3.5 通知系统

**数据模型：**
- 字段：recipient, sender, type, title, content, isRead, relatedId, relatedModel

**通知类型：**
| 类型 | 触发条件 |
|------|----------|
| `reservation_approved` | 预约审批通过 |
| `reservation_rejected` | 预约审批拒绝 |
| `equipment_available` | 设备恢复可用 |
| `equipment_maintenance` | 设备进入维护 |
| `inventory_low` | 库存低于最低线 |
| `system_announcement` | 系统公告 |

**推送方式：**
- HTTP 轮询（30秒间隔获取未读数）
- Socket.IO 实时推送（WebSocket）
- 未来扩展：邮件通知（Nodemailer）

---

## 4. API 设计

### 4.1 RESTful 接口规范

- 基础路径：`/api/v1`
- 认证方式：`Authorization: Bearer <token>`
- 响应格式：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {},
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5
  }
}
```

### 4.2 接口清单

| 模块 | 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|------|
| **认证** | POST | `/auth/register` | 注册 | 公开 |
| | POST | `/auth/login` | 登录 | 公开 |
| | POST | `/auth/refresh-token` | 刷新令牌 | 公开 |
| | POST | `/auth/logout` | 退出 | 认证 |
| | GET | `/auth/profile` | 个人信息 | 认证 |
| | PUT | `/auth/change-password` | 修改密码 | 认证 |
| **用户** | GET | `/users` | 用户列表 | 认证 |
| | GET | `/users/:id` | 用户详情 | 认证 |
| | PUT | `/users/:id` | 更新信息 | 认证 |
| | PUT | `/users/:id/role` | 更改角色 | 管理员 |
| | PUT | `/users/:id/toggle-active` | 启用/禁用 | 管理员 |
| **设备** | GET | `/equipment` | 设备列表 | 认证 |
| | GET | `/equipment/:id` | 设备详情 | 认证 |
| | POST | `/equipment` | 创建设备 | 管理员/主任 |
| | PUT | `/equipment/:id` | 更新设备 | 管理员/主任 |
| | DELETE | `/equipment/:id` | 删除设备 | 管理员 |
| | POST | `/equipment/:id/maintenance` | 维护记录 | 管理员/主任 |
| | GET | `/equipment/statistics` | 设备统计 | 认证 |
| **预约** | GET | `/reservations` | 预约列表 | 认证 |
| | GET | `/reservations/my` | 我的预约 | 认证 |
| | GET | `/reservations/calendar` | 日历数据 | 认证 |
| | POST | `/reservations` | 创建预约 | 认证 |
| | PUT | `/reservations/:id/status` | 审批 | 管理员/主任 |
| | PUT | `/reservations/:id/cancel` | 取消预约 | 认证 |
| **库存** | GET | `/inventory` | 库存列表 | 认证 |
| | GET | `/inventory/:id` | 物品详情 | 认证 |
| | POST | `/inventory` | 创建物品 | 管理员/主任 |
| | PUT | `/inventory/:id` | 更新物品 | 管理员/主任 |
| | DELETE | `/inventory/:id` | 删除物品 | 管理员 |
| | POST | `/inventory/:id/usage` | 出入库 | 认证 |
| | GET | `/inventory/statistics` | 库存统计 | 认证 |
| **通知** | GET | `/notifications` | 通知列表 | 认证 |
| | GET | `/notifications/unread-count` | 未读数 | 认证 |
| | PUT | `/notifications/:id/read` | 标记已读 | 认证 |
| | PUT | `/notifications/read-all` | 全部已读 | 认证 |

---

## 5. 数据库设计

### 5.1 MongoDB Collections

```
┌─────────────────┐     ┌─────────────────┐
│     users       │     │   equipment     │
├─────────────────┤     ├─────────────────┤
│ _id             │◄────│ manager (ref)   │
│ username        │     │ _id             │
│ email           │     │ name            │
│ password (hash) │     │ code (unique)   │
│ role            │     │ category        │
│ displayName     │     │ status          │
│ department      │     │ location        │
│ isActive        │     │ maintenanceRecs │
│ lastLoginAt     │     │ timestamps      │
│ timestamps      │     └────────┬────────┘
└────────┬────────┘              │
         │                       │
         │     ┌─────────────────┘
         │     │
         ▼     ▼
┌─────────────────┐     ┌─────────────────┐
│  reservations   │     │   inventory     │
├─────────────────┤     ├─────────────────┤
│ _id             │     │ _id             │
│ equipment (ref) │     │ name            │
│ user (ref)      │     │ code (unique)   │
│ startTime       │     │ category        │
│ endTime         │     │ quantity        │
│ purpose         │     │ minQuantity     │
│ status          │     │ manager (ref)   │
│ approvedBy(ref) │     │ usageRecords[]  │
│ timestamps      │     │ timestamps      │
└─────────────────┘     └─────────────────┘
         │
         │
         ▼
┌─────────────────┐
│  notifications  │
├─────────────────┤
│ _id             │
│ recipient (ref) │
│ sender (ref)    │
│ type            │
│ title           │
│ content         │
│ isRead          │
│ relatedId       │
│ relatedModel    │
│ timestamps      │
└─────────────────┘
```

### 5.2 索引策略

| Collection | 索引 | 类型 | 用途 |
|------------|------|------|------|
| users | email | unique | 登录查询 |
| users | department, role | compound | 筛选查询 |
| equipment | code | unique | 编号查询 |
| equipment | status, category | compound | 列表筛选 |
| equipment | name, description | text | 全文搜索 |
| reservations | equipment, startTime, endTime | compound | 冲突检测 |
| reservations | user, status | compound | 我的预约 |
| inventory | code | unique | 编号查询 |
| inventory | name, description | text | 全文搜索 |
| notifications | recipient, isRead | compound | 未读查询 |

---

## 6. 安全设计

### 6.1 认证机制

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  Login  │────►│ JWT     │────►│ Access  │  有效期: 7天
│         │     │ Sign    │     │ Token   │
└─────────┘     └─────────┘     └─────────┘
                      │
                      ▼
                ┌─────────┐
                │ Refresh │  有效期: 30天
                │ Token   │  存储于 DB，支持撤销
                └─────────┘
```

- **Access Token**: 短期令牌，每次请求携带
- **Refresh Token**: 长期令牌，用于刷新 Access Token
- **密码加密**: bcrypt (12 rounds)
- **Token 刷新**: 自动拦截 401，透明刷新

### 6.2 安全中间件

| 中间件 | 功能 |
|--------|------|
| `helmet` | HTTP 安全头 |
| `cors` | 跨域保护 |
| `rate-limit` | 请求频率限制 (100/15min) |
| `zod validation` | 输入数据校验 |
| `bcryptjs` | 密码哈希 |
| `compression` | 响应压缩 |

### 6.3 RBAC 权限控制

```typescript
// 路由级权限控制示例
router.post('/', authorize(UserRole.ADMIN, UserRole.MANAGER), controller.create);
router.delete('/:id', authorize(UserRole.ADMIN), controller.delete);
```

---

## 7. 部署架构

### 7.1 Docker 容器编排

```
┌──────────────────────────────────────────┐
│            Docker Compose                │
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │ Frontend │  │ Backend  │             │
│  │ (Nginx)  │  │ (Node)   │             │
│  │  :80     │  │  :3000   │             │
│  └────┬─────┘  └────┬─────┘             │
│       │              │                   │
│  ┌────┴──────────────┴────┐             │
│  │      lab-network       │             │
│  └────┬──────┬──────┬─────┘             │
│       │      │      │                   │
│  ┌────┴──┐ ┌─┴───┐ ┌┴──────┐           │
│  │MongoDB│ │Redis│ │Postgre│           │
│  │ :27017│ │:6379│ │:5432  │           │
│  └───────┘ └─────┘ └───────┘           │
└──────────────────────────────────────────┘
```

### 7.2 Nginx 配置要点

- **静态资源**：前端 SPA 文件，1年强缓存（immutable）
- **API 代理**：`/api/*` → backend:3000
- **WebSocket**：`/socket.io/*` → backend:3000 (upgrade)
- **SPA 回退**：所有未匹配路由 → index.html
- **压缩**：Gzip on（JS/CSS/JSON/SVG）
- **安全头**：X-Frame-Options, X-Content-Type-Options, XSS-Protection

### 7.3 CI/CD 流程

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Push   │────►│  Lint   │────►│  Test   │────►│  Build  │
│  Code   │     │         │     │Coverage │     │ Docker  │
└─────────┘     └─────────┘     └─────────┘     └────┬────┘
                                                      │
                                                      ▼
                                                ┌─────────┐
                                                │  Push   │
                                                │  GHCR   │
                                                └────┬────┘
                                                     │
                                                     ▼
                                                ┌─────────┐
                                                │ Deploy  │
                                                │  SSH    │
                                                └─────────┘
```

**流水线阶段：**
1. **代码提交** → 触发 GitHub Actions
2. **Lint** → ESLint 代码质量检查
3. **Test** → Jest 单元测试 + 覆盖率
4. **Build** → TypeScript 编译 + Vite 构建
5. **Docker** → 多阶段构建镜像
6. **Push** → 推送至 GitHub Container Registry
7. **Deploy** → SSH 到服务器执行 `docker compose up -d`

---

## 8. 性能优化

### 8.1 前端优化

| 策略 | 实现 |
|------|------|
| **代码分割** | Vite 自动 + `manualChunks` (vendor/antd 分离) |
| **懒加载** | React.lazy + Suspense 路由级懒加载 |
| **缓存策略** | 静态资源 1年缓存，API 响应按需缓存 |
| **请求优化** | Axios 拦截器自动 Token 刷新，避免重复请求 |
| **状态管理** | Zustand 精确订阅，避免不必要渲染 |

### 8.2 后端优化

| 策略 | 实现 |
|------|------|
| **Redis 缓存** | 设备列表 5min TTL，详情 10min TTL |
| **数据库索引** | 复合索引覆盖常用查询 |
| **分页查询** | 标准分页 (skip/limit)，大数据量可切换游标分页 |
| **响应压缩** | compression 中间件 |
| **连接池** | MongoDB maxPoolSize: 10, PG max: 20 |

### 8.3 基础设施优化

| 策略 | 实现 |
|------|------|
| **Nginx Gzip** | 压缩 JS/CSS/JSON/SVG |
| **Docker 多阶段** | 最小化镜像体积 (alpine 基础) |
| **Health Check** | 容器健康检查，异常自动重启 |
| **日志管理** | Winston 分级日志 + 文件轮转 (5MB × 5) |

---

## 9. 项目结构

```
lab-system/
├── frontend/                        # 前端项目
│   ├── public/                      #   静态资源
│   ├── src/
│   │   ├── api/                     #   API 服务层 (6 模块)
│   │   ├── components/              #   通用组件
│   │   │   ├── common/              #     ProtectedRoute
│   │   │   └── layout/              #     MainLayout
│   │   ├── hooks/                   #   自定义 Hooks
│   │   ├── pages/                   #   页面组件 (6 页面)
│   │   │   ├── Dashboard/
│   │   │   ├── Users/
│   │   │   ├── Equipment/
│   │   │   ├── Reservations/
│   │   │   ├── Inventory/
│   │   │   ├── Notifications/
│   │   │   └── Login/
│   │   ├── store/                   #   Zustand 状态管理
│   │   ├── types/                   #   TypeScript 类型
│   │   ├── utils/                   #   工具函数
│   │   ├── styles/                  #   全局样式
│   │   ├── App.tsx                  #   路由 + 主题配置
│   │   └── main.tsx                 #   入口
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
├── backend/                         # 后端项目
│   ├── src/
│   │   ├── config/                  #   配置 (env, db, redis)
│   │   ├── controllers/             #   控制器 (6 模块)
│   │   ├── middleware/              #   中间件 (auth, error, validate)
│   │   ├── models/                  #   数据模型 (5 模型)
│   │   ├── routes/                  #   路由 (6 模块)
│   │   ├── services/                #   业务服务
│   │   ├── validators/              #   Zod 校验
│   │   ├── types/                   #   类型定义
│   │   ├── utils/                   #   工具 (logger, response)
│   │   └── app.ts                   #   入口
│   ├── package.json
│   ├── tsconfig.json
│   └── .env.example
├── docker/                          # Docker 构建
│   ├── frontend/
│   │   ├── Dockerfile               #   多阶段构建: build → nginx
│   │   └── nginx.conf               #   Nginx 站点配置
│   └── backend/
│       └── Dockerfile               #   多阶段构建: build → node
├── .github/workflows/
│   └── ci-cd.yml                    #   GitHub Actions 流水线
├── docs/
│   └── ARCHITECTURE.md              #   本文档
├── docker-compose.yml               #   生产环境编排
├── docker-compose.dev.yml           #   开发环境（仅基础设施）
└── .gitignore
```

---

## 10. 开发指南

### 10.1 本地开发环境

```bash
# 1. 启动基础设施（MongoDB + Redis）
docker compose -f docker-compose.dev.yml up -d

# 2. 启动后端
cd backend
cp .env.example .env
npm install
npm run dev        # http://localhost:3000

# 3. 启动前端
cd frontend
cp .env.example .env
npm install
npm run dev        # http://localhost:5173
```

### 10.2 生产部署

```bash
# 一键部署
docker compose up -d --build

# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 停止服务
docker compose down
```

### 10.3 开发规范

| 类别 | 规范 |
|------|------|
| **Git 分支** | main (生产) / develop (开发) / feature/* / hotfix/* |
| **提交消息** | `feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:` |
| **代码风格** | ESLint + TypeScript strict mode |
| **API 版本** | URL 路径版本化 `/api/v1/` |
| **错误处理** | 全局 ErrorHandler + AppError 类 |
| **日志级别** | error > warn > info > debug |

---

## 11. 扩展规划

### 11.1 短期 (1-3 月)

- [ ] 集成邮件通知 (Nodemailer)
- [ ] 添加文件上传功能 (Multer + OSS)
- [ ] 实现设备日历视图组件
- [ ] 添加数据导出 (Excel/CSV)
- [ ] 完善单元测试覆盖率 > 80%

### 11.2 中期 (3-6 月)

- [ ] 移动端适配 (响应式 + PWA)
- [ ] 仪表盘数据可视化 (ECharts)
- [ ] 审计日志系统
- [ ] 二维码/RFID 设备扫描
- [ ] 多实验室 / 多租户支持

### 11.3 长期 (6-12 月)

- [ ] 微服务拆分 (用户服务、设备服务、预约服务)
- [ ] Kubernetes 部署
- [ ] ELK 日志收集分析
- [ ] Prometheus + Grafana 监控
- [ ] AI 智能推荐 (设备使用预测、库存补充建议)
