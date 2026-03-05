import { Router } from 'express';
import authRoutes from './auth.routes';
import userRoutes from './user.routes';
import equipmentRoutes from './equipment.routes';
import reservationRoutes from './reservation.routes';
import inventoryRoutes from './inventory.routes';
import notificationRoutes from './notification.routes';

const router = Router();

router.use('/auth', authRoutes);
router.use('/users', userRoutes);
router.use('/equipment', equipmentRoutes);
router.use('/reservations', reservationRoutes);
router.use('/inventory', inventoryRoutes);
router.use('/notifications', notificationRoutes);

export default router;
