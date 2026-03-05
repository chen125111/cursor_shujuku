export type Role = "admin" | "manager" | "user";
export type UserStatus = "active" | "disabled";
export type EquipmentStatus = "available" | "in_use" | "maintenance" | "offline";
export type ReservationStatus = "pending" | "approved" | "rejected" | "cancelled";
export type InventoryMovementType = "in" | "out";

export interface User {
  id: string;
  name: string;
  email: string;
  password: string;
  role: Role;
  status: UserStatus;
  createdAt: string;
}

export interface RolePermissionMap {
  admin: string[];
  manager: string[];
  user: string[];
}

export interface Equipment {
  id: string;
  name: string;
  category: string;
  location: string;
  status: EquipmentStatus;
  utilization: number;
  responsible: string;
  lastMaintenance?: string;
  nextMaintenance?: string;
}

export interface MaintenanceRecord {
  id: string;
  equipmentId: string;
  date: string;
  type: string;
  description: string;
  technician: string;
  cost?: number;
}

export interface LabRoom {
  id: string;
  name: string;
  location: string;
  capacity: number;
}

export interface Reservation {
  id: string;
  labId: string;
  userId: string;
  purpose: string;
  startTime: string;
  endTime: string;
  status: ReservationStatus;
  createdAt: string;
}

export interface InventoryItem {
  id: string;
  name: string;
  category: string;
  unit: string;
  stock: number;
  threshold: number;
  location: string;
  lastUpdated: string;
}

export interface InventoryLog {
  id: string;
  itemId: string;
  type: InventoryMovementType;
  quantity: number;
  operator: string;
  remark?: string;
  time: string;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}
