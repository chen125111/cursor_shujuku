import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Card,
  Row,
  Col,
  Popconfirm,
  Typography,
  Tooltip,
  Statistic,
  Radio,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  InboxOutlined,
  ImportOutlined,
  ExportOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { inventoryApi } from '@/api/inventory';
import { useAuthStore } from '@/store/authStore';
import type { InventoryItem } from '@/types';

const { Title } = Typography;

const categoryMap: Record<string, string> = {
  reagent: '试剂',
  consumable: '耗材',
  glassware: '玻璃器具',
  instrument: '仪器',
  safety: '安全用品',
  other: '其他',
};

const InventoryPage: React.FC = () => {
  const [data, setData] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [usageModalVisible, setUsageModalVisible] = useState(false);
  const [currentItem, setCurrentItem] = useState<InventoryItem | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [form] = Form.useForm();
  const [usageForm] = Form.useForm();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin' || user?.role === 'manager';

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await inventoryApi.getAll({
        page,
        limit: pageSize,
        search: search || undefined,
        category: categoryFilter,
        lowStock: lowStockOnly ? 'true' : undefined,
      });
      if (res.success) {
        setData(res.data || []);
        setTotal(res.meta?.total || 0);
      }
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, categoryFilter, lowStockOnly]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await inventoryApi.getStatistics();
      if (res.success) setStats(res.data);
    } catch { /* empty */ }
  }, []);

  useEffect(() => { fetchData(); fetchStats(); }, [fetchData, fetchStats]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (currentItem) {
        await inventoryApi.update(currentItem._id, values);
        message.success('更新成功');
      } else {
        await inventoryApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchData();
      fetchStats();
    } catch { /* validation error */ }
  };

  const handleUsage = async () => {
    try {
      const values = await usageForm.validateFields();
      await inventoryApi.recordUsage(currentItem!._id, values);
      message.success(values.type === 'in' ? '入库成功' : '出库成功');
      setUsageModalVisible(false);
      fetchData();
      fetchStats();
    } catch { /* empty */ }
  };

  const columns = [
    { title: '编号', dataIndex: 'code', key: 'code', width: 110 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 150 },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (c: string) => categoryMap[c] || c,
    },
    { title: '规格', dataIndex: 'specifications', key: 'specs', width: 120, ellipsis: true },
    {
      title: '库存',
      key: 'quantity',
      width: 120,
      render: (_: unknown, record: InventoryItem) => (
        <Space>
          <span>{record.quantity} {record.unit}</span>
          {record.quantity <= record.minQuantity && (
            <Tag icon={<WarningOutlined />} color="error">不足</Tag>
          )}
        </Space>
      ),
    },
    { title: '位置', dataIndex: 'location', key: 'location', width: 100 },
    { title: '供应商', dataIndex: 'supplier', key: 'supplier', width: 120, ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: InventoryItem) => (
        <Space>
          <Tooltip title="出入库">
            <Button
              type="link"
              size="small"
              icon={<ImportOutlined />}
              onClick={() => {
                setCurrentItem(record);
                usageForm.resetFields();
                setUsageModalVisible(true);
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
                  onClick={() => {
                    setCurrentItem(record);
                    form.setFieldsValue(record);
                    setModalVisible(true);
                  }}
                />
              </Tooltip>
              <Popconfirm
                title="确认删除？"
                onConfirm={async () => {
                  await inventoryApi.delete(record._id);
                  message.success('删除成功');
                  fetchData();
                }}
              >
                <Tooltip title="删除">
                  <Button type="link" size="small" danger icon={<DeleteOutlined />} />
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
        <InboxOutlined style={{ marginRight: 8 }} />
        库存管理
      </Title>

      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}><Card><Statistic title="物品总数" value={stats.totalItems} /></Card></Col>
          <Col span={6}><Card><Statistic title="库存不足" value={stats.lowStockCount} valueStyle={stats.lowStockCount > 0 ? { color: '#ff4d4f' } : undefined} /></Card></Col>
          <Col span={6}><Card><Statistic title="总价值" value={stats.totalValue} prefix="¥" precision={2} /></Card></Col>
          <Col span={6}><Card><Statistic title="分类数" value={stats.categoryStats?.length || 0} /></Card></Col>
        </Row>
      )}

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="搜索名称或编号"
                prefix={<SearchOutlined />}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onPressEnter={() => { setPage(1); fetchData(); }}
                style={{ width: 220 }}
                allowClear
              />
              <Select
                placeholder="分类"
                allowClear
                style={{ width: 130 }}
                value={categoryFilter}
                onChange={(v) => { setCategoryFilter(v); setPage(1); }}
                options={Object.entries(categoryMap).map(([k, v]) => ({ value: k, label: v }))}
              />
              <Button
                type={lowStockOnly ? 'primary' : 'default'}
                icon={<WarningOutlined />}
                onClick={() => { setLowStockOnly(!lowStockOnly); setPage(1); }}
              >
                库存不足
              </Button>
            </Space>
          </Col>
          {isAdmin && (
            <Col>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => { setCurrentItem(null); form.resetFields(); setModalVisible(true); }}
              >
                添加物品
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
          current: page, pageSize, total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
        scroll={{ x: 1050 }}
      />

      <Modal
        title={currentItem ? '编辑物品' : '添加物品'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="code" label="编号" rules={[{ required: true }]}>
                <Input disabled={!!currentItem} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="分类" rules={[{ required: true }]}>
                <Select options={Object.entries(categoryMap).map(([k, v]) => ({ value: k, label: v }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="unit" label="单位" rules={[{ required: true }]}><Input placeholder="如：瓶、盒、个" /></Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="quantity" label="数量" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="minQuantity" label="最低库存" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="unitPrice" label="单价"><InputNumber style={{ width: '100%' }} min={0} prefix="¥" /></Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="location" label="存放位置" rules={[{ required: true }]}><Input /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="department" label="所属部门" rules={[{ required: true }]}><Input /></Form.Item>
            </Col>
          </Row>
          <Form.Item name="supplier" label="供应商"><Input /></Form.Item>
          <Form.Item name="specifications" label="规格"><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`出入库 - ${currentItem?.name}`}
        open={usageModalVisible}
        onOk={handleUsage}
        onCancel={() => setUsageModalVisible(false)}
        destroyOnClose
      >
        <Form form={usageForm} layout="vertical">
          <Form.Item name="type" label="类型" rules={[{ required: true }]} initialValue="out">
            <Radio.Group>
              <Radio.Button value="in"><ImportOutlined /> 入库</Radio.Button>
              <Radio.Button value="out"><ExportOutlined /> 出库</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item name="quantity" label="数量" rules={[{ required: true }]}>
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              addonAfter={currentItem?.unit}
            />
          </Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default InventoryPage;
