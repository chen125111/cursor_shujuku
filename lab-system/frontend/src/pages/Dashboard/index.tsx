import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Typography, Space } from 'antd';
import {
  ExperimentOutlined,
  CalendarOutlined,
  InboxOutlined,
  TeamOutlined,
  ArrowUpOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/store/authStore';
import { equipmentApi } from '@/api/equipment';
import { reservationApi } from '@/api/reservation';
import { inventoryApi } from '@/api/inventory';

const { Title, Text } = Typography;

const statusColors: Record<string, string> = {
  pending: 'gold',
  approved: 'green',
  rejected: 'red',
  available: 'green',
  in_use: 'blue',
  maintenance: 'orange',
};

const statusLabels: Record<string, string> = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已拒绝',
  available: '可用',
  in_use: '使用中',
  maintenance: '维护中',
};

const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  const [stats, setStats] = useState({
    equipmentTotal: 0,
    reservationsPending: 0,
    inventoryLow: 0,
    userTotal: 0,
  });
  const [recentReservations, setRecentReservations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        const [equipRes, invRes, resRes] = await Promise.allSettled([
          equipmentApi.getStatistics(),
          inventoryApi.getStatistics(),
          reservationApi.getMyReservations({ limit: 5 }),
        ]);

        setStats({
          equipmentTotal:
            equipRes.status === 'fulfilled' ? (equipRes.value.data as any)?.total || 0 : 0,
          reservationsPending: 0,
          inventoryLow:
            invRes.status === 'fulfilled' ? (invRes.value.data as any)?.lowStockCount || 0 : 0,
          userTotal: 0,
        });

        if (resRes.status === 'fulfilled' && resRes.value.data) {
          setRecentReservations(resRes.value.data as any[]);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const columns = [
    {
      title: '设备',
      dataIndex: ['equipment', 'name'],
      key: 'equipment',
    },
    {
      title: '时间',
      dataIndex: 'startTime',
      key: 'startTime',
      render: (text: string) => new Date(text).toLocaleString('zh-CN'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status]}>
          {statusLabels[status] || status}
        </Tag>
      ),
    },
    {
      title: '用途',
      dataIndex: 'purpose',
      key: 'purpose',
      ellipsis: true,
    },
  ];

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={4}>
            <ClockCircleOutlined style={{ marginRight: 8 }} />
            欢迎回来，{user?.displayName || '用户'}
          </Title>
          <Text type="secondary">
            {new Date().toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              weekday: 'long',
            })}
          </Text>
        </div>

        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card hoverable>
              <Statistic
                title="设备总数"
                value={stats.equipmentTotal}
                prefix={<ExperimentOutlined />}
                valueStyle={{ color: '#1677ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card hoverable>
              <Statistic
                title="待审批预约"
                value={stats.reservationsPending}
                prefix={<CalendarOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card hoverable>
              <Statistic
                title="库存不足"
                value={stats.inventoryLow}
                prefix={<InboxOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
                suffix={
                  stats.inventoryLow > 0 ? (
                    <ArrowUpOutlined style={{ fontSize: 14 }} />
                  ) : null
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card hoverable>
              <Statistic
                title="用户数量"
                value={stats.userTotal}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>

        <Card title="我的最近预约" extra={<a href="/reservations">查看全部</a>}>
          <Table
            columns={columns}
            dataSource={recentReservations}
            rowKey="_id"
            pagination={false}
            loading={loading}
            locale={{ emptyText: '暂无预约记录' }}
          />
        </Card>
      </Space>
    </div>
  );
};

export default Dashboard;
