import { Request } from 'express';

// User roles
export enum UserRole {
  ADMIN = 'admin',
  MANAGER = 'manager',
  RESEARCHER = 'researcher',
  STUDENT = 'student',
}

// Equipment status
export enum EquipmentStatus {
  AVAILABLE = 'available',
  IN_USE = 'in_use',
  MAINTENANCE = 'maintenance',
  RETIRED = 'retired',
}

// Reservation status
export enum ReservationStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  CANCELLED = 'cancelled',
  COMPLETED = 'completed',
}

// Inventory item category
export enum InventoryCategory {
  REAGENT = 'reagent',
  CONSUMABLE = 'consumable',
  GLASSWARE = 'glassware',
  INSTRUMENT = 'instrument',
  SAFETY = 'safety',
  OTHER = 'other',
}

// Notification type
export enum NotificationType {
  RESERVATION_APPROVED = 'reservation_approved',
  RESERVATION_REJECTED = 'reservation_rejected',
  EQUIPMENT_AVAILABLE = 'equipment_available',
  EQUIPMENT_MAINTENANCE = 'equipment_maintenance',
  INVENTORY_LOW = 'inventory_low',
  SYSTEM_ANNOUNCEMENT = 'system_announcement',
}

// JWT Payload
export interface JwtPayload {
  userId: string;
  email: string;
  role: UserRole;
}

// Authenticated Request
export interface AuthRequest extends Request {
  user?: JwtPayload;
}

// Pagination query
export interface PaginationQuery {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  search?: string;
}

// Date range filter
export interface DateRangeFilter {
  startDate?: Date;
  endDate?: Date;
}
