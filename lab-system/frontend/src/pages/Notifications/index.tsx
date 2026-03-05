import React, { useEffect, useState } from 'react';
import {
  List,
  Button,
  Tag,
  Space,
  Typography,
  Card,
  Empty,
  Spin,
  Segmented,
} from 'antd';
import {
  BellOutlined,
  CheckOutlined,
  CalendarOutlined,
  ExperimentOutlined,
  InboxOutlined,
  SoundOutlined,
} from '@ant-design/icons';
import { useNotificationStore } from '@/store/notificationStore';
import type { Notification, NotificationType } from '@/types';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Title, Text } = Typography;

const typeConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  reservation_approved: { icon: <CalendarOutlined />, color: 'green' },
  reservation_rejected: { icon: <CalendarOutlined />, color: 'red' },
  equipment_available: { icon: <ExperimentOutlined />, color: 'blue' },
  equipment_maintenance: { icon: <ExperimentOutlined />, color: 'orange' },
  inventory_low: { icon: <InboxOutlined />, color: 'volcano' },
  system_announcement: { icon: <SoundOutlined />, color: 'purple' },
};

const NotificationsPage: React.FC = () => {
  const {
    notifications,
    loading,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
  } = useNotificationStore();
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    fetchNotifications({ unreadOnly: filter === 'unread' ? 'true' : undefined });
  }, [fetchNotifications, filter]);

  const handleMarkAsRead = async (notification: Notification) => {
    if (!notification.isRead) {
      await markAsRead(notification._id);
    }
  };

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <BellOutlined style={{ marginRight: 8 }} />
          通知中心
        </Title>
        <Button icon={<CheckOutlined />} onClick={markAllAsRead}>
          全部标记已读
        </Button>
      </Space>

      <Card>
        <Segmented
          value={filter}
          onChange={(v) => setFilter(v as string)}
          options={[
            { value: 'all', label: '全部' },
            { value: 'unread', label: '未读' },
          ]}
          style={{ marginBottom: 16 }}
        />

        <Spin spinning={loading}>
          {notifications.length === 0 ? (
            <Empty description="暂无通知" />
          ) : (
            <List
              itemLayout="horizontal"
              dataSource={notifications}
              renderItem={(item) => {
                const cfg = typeConfig[item.type] || typeConfig.system_announcement;
                return (
                  <List.Item
                    onClick={() => handleMarkAsRead(item)}
                    style={{
                      cursor: 'pointer',
                      backgroundColor: item.isRead ? undefined : '#f6ffed',
                      padding: '12px 16px',
                      borderRadius: 8,
                      marginBottom: 4,
                    }}
                    actions={[
                      !item.isRead && (
                        <Tag color="blue" key="unread">未读</Tag>
                      ),
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      avatar={
                        <Tag color={cfg.color} style={{ margin: 0, padding: '4px 8px' }}>
                          {cfg.icon}
                        </Tag>
                      }
                      title={<Text strong={!item.isRead}>{item.title}</Text>}
                      description={
                        <Space direction="vertical" size={2}>
                          <Text type="secondary">{item.content}</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {dayjs(item.createdAt).fromNow()}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default NotificationsPage;
