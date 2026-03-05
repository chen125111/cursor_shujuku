import { Router } from 'express';
import { EquipmentController } from '../controllers/equipment.controller';
import { authenticate, authorize } from '../middleware/auth';
import { validate } from '../middleware/validate';
import {
  createEquipmentSchema,
  updateEquipmentSchema,
  addMaintenanceSchema,
} from '../validators/equipment.validator';
import { UserRole } from '../types';

const router = Router();

router.use(authenticate);

router.get('/', EquipmentController.getAll);
router.get('/statistics', EquipmentController.getStatistics);
router.get('/:id', EquipmentController.getById);

router.post(
  '/',
  authorize(UserRole.ADMIN, UserRole.MANAGER),
  validate(createEquipmentSchema),
  EquipmentController.create
);

router.put(
  '/:id',
  authorize(UserRole.ADMIN, UserRole.MANAGER),
  validate(updateEquipmentSchema),
  EquipmentController.update
);

router.delete(
  '/:id',
  authorize(UserRole.ADMIN),
  EquipmentController.delete
);

router.post(
  '/:id/maintenance',
  authorize(UserRole.ADMIN, UserRole.MANAGER),
  validate(addMaintenanceSchema),
  EquipmentController.addMaintenance
);

export default router;
