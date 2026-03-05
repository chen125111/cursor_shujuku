import mongoose, { Schema, Document } from 'mongoose';
import { ReservationStatus } from '../types';

export interface IReservation extends Document {
  equipment: mongoose.Types.ObjectId;
  user: mongoose.Types.ObjectId;
  startTime: Date;
  endTime: Date;
  purpose: string;
  status: ReservationStatus;
  approvedBy?: mongoose.Types.ObjectId;
  approvedAt?: Date;
  rejectReason?: string;
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

const reservationSchema = new Schema<IReservation>(
  {
    equipment: {
      type: Schema.Types.ObjectId,
      ref: 'Equipment',
      required: true,
    },
    user: { type: Schema.Types.ObjectId, ref: 'User', required: true },
    startTime: { type: Date, required: true },
    endTime: { type: Date, required: true },
    purpose: { type: String, required: true, trim: true },
    status: {
      type: String,
      enum: Object.values(ReservationStatus),
      default: ReservationStatus.PENDING,
    },
    approvedBy: { type: Schema.Types.ObjectId, ref: 'User' },
    approvedAt: { type: Date },
    rejectReason: { type: String },
    notes: { type: String },
  },
  {
    timestamps: true,
  }
);

reservationSchema.index({ equipment: 1, startTime: 1, endTime: 1 });
reservationSchema.index({ user: 1 });
reservationSchema.index({ status: 1 });
reservationSchema.index({ startTime: 1 });

reservationSchema.pre('save', function (next) {
  if (this.startTime >= this.endTime) {
    return next(new Error('End time must be after start time'));
  }
  next();
});

export const Reservation = mongoose.model<IReservation>(
  'Reservation',
  reservationSchema
);
