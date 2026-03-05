import { Router } from 'express';
import { InventoryController } from '../controllers/inventory.controller';
import { authenticate, authorize } from '../middleware/auth';
import { UserRole } from '../types';

const router = Router();

router.use(authenticate);

router.get('/', InventoryController.getAll);
router.get('/statistics', InventoryController.getStatistics);
router.get('/:id', InventoryController.getById);

router.post(
  '/',
  authorize(UserRole.ADMIN, UserRole.MANAGER),
  InventoryController.create
);

router.put(
  '/:id',
  authorize(UserRole.ADMIN, UserRole.MANAGER),
  InventoryController.update
);

router.delete(
  '/:id',
  authorize(UserRole.ADMIN),
  InventoryController.delete
);

router.post('/:id/usage', InventoryController.recordUsage);

export default router;
