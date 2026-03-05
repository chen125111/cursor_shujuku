import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Card,
  Row,
  Col,
  Typography,
  Avatar,
  Switch,
  message,
  Tooltip,
} from 'antd';
import {
  SearchOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { userApi } from '@/api/user';
import { useAuthStore } from '@/store/authStore';
import type { User } from '@/types';

const { Title } = Typography;

const roleMap: Record<string, { color: string; label: string }> = {
  admin: { color: 'red', label: '管理员' },
  manager: { color: 'orange', label: '实验室主任' },
  researcher: { color: 'blue', label: '研究员' },
  student: { color: 'green', label: '学生' },
};

const UsersPage: React.FC = () => {
  const [data, setData] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string | undefined>();
  const { user: currentUser } = useAuthStore();
  const isAdmin = currentUser?.role === 'admin';

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await userApi.getAll({
        page,
        limit: pageSize,
        search: search || undefined,
        role: roleFilter,
      });
      if (res.success) {
        setData(res.data || []);
        setTotal(res.meta?.total || 0);
      }
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, roleFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleToggleActive = async (id: string) => {
    await userApi.toggleActive(id);
    message.success('状态已更新');
    fetchData();
  };

  const handleRoleChange = async (id: string, role: string) => {
    await userApi.updateRole(id, role);
    message.success('角色已更新');
    fetchData();
  };

  const columns = [
    {
      title: '用户',
      key: 'user',
      width: 220,
      render: (_: unknown, record: User) => (
        <Space>
          <Avatar src={record.avatar} icon={<UserOutlined />} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.displayName}</div>
            <div style={{ fontSize: 12, color: '#999' }}>{record.email}</div>
          </div>
        </Space>
      ),
    },
    { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
    { title: '部门', dataIndex: 'department', key: 'department', width: 130 },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role: string, record: User) =>
        isAdmin && record._id !== currentUser?._id ? (
          <Select
            size="small"
            value={role}
            style={{ width: 120 }}
            onChange={(v) => handleRoleChange(record._id, v)}
            options={Object.entries(roleMap).map(([k, v]) => ({ value: k, label: v.label }))}
          />
        ) : (
          <Tag color={roleMap[role]?.color}>{roleMap[role]?.label}</Tag>
        ),
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      width: 100,
      render: (active: boolean, record: User) =>
        isAdmin && record._id !== currentUser?._id ? (
          <Switch
            checked={active}
            onChange={() => handleToggleActive(record._id)}
            checkedChildren="启用"
            unCheckedChildren="禁用"
          />
        ) : (
          <Tag color={active ? 'green' : 'default'}>{active ? '活跃' : '已禁用'}</Tag>
        ),
    },
    {
      title: '最后登录',
      dataIndex: 'lastLoginAt',
      key: 'lastLoginAt',
      width: 160,
      render: (t: string) => (t ? new Date(t).toLocaleString('zh-CN') : '从未登录'),
    },
  ];

  return (
    <div>
      <Title level={4}>
        <TeamOutlined style={{ marginRight: 8 }} />
        用户管理
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="搜索用户名、姓名或邮箱"
                prefix={<SearchOutlined />}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onPressEnter={() => { setPage(1); fetchData(); }}
                style={{ width: 280 }}
                allowClear
              />
              <Select
                placeholder="角色筛选"
                allowClear
                style={{ width: 140 }}
                value={roleFilter}
                onChange={(v) => { setRoleFilter(v); setPage(1); }}
                options={Object.entries(roleMap).map(([k, v]) => ({ value: k, label: v.label }))}
              />
            </Space>
          </Col>
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
        scroll={{ x: 900 }}
      />
    </div>
  );
};

export default UsersPage;
