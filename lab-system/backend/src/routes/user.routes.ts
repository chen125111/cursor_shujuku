import { Router } from 'express';
import { UserController } from '../controllers/user.controller';
import { authenticate, authorize } from '../middleware/auth';
import { UserRole } from '../types';

const router = Router();

router.use(authenticate);

router.get('/', UserController.getAll);
router.get('/departments', UserController.getDepartments);
router.get('/:id', UserController.getById);
router.put('/:id', UserController.update);
router.put('/:id/role', authorize(UserRole.ADMIN), UserController.updateRole);
router.put('/:id/toggle-active', authorize(UserRole.ADMIN), UserController.toggleActive);

export default router;
