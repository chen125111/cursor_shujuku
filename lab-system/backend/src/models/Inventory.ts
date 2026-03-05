import mongoose, { Schema, Document } from 'mongoose';
import { InventoryCategory } from '../types';

export interface IInventory extends Document {
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
  expiryDate?: Date;
  department: string;
  manager: mongoose.Types.ObjectId;
  description?: string;
  usageRecords: {
    user: mongoose.Types.ObjectId;
    quantity: number;
    type: 'in' | 'out';
    date: Date;
    notes?: string;
  }[];
  createdAt: Date;
  updatedAt: Date;
}

const inventorySchema = new Schema<IInventory>(
  {
    name: { type: String, required: true, trim: true },
    code: { type: String, required: true, unique: true, trim: true },
    category: {
      type: String,
      enum: Object.values(InventoryCategory),
      required: true,
    },
    specifications: { type: String, trim: true },
    unit: { type: String, required: true, trim: true },
    quantity: { type: Number, required: true, min: 0 },
    minQuantity: { type: Number, required: true, min: 0 },
    location: { type: String, required: true, trim: true },
    supplier: { type: String, trim: true },
    unitPrice: { type: Number, min: 0 },
    expiryDate: { type: Date },
    department: { type: String, required: true, trim: true },
    manager: { type: Schema.Types.ObjectId, ref: 'User', required: true },
    description: { type: String },
    usageRecords: [
      {
        user: { type: Schema.Types.ObjectId, ref: 'User', required: true },
        quantity: { type: Number, required: true },
        type: { type: String, enum: ['in', 'out'], required: true },
        date: { type: Date, default: Date.now },
        notes: { type: String },
      },
    ],
  },
  {
    timestamps: true,
  }
);

inventorySchema.index({ code: 1 });
inventorySchema.index({ category: 1 });
inventorySchema.index({ department: 1 });
inventorySchema.index({ name: 'text', description: 'text' });

inventorySchema.virtual('isLowStock').get(function () {
  return this.quantity <= this.minQuantity;
});

export const Inventory = mongoose.model<IInventory>('Inventory', inventorySchema);
