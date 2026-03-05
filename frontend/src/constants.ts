import dayjs from "dayjs";
import type {
  Equipment,
  InventoryItem,
  InventoryLog,
  LabRoom,
  MaintenanceRecord,
  Reservation,
  RolePermissionMap,
  User,
} from "./types";

export const PERMISSION_OPTIONS = [
  "user:view",
  "user:edit",
  "equipment:view",
  "equipment:edit",
  "reservation:view",
  "reservation:approve",
  "inventory:view",
  "inventory:edit",
];

export const DEFAULT_ROLE_PERMISSIONS: RolePermissionMap = {
  admin: [...PERMISSION_OPTIONS],
  manager: [
    "user:view",
    "equipment:view",
    "equipment:edit",
    "reservation:view",
    "reservation:approve",
    "inventory:view",
    "inventory:edit",
  ],
  user: ["equipment:view", "reservation:view", "inventory:view"],
};

export const DEFAULT_USERS: User[] = [
  {
    id: "u_admin",
    name: "系统管理员",
    email: "admin@lab.local",
    password: "admin123",
    role: "admin",
    status: "active",
    createdAt: dayjs().subtract(60, "day").toISOString(),
  },
  {
    id: "u_manager",
    name: "实验室主管",
    email: "manager@lab.local",
    password: "manager123",
    role: "manager",
    status: "active",
    createdAt: dayjs().subtract(45, "day").toISOString(),
  },
  {
    id: "u_researcher",
    name: "研究员A",
    email: "user@lab.local",
    password: "user123",
    role: "user",
    status: "active",
    createdAt: dayjs().subtract(21, "day").toISOString(),
  },
];

export const DEFAULT_LABS: LabRoom[] = [
  { id: "lab_1", name: "生化实验室A", location: "1F-101", capacity: 20 },
  { id: "lab_2", name: "材料实验室B", location: "2F-201", capacity: 15 },
  { id: "lab_3", name: "精密仪器室C", location: "3F-301", capacity: 8 },
];

export const DEFAULT_EQUIPMENTS: Equipment[] = [
  {
    id: "eq_1",
    name: "高效液相色谱仪",
    category: "分析仪器",
    location: "1F-101",
    status: "available",
    utilization: 62,
    responsible: "实验室主管",
    lastMaintenance: dayjs().subtract(12, "day").toISOString(),
    nextMaintenance: dayjs().add(18, "day").toISOString(),
  },
  {
    id: "eq_2",
    name: "离心机",
    category: "通用设备",
    location: "1F-102",
    status: "in_use",
    utilization: 84,
    responsible: "研究员A",
    lastMaintenance: dayjs().subtract(8, "day").toISOString(),
    nextMaintenance: dayjs().add(22, "day").toISOString(),
  },
  {
    id: "eq_3",
    name: "X射线衍射仪",
    category: "精密设备",
    location: "2F-201",
    status: "maintenance",
    utilization: 40,
    responsible: "设备工程师",
    lastMaintenance: dayjs().subtract(2, "day").toISOString(),
    nextMaintenance: dayjs().add(28, "day").toISOString(),
  },
];

export const DEFAULT_MAINTENANCE: MaintenanceRecord[] = [
  {
    id: "mt_1",
    equipmentId: "eq_1",
    date: dayjs().subtract(12, "day").toISOString(),
    type: "例行保养",
    description: "更换滤芯并完成校准",
    technician: "王工",
    cost: 1200,
  },
  {
    id: "mt_2",
    equipmentId: "eq_3",
    date: dayjs().subtract(2, "day").toISOString(),
    type: "故障维修",
    description: "修复温控模块",
    technician: "李工",
    cost: 3200,
  },
];

export const DEFAULT_RESERVATIONS: Reservation[] = [
  {
    id: "rs_1",
    labId: "lab_1",
    userId: "u_researcher",
    purpose: "蛋白样本检测",
    startTime: dayjs().add(1, "day").hour(9).minute(0).second(0).toISOString(),
    endTime: dayjs().add(1, "day").hour(11).minute(0).second(0).toISOString(),
    status: "approved",
    createdAt: dayjs().subtract(2, "day").toISOString(),
  },
  {
    id: "rs_2",
    labId: "lab_2",
    userId: "u_manager",
    purpose: "材料性能测试",
    startTime: dayjs().add(1, "day").hour(13).minute(0).second(0).toISOString(),
    endTime: dayjs().add(1, "day").hour(15).minute(0).second(0).toISOString(),
    status: "pending",
    createdAt: dayjs().subtract(1, "day").toISOString(),
  },
];

export const DEFAULT_INVENTORY_ITEMS: InventoryItem[] = [
  {
    id: "inv_1",
    name: "一次性手套",
    category: "耗材",
    unit: "盒",
    stock: 32,
    threshold: 20,
    location: "仓库A",
    lastUpdated: dayjs().subtract(1, "day").toISOString(),
  },
  {
    id: "inv_2",
    name: "培养皿",
    category: "耗材",
    unit: "包",
    stock: 8,
    threshold: 10,
    location: "仓库A",
    lastUpdated: dayjs().subtract(2, "day").toISOString(),
  },
  {
    id: "inv_3",
    name: "乙醇",
    category: "试剂",
    unit: "瓶",
    stock: 15,
    threshold: 8,
    location: "危化品柜",
    lastUpdated: dayjs().subtract(3, "day").toISOString(),
  },
];

export const DEFAULT_INVENTORY_LOGS: InventoryLog[] = [
  {
    id: "log_1",
    itemId: "inv_1",
    type: "out",
    quantity: 5,
    operator: "研究员A",
    remark: "常规实验领用",
    time: dayjs().subtract(1, "day").toISOString(),
  },
  {
    id: "log_2",
    itemId: "inv_2",
    type: "in",
    quantity: 12,
    operator: "仓管员",
    remark: "补货",
    time: dayjs().subtract(4, "day").toISOString(),
  },
];
