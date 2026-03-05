import dayjs from "dayjs";
import React, { createContext, useContext, useMemo, useState } from "react";
import {
  DEFAULT_EQUIPMENTS,
  DEFAULT_INVENTORY_ITEMS,
  DEFAULT_INVENTORY_LOGS,
  DEFAULT_LABS,
  DEFAULT_MAINTENANCE,
  DEFAULT_RESERVATIONS,
  DEFAULT_ROLE_PERMISSIONS,
  DEFAULT_USERS,
} from "../constants";
import type {
  Equipment,
  InventoryItem,
  InventoryLog,
  InventoryMovementType,
  LabRoom,
  LoginPayload,
  MaintenanceRecord,
  RegisterPayload,
  Reservation,
  ReservationStatus,
  Role,
  RolePermissionMap,
  User,
  UserStatus,
} from "../types";

interface ReservationConflict {
  reservation: Reservation;
  lab: LabRoom | undefined;
  user: User | undefined;
}

interface AppStore {
  users: User[];
  rolePermissions: RolePermissionMap;
  currentUser: User | null;
  labs: LabRoom[];
  equipments: Equipment[];
  maintenanceRecords: MaintenanceRecord[];
  reservations: Reservation[];
  inventoryItems: InventoryItem[];
  inventoryLogs: InventoryLog[];
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  updateUserRole: (userId: string, role: Role) => void;
  updateUserStatus: (userId: string, status: UserStatus) => void;
  updateRolePermissions: (role: Role, permissions: string[]) => void;
  addEquipment: (
    payload: Omit<Equipment, "id" | "lastMaintenance" | "nextMaintenance">,
  ) => void;
  updateEquipmentStatus: (equipmentId: string, status: Equipment["status"]) => void;
  addMaintenanceRecord: (
    payload: Omit<MaintenanceRecord, "id">,
  ) => void;
  createReservation: (payload: {
    labId: string;
    purpose: string;
    startTime: string;
    endTime: string;
  }) => { ok: true } | { ok: false; message: string; conflicts?: ReservationConflict[] };
  updateReservationStatus: (reservationId: string, status: ReservationStatus) => void;
  addInventoryItem: (payload: Omit<InventoryItem, "id" | "lastUpdated" | "stock"> & { stock?: number }) => void;
  stockMovement: (payload: {
    itemId: string;
    type: InventoryMovementType;
    quantity: number;
    remark?: string;
  }) => { ok: true } | { ok: false; message: string };
}

const STORAGE_KEYS = {
  users: "lab_users",
  rolePermissions: "lab_role_permissions",
  currentUserId: "lab_current_user_id",
  labs: "lab_rooms",
  equipments: "lab_equipments",
  maintenance: "lab_maintenance_records",
  reservations: "lab_reservations",
  inventoryItems: "lab_inventory_items",
  inventoryLogs: "lab_inventory_logs",
};

const AppContext = createContext<AppStore | undefined>(undefined);

function readStorage<T>(key: string, fallback: T): T {
  const raw = localStorage.getItem(key);
  if (!raw) {
    localStorage.setItem(key, JSON.stringify(fallback));
    return fallback;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    localStorage.setItem(key, JSON.stringify(fallback));
    return fallback;
  }
}

function saveStorage<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value));
}

