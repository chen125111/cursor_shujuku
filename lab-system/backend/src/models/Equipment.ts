import mongoose, { Schema, Document } from 'mongoose';
import { EquipmentStatus } from '../types';

export interface IEquipment extends Document {
  name: string;
  code: string;
  category: string;
  brand: string;
  model: string;
  specifications: string;
  location: string;
  status: EquipmentStatus;
  purchaseDate: Date;
  purchasePrice: number;
  warrantyExpiry?: Date;
  manager: mongoose.Types.ObjectId;
  department: string;
  description?: string;
  images: string[];
  maintenanceRecords: {
    date: Date;
    type: string;
    description: string;
    cost: number;
    technician: string;
  }[];
  usageCount: number;
  createdAt: Date;
  updatedAt: Date;
}

const equipmentSchema = new Schema<IEquipment>(
  {
    name: { type: String, required: true, trim: true },
    code: { type: String, required: true, unique: true, trim: true },
    category: { type: String, required: true, trim: true },
    brand: { type: String, required: true, trim: true },
    model: { type: String, required: true, trim: true },
    specifications: { type: String, trim: true },
    location: { type: String, required: true, trim: true },
    status: {
      type: String,
      enum: Object.values(EquipmentStatus),
      default: EquipmentStatus.AVAILABLE,
    },
    purchaseDate: { type: Date, required: true },
    purchasePrice: { type: Number, required: true, min: 0 },
    warrantyExpiry: { type: Date },
    manager: { type: Schema.Types.ObjectId, ref: 'User', required: true },
    department: { type: String, required: true, trim: true },
    description: { type: String },
    images: [{ type: String }],
    maintenanceRecords: [
      {
        date: { type: Date, required: true },
        type: { type: String, required: true },
        description: { type: String },
        cost: { type: Number, default: 0 },
        technician: { type: String },
      },
    ],
    usageCount: { type: Number, default: 0 },
  },
  {
    timestamps: true,
    toJSON: { virtuals: true },
  }
);

equipmentSchema.index({ code: 1 });
equipmentSchema.index({ status: 1 });
equipmentSchema.index({ category: 1 });
equipmentSchema.index({ department: 1 });
equipmentSchema.index({ name: 'text', description: 'text' });

export const Equipment = mongoose.model<IEquipment>('Equipment', equipmentSchema);
