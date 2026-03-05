import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Select,
  DatePicker,
  Input,
  message,
  Card,
  Typography,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  CalendarOutlined,
  CheckOutlined,
  CloseOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { reservationApi } from '@/api/reservation';
import { equipmentApi } from '@/api/equipment';
import { useAuthStore } from '@/store/authStore';
import type { Reservation, Equipment } from '@/types';
import dayjs from 'dayjs';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'gold', label: '待审批' },
  approved: { color: 'green', label: '已通过' },
  rejected: { color: 'red', label: '已拒绝' },
  cancelled: { color: 'default', label: '已取消' },
  completed: { color: 'blue', label: '已完成' },
};

const ReservationsPage: React.FC = () => {
  const [data, setData] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [modalVisible, setModalVisible] = useState(false);
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [currentId, setCurrentId] = useState<string>('');
  const [equipments, setEquipments] = useState<Equipment[]>([]);
  const [form] = Form.useForm();
  const [rejectForm] = Form.useForm();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin' || user?.role === 'manager';

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = isAdmin
        ? await reservationApi.getAll({ page, limit: pageSize })
        : await reservationApi.getMyReservations({ page, limit: pageSize });
      if (res.success) {
        setData(res.data || []);
        setTotal(res.meta?.total || 0);
      }
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, isAdmin]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async () => {
    try {
      const eqRes = await equipmentApi.getAll({ status: 'available', limit: 100 });
      setEquipments(eqRes.data || []);
    } catch { /* empty */ }
    form.resetFields();
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const [startTime, endTime] = values.timeRange;
      await reservationApi.create({
        equipment: values.equipment,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        purpose: values.purpose,
        notes: values.notes,
      });
      message.success('预约提交成功');
      setModalVisible(false);
      fetchData();
    } catch {
      // validation error
    }
  };

  const handleApprove = async (id: string) => {
    await reservationApi.updateStatus(id, { status: 'approved' });
    message.success('预约已通过');
    fetchData();
  };

  const handleReject = (id: string) => {
    setCurrentId(id);
    rejectForm.resetFields();
    setRejectModalVisible(true);
  };

  const submitReject = async () => {
    const values = await rejectForm.validateFields();
    await reservationApi.updateStatus(currentId, {
      status: 'rejected',
      rejectReason: values.rejectReason,
    });
    message.success('预约已拒绝');
    setRejectModalVisible(false);
    fetchData();
  };

  const handleCancel = async (id: string) => {
    await reservationApi.cancel(id);
    message.success('预约已取消');
    fetchData();
  };

  const columns = [
    {
      title: '设备',
      dataIndex: ['equipment', 'name'],
      key: 'equipment',
      width: 150,
    },
    {
      title: '申请人',
      dataIndex: ['user', 'displayName'],
      key: 'user',
      width: 100,
    },
    {
      title: '开始时间',
      dataIndex: 'startTime',
      key: 'startTime',
      width: 160,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '结束时间',
      dataIndex: 'endTime',
      key: 'endTime',
      width: 160,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '用途',
      dataIndex: 'purpose',
      key: 'purpose',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusMap[status]?.color}>{statusMap[status]?.label}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: Reservation) => (
        <Space>
          {isAdmin && record.status === 'pending' && (
            <>
              <Tooltip title="通过">
                <Button
                  type="link"
                  size="small"
                  icon={<CheckOutlined />}
                  onClick={() => handleApprove(record._id)}
                  style={{ color: '#52c41a' }}
                />
              </Tooltip>
              <Tooltip title="拒绝">
                <Button
                  type="link"
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={() => handleReject(record._id)}
                  danger
                />
              </Tooltip>
            </>
          )}
          {(record.status === 'pending' || record.status === 'approved') &&
            record.user?._id === user?._id && (
              <Popconfirm title="确认取消？" onConfirm={() => handleCancel(record._id)}>
                <Tooltip title="取消">
                  <Button type="link" size="small" icon={<StopOutlined />} />
                </Tooltip>
              </Popconfirm>
            )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4}>
        <CalendarOutlined style={{ marginRight: 8 }} />
        预约系统
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建预约
          </Button>
        </Space>
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
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
        scroll={{ x: 1000 }}
      />

      <Modal
        title="新建预约"
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="equipment" label="选择设备" rules={[{ required: true, message: '请选择设备' }]}>
            <Select
              showSearch
              placeholder="搜索并选择设备"
              optionFilterProp="label"
              options={equipments.map((e) => ({
                value: e._id,
                label: `${e.name} (${e.code}) - ${e.location}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="timeRange" label="预约时间" rules={[{ required: true, message: '请选择时间段' }]}>
            <RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="purpose" label="使用目的" rules={[{ required: true, message: '请输入使用目的' }]}>
            <Input.TextArea rows={3} maxLength={500} showCount />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="拒绝原因"
        open={rejectModalVisible}
        onOk={submitReject}
        onCancel={() => setRejectModalVisible(false)}
        destroyOnClose
      >
        <Form form={rejectForm} layout="vertical">
          <Form.Item name="rejectReason" label="原因" rules={[{ required: true, message: '请输入拒绝原因' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReservationsPage;