function genId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [users, setUsers] = useState<User[]>(() => readStorage(STORAGE_KEYS.users, DEFAULT_USERS));
  const [rolePermissions, setRolePermissions] = useState<RolePermissionMap>(() =>
    readStorage(STORAGE_KEYS.rolePermissions, DEFAULT_ROLE_PERMISSIONS),
  );
  const [labs] = useState<LabRoom[]>(() => readStorage(STORAGE_KEYS.labs, DEFAULT_LABS));
  const [equipments, setEquipments] = useState<Equipment[]>(() =>
    readStorage(STORAGE_KEYS.equipments, DEFAULT_EQUIPMENTS),
  );
  const [maintenanceRecords, setMaintenanceRecords] = useState<MaintenanceRecord[]>(() =>
    readStorage(STORAGE_KEYS.maintenance, DEFAULT_MAINTENANCE),
  );
  const [reservations, setReservations] = useState<Reservation[]>(() =>
    readStorage(STORAGE_KEYS.reservations, DEFAULT_RESERVATIONS),
  );
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>(() =>
    readStorage(STORAGE_KEYS.inventoryItems, DEFAULT_INVENTORY_ITEMS),
  );
  const [inventoryLogs, setInventoryLogs] = useState<InventoryLog[]>(() =>
    readStorage(STORAGE_KEYS.inventoryLogs, DEFAULT_INVENTORY_LOGS),
  );
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    const currentUserId = localStorage.getItem(STORAGE_KEYS.currentUserId);
    if (!currentUserId) {
      return null;
    }
    return users.find((u) => u.id === currentUserId) ?? null;
  });

  const login = async (payload: LoginPayload) => {
    const target = users.find((u) => u.email === payload.email && u.password === payload.password);
    if (!target) {
      throw new Error("邮箱或密码错误");
    }
    if (target.status !== "active") {
      throw new Error("账号已被禁用，请联系管理员");
    }
    setCurrentUser(target);
    localStorage.setItem(STORAGE_KEYS.currentUserId, target.id);
  };

  const register = async (payload: RegisterPayload) => {
    if (users.some((u) => u.email === payload.email)) {
      throw new Error("该邮箱已注册");
    }
    const newUser: User = {
      id: genId("user"),
      name: payload.name.trim(),
      email: payload.email.trim().toLowerCase(),
      password: payload.password,
      role: "user",
      status: "active",
      createdAt: new Date().toISOString(),
    };
    const nextUsers = [newUser, ...users];
    setUsers(nextUsers);
    saveStorage(STORAGE_KEYS.users, nextUsers);
  };

  const logout = () => {
    setCurrentUser(null);
    localStorage.removeItem(STORAGE_KEYS.currentUserId);
  };

  const updateUserRole = (userId: string, role: Role) => {
    const nextUsers = users.map((u) => (u.id === userId ? { ...u, role } : u));
    setUsers(nextUsers);
    saveStorage(STORAGE_KEYS.users, nextUsers);
    if (currentUser?.id === userId) {
      const updated = nextUsers.find((u) => u.id === userId) ?? null;
      setCurrentUser(updated);
    }
  };

  const updateUserStatus = (userId: string, status: UserStatus) => {
    const nextUsers = users.map((u) => (u.id === userId ? { ...u, status } : u));
    setUsers(nextUsers);
    saveStorage(STORAGE_KEYS.users, nextUsers);
    if (currentUser?.id === userId && status === "disabled") {
      logout();
    }
  };

  const updateRolePermissions = (role: Role, permissions: string[]) => {
    const next = { ...rolePermissions, [role]: permissions };
    setRolePermissions(next);
    saveStorage(STORAGE_KEYS.rolePermissions, next);
  };

  const addEquipment: AppStore["addEquipment"] = (payload) => {
    const newEquipment: Equipment = {
      ...payload,
      id: genId("eq"),
      utilization: Math.max(0, Math.min(100, payload.utilization)),
    };
    const next = [newEquipment, ...equipments];
    setEquipments(next);
    saveStorage(STORAGE_KEYS.equipments, next);
  };

  const updateEquipmentStatus = (equipmentId: string, status: Equipment["status"]) => {
    const next = equipments.map((eq) => (eq.id === equipmentId ? { ...eq, status } : eq));
    setEquipments(next);
    saveStorage(STORAGE_KEYS.equipments, next);
  };

  const addMaintenanceRecord: AppStore["addMaintenanceRecord"] = (payload) => {
    const newRecord: MaintenanceRecord = { ...payload, id: genId("mt") };
    const nextRecords = [newRecord, ...maintenanceRecords];
    setMaintenanceRecords(nextRecords);
    saveStorage(STORAGE_KEYS.maintenance, nextRecords);

    const nextEquipments: Equipment[] = equipments.map((eq): Equipment => {
      if (eq.id !== payload.equipmentId) {
        return eq;
      }
      return {
        ...eq,
        status: "available",
        lastMaintenance: payload.date,
        nextMaintenance: dayjs(payload.date).add(30, "day").toISOString(),
      };
    });
    setEquipments(nextEquipments);
    saveStorage(STORAGE_KEYS.equipments, nextEquipments);
  };

  const createReservation: AppStore["createReservation"] = (payload) => {
    if (!currentUser) {
      return { ok: false, message: "请先登录" };
    }
    if (!dayjs(payload.startTime).isBefore(dayjs(payload.endTime))) {
      return { ok: false, message: "结束时间必须晚于开始时间" };
    }
    const activeReservations = reservations.filter((rs) =>
      ["pending", "approved"].includes(rs.status),
    );
    const conflicts = activeReservations
      .filter((rs) => {
        if (rs.labId !== payload.labId) {
          return false;
        }
        const overlap =
          dayjs(payload.startTime).isBefore(dayjs(rs.endTime)) &&
          dayjs(payload.endTime).isAfter(dayjs(rs.startTime));
        return overlap;
      })
      .map((reservation) => ({
        reservation,
        lab: labs.find((l) => l.id === reservation.labId),
        user: users.find((u) => u.id === reservation.userId),
      }));

    if (conflicts.length > 0) {
      return { ok: false, message: "预约时间冲突", conflicts };
    }

    const newReservation: Reservation = {
      id: genId("rs"),
      labId: payload.labId,
      userId: currentUser.id,
      purpose: payload.purpose.trim(),
      startTime: payload.startTime,
      endTime: payload.endTime,
      status: "pending",
      createdAt: new Date().toISOString(),
    };
    const next = [newReservation, ...reservations];
    setReservations(next);
    saveStorage(STORAGE_KEYS.reservations, next);
    return { ok: true };
  };

  const updateReservationStatus = (reservationId: string, status: ReservationStatus) => {
    const next = reservations.map((rs) => (rs.id === reservationId ? { ...rs, status } : rs));
    setReservations(next);
    saveStorage(STORAGE_KEYS.reservations, next);
  };

  const addInventoryItem: AppStore["addInventoryItem"] = (payload) => {
    const newItem: InventoryItem = {
      id: genId("inv"),
      name: payload.name,
      category: payload.category,
      unit: payload.unit,
      stock: payload.stock ?? 0,
      threshold: payload.threshold,
      location: payload.location,
      lastUpdated: new Date().toISOString(),
    };
    const next = [newItem, ...inventoryItems];
    setInventoryItems(next);
    saveStorage(STORAGE_KEYS.inventoryItems, next);
  };

  const stockMovement: AppStore["stockMovement"] = ({ itemId, quantity, type, remark }) => {
    if (!currentUser) {
      return { ok: false, message: "请先登录" };
    }
    if (quantity <= 0) {
      return { ok: false, message: "数量必须大于 0" };
    }
    const target = inventoryItems.find((item) => item.id === itemId);
    if (!target) {
      return { ok: false, message: "未找到库存物品" };
    }
    if (type === "out" && target.stock < quantity) {
      return { ok: false, message: "库存不足，无法出库" };
    }

    const nextItems = inventoryItems.map((item) => {
      if (item.id !== itemId) {
        return item;
      }
      const stock = type === "in" ? item.stock + quantity : item.stock - quantity;
      return {
        ...item,
        stock,
        lastUpdated: new Date().toISOString(),
      };
    });
    setInventoryItems(nextItems);
    saveStorage(STORAGE_KEYS.inventoryItems, nextItems);

    const newLog: InventoryLog = {
      id: genId("log"),
      itemId,
      type,
      quantity,
      operator: currentUser.name,
      remark: remark?.trim(),
      time: new Date().toISOString(),
    };
    const nextLogs = [newLog, ...inventoryLogs];
    setInventoryLogs(nextLogs);
    saveStorage(STORAGE_KEYS.inventoryLogs, nextLogs);
    return { ok: true };
  };

  const value = useMemo<AppStore>(
    () => ({
      users,
      rolePermissions,
      currentUser,
      labs,
      equipments,
      maintenanceRecords,
      reservations,
      inventoryItems,
      inventoryLogs,
      login,
      register,
      logout,
      updateUserRole,
      updateUserStatus,
      updateRolePermissions,
      addEquipment,
      updateEquipmentStatus,
      addMaintenanceRecord,
      createReservation,
      updateReservationStatus,
      addInventoryItem,
      stockMovement,
    }),
    [
      users,
      rolePermissions,
      currentUser,
      labs,
      equipments,
      maintenanceRecords,
      reservations,
      inventoryItems,
      inventoryLogs,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppStore() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppStore 必须在 AppProvider 中使用");
  }
  return context;
}
