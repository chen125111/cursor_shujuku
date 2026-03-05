import { z } from 'zod';

export const createEquipmentSchema = z.object({
  body: z.object({
    name: z.string().min(1, '请输入设备名称'),
    code: z.string().min(1, '请输入设备编号'),
    category: z.string().min(1, '请选择设备分类'),
    brand: z.string().min(1, '请输入品牌'),
    model: z.string().min(1, '请输入型号'),
    specifications: z.string().optional(),
    location: z.string().min(1, '请输入存放位置'),
    purchaseDate: z.string().datetime().or(z.string()),
    purchasePrice: z.number().min(0, '价格不能为负'),
    warrantyExpiry: z.string().optional(),
    department: z.string().min(1, '请选择所属部门'),
    description: z.string().optional(),
  }),
});

export const updateEquipmentSchema = z.object({
  body: z.object({
    name: z.string().min(1).optional(),
    category: z.string().optional(),
    brand: z.string().optional(),
    model: z.string().optional(),
    specifications: z.string().optional(),
    location: z.string().optional(),
    status: z.enum(['available', 'in_use', 'maintenance', 'retired']).optional(),
    purchasePrice: z.number().min(0).optional(),
    warrantyExpiry: z.string().optional(),
    department: z.string().optional(),
    description: z.string().optional(),
  }),
  params: z.object({
    id: z.string().min(1),
  }),
});

export const addMaintenanceSchema = z.object({
  body: z.object({
    type: z.string().min(1, '请选择维护类型'),
    description: z.string().min(1, '请输入维护描述'),
    cost: z.number().min(0).optional(),
    technician: z.string().optional(),
  }),
  params: z.object({
    id: z.string().min(1),
  }),
});
