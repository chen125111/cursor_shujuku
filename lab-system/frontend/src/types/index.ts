// User types
export enum UserRole {
  ADMIN = 'admin',
  MANAGER = 'manager',
  RESEARCHER = 'researcher',
  STUDENT = 'student',
}

export interface User {
  _id: string;
  username: string;
  email: string;
  role: UserRole;
  displayName: string;
  department: string;
  phone?: string;
  avatar?: string;
  isActive: boolean;
  lastLoginAt?: string;
  createdAt: string;
  updatedAt: string;
}

// Equipment types
export enum EquipmentStatus {
  AVAILABLE = 'available',
  IN_USE = 'in_use',
  MAINTENANCE = 'maintenance',
  RETIRED = 'retired',
}

export interface Equipment {
  _id: string;
  name: string;
  code: string;
  category: string;
  brand: string;
  model: string;
  specifications: string;
  location: string;
  status: EquipmentStatus;
  purchaseDate: string;
  purchasePrice: number;
  warrantyExpiry?: string;
  manager: User;
  department: string;
  description?: string;
  images: string[];
  maintenanceRecords: MaintenanceRecord[];
  usageCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface MaintenanceRecord {
  date: string;
  type: string;
  description: string;
  cost: number;
  technician: string;
}

// Reservation types
export enum ReservationStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  CANCELLED = 'cancelled',
  COMPLETED = 'completed',
}

export interface Reservation {
  _id: string;
  equipment: Equipment;
  user: User;
  startTime: string;
  endTime: string;
  purpose: string;
  status: ReservationStatus;
  approvedBy?: User;
  approvedAt?: string;
  rejectReason?: string;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

// Inventory types
export enum InventoryCategory {
  REAGENT = 'reagent',
  CONSUMABLE = 'consumable',
  GLASSWARE = 'glassware',
  INSTRUMENT = 'instrument',
  SAFETY = 'safety',
  OTHER = 'other',
}

export interface InventoryItem {
  _id: string;
  name: string;
  code: string;
  category: InventoryCategory;
  specifications: string;
  unit: string;
  quantity: number;
  minQuantity: number;
  location: string;
  supplier: string;
  unitPrice: number;
  expiryDate?: string;
  department: string;
  manager: User;
  description?: string;
  usageRecords: UsageRecord[];
  createdAt: string;
  updatedAt: string;
}

export interface UsageRecord {
  user: User;
  quantity: number;
  type: 'in' | 'out';
  date: string;
  notes?: string;
}

// Notification types
export enum NotificationType {
  RESERVATION_APPROVED = 'reservation_approved',
  RESERVATION_REJECTED = 'reservation_rejected',
  EQUIPMENT_AVAILABLE = 'equipment_available',
  EQUIPMENT_MAINTENANCE = 'equipment_maintenance',
  INVENTORY_LOW = 'inventory_low',
  SYSTEM_ANNOUNCEMENT = 'system_announcement',
}

export interface Notification {
  _id: string;
  recipient: string;
  sender?: User;
  type: NotificationType;
  title: string;
  content: string;
  isRead: boolean;
  readAt?: string;
  relatedId?: string;
  relatedModel?: string;
  createdAt: string;
}

// API Response types
export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
  meta?: PaginationMeta;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

// Auth types
export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  username: string;
  email: string;
  password: string;
  displayName: string;
  department: string;
  phone?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}
