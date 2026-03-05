import { Router } from 'express';
import { ReservationController } from '../controllers/reservation.controller';
import { authenticate, authorize } from '../middleware/auth';
import { validate } from '../middleware/validate';
import {
  createReservationSchema,
  updateReservationStatusSchema,
} from '../validators/reservation.validator';
import { UserRole } from '../types';

const router = Router();

router.use(authenticate);

router.get('/', ReservationController.getAll);
router.get('/my', ReservationController.getMyReservations);
router.get('/calendar', ReservationController.getCalendar);

router.post('/', validate(createReservationSchema), ReservationController.create);

router.put(
  '/:id/status',
  authorize(UserRole.ADMIN, UserRole.MANAGER),
  validate(updateReservationStatusSchema),
  ReservationController.updateStatus
);

router.put('/:id/cancel', ReservationController.cancel);

export default router;
