import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Input,
  Select,
  Tag,
  Modal,
  Form,
  InputNumber,
  DatePicker,
  message,
  Card,
  Row,
  Col,
  Popconfirm,
  Typography,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  ToolOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { equipmentApi } from '@/api/equipment';
import type { Equipment, EquipmentStatus } from '@/types';
import { useAuthStore } from '@/store/authStore';

const { Title } = Typography;

const statusMap: Record<string, { color: string; label: string }> = {
  available: { color: 'green', label: '可用' },
  in_use: { color: 'blue', label: '使用中' },
  maintenance: { color: 'orange', label: '维护中' },
  retired: { color: 'default', label: '已报废' },
};

const categories = [
  '分析仪器', '光学仪器', '电子设备', '化学设备',
  '生物设备', '物理设备', '计算设备', '安全设备', '其他',
];

const EquipmentPage: React.FC = () => {
  const [data, setData] = useState<Equipment[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  const [modalVisible, setModalVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentEquipment, setCurrentEquipment] = useState<Equipment | null>(null);
  const [form] = Form.useForm();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin' || user?.role === 'manager';

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await equipmentApi.getAll({
        page,
        limit: pageSize,
        search: search || undefined,
        status: statusFilter,
        category: categoryFilter,
      });
      if (res.success) {
        setData(res.data || []);
        setTotal(res.meta?.total || 0);
      }
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, statusFilter, categoryFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = () => {
    setCurrentEquipment(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: Equipment) => {
    setCurrentEquipment(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (currentEquipment) {
        await equipmentApi.update(currentEquipment._id, values);
        message.success('更新成功');
      } else {
        await equipmentApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchData();
    } catch {
      // validation error
    }
  };

  const handleDelete = async (id: string) => {
    await equipmentApi.delete(id);
    message.success('删除成功');
    fetchData();
  };

  const columns = [
    {
      title: '设备编号',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: '设备名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
    },
    {
      title: '品牌/型号',
      key: 'brandModel',
      width: 150,
      render: (_: unknown, record: Equipment) => `${record.brand} ${record.model}`,
    },
    {
      title: '位置',
      dataIndex: 'location',
      key: 'location',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: EquipmentStatus) => (
        <Tag color={statusMap[status]?.color}>{statusMap[status]?.label}</Tag>
      ),
    },
    {
      title: '负责人',
      dataIndex: ['manager', 'displayName'],
      key: 'manager',
      width: 100,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: Equipment) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                setCurrentEquipment(record);
                setDetailVisible(true);
              }}
            />
          </Tooltip>
          {isAdmin && (
            <>
              <Tooltip title="编辑">
                <Button
                  type="link"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                />
              </Tooltip>
              <Popconfirm
                title="确认删除此设备？"
                onConfirm={() => handleDelete(record._id)}
              >
                <Tooltip title="删除">
                  <Button
                    type="link"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                  />
                </Tooltip>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4}>
        <ToolOutlined style={{ marginRight: 8 }} />
        设备管理
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="搜索设备名称或编号"
                prefix={<SearchOutlined />}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onPressEnter={() => { setPage(1); fetchData(); }}
                style={{ width: 250 }}
                allowClear
              />
              <Select
                placeholder="状态筛选"
                allowClear
                style={{ width: 130 }}
                value={statusFilter}
                onChange={(v) => { setStatusFilter(v); setPage(1); }}
                options={Object.entries(statusMap).map(([k, v]) => ({
                  value: k,
                  label: v.label,
                }))}
              />
              <Select
                placeholder="分类筛选"
                allowClear
                style={{ width: 130 }}
                value={categoryFilter}
                onChange={(v) => { setCategoryFilter(v); setPage(1); }}
                options={categories.map((c) => ({ value: c, label: c }))}
              />
            </Space>
          </Col>
          {isAdmin && (
            <Col>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                添加设备
              </Button>
            </Col>
          )}
        </Row>
      </Card>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="_id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
        scroll={{ x: 1100 }}
      />

      <Modal
        title={currentEquipment ? '编辑设备' : '添加设备'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="设备名称" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="code" label="设备编号" rules={[{ required: true }]}>
                <Input disabled={!!currentEquipment} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="分类" rules={[{ required: true }]}>
                <Select options={categories.map((c) => ({ value: c, label: c }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="location" label="存放位置" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="brand" label="品牌" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="model" label="型号" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="purchasePrice" label="采购价格" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} prefix="¥" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="purchaseDate" label="采购日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="department" label="所属部门" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="设备描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="设备详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={640}
      >
        {currentEquipment && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}><strong>编号：</strong>{currentEquipment.code}</Col>
              <Col span={12}><strong>名称：</strong>{currentEquipment.name}</Col>
              <Col span={12}><strong>品牌：</strong>{currentEquipment.brand}</Col>
              <Col span={12}><strong>型号：</strong>{currentEquipment.model}</Col>
              <Col span={12}><strong>分类：</strong>{currentEquipment.category}</Col>
              <Col span={12}><strong>位置：</strong>{currentEquipment.location}</Col>
              <Col span={12}>
                <strong>状态：</strong>
                <Tag color={statusMap[currentEquipment.status]?.color}>
                  {statusMap[currentEquipment.status]?.label}
                </Tag>
              </Col>
              <Col span={12}><strong>部门：</strong>{currentEquipment.department}</Col>
              <Col span={24}><strong>描述：</strong>{currentEquipment.description || '无'}</Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default EquipmentPage;
