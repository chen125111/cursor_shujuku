import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Form,
  Input,
  Button,
  Card,
  Typography,
  Space,
  Tabs,
  Select,
  message,
  theme,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/store/authStore';

const { Title, Text } = Typography;

const departments = [
  '化学工程系', '材料科学系', '生物工程系', '环境科学系',
  '物理学系', '计算机科学系', '电子工程系', '机械工程系',
];

const LoginPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('login');
  const navigate = useNavigate();
  const { login, register, loading } = useAuthStore();
  const { token } = theme.useToken();

  const handleLogin = async (values: { email: string; password: string }) => {
    try {
      await login(values.email, values.password);
      message.success('登录成功');
      navigate('/dashboard');
    } catch {
      message.error('登录失败，请检查邮箱和密码');
    }
  };

  const handleRegister = async (values: {
    username: string;
    email: string;
    password: string;
    displayName: string;
    department: string;
  }) => {
    try {
      await register(values);
      message.success('注册成功');
      navigate('/dashboard');
    } catch {
      message.error('注册失败，请稍后再试');
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg, ${token.colorPrimaryBg} 0%, ${token.colorBgLayout} 100%)`,
      }}
    >
      <Card
        style={{
          width: 460,
          boxShadow: token.boxShadowTertiary,
          borderRadius: token.borderRadiusLG,
        }}
      >
        <Space
          direction="vertical"
          align="center"
          style={{ width: '100%', marginBottom: 24 }}
        >
          <ExperimentOutlined
            style={{ fontSize: 48, color: token.colorPrimary }}
          />
          <Title level={3} style={{ margin: 0 }}>
            实验室管理系统
          </Title>
          <Text type="secondary">Laboratory Management System</Text>
        </Space>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          centered
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form layout="vertical" onFinish={handleLogin} size="large">
                  <Form.Item
                    name="email"
                    rules={[
                      { required: true, message: '请输入邮箱' },
                      { type: 'email', message: '请输入有效的邮箱' },
                    ]}
                  >
                    <Input prefix={<MailOutlined />} placeholder="邮箱地址" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[{ required: true, message: '请输入密码' }]}
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="密码"
                    />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      block
                      loading={loading}
                    >
                      登 录
                    </Button>
                  </Form.Item>
                  <div style={{ textAlign: 'center' }}>
                    <Link to="#" onClick={() => setActiveTab('register')}>
                      还没有账号？立即注册
                    </Link>
                  </div>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form layout="vertical" onFinish={handleRegister} size="large">
                  <Form.Item
                    name="username"
                    rules={[
                      { required: true, message: '请输入用户名' },
                      { min: 3, message: '用户名至少3个字符' },
                    ]}
                  >
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item
                    name="email"
                    rules={[
                      { required: true, message: '请输入邮箱' },
                      { type: 'email', message: '请输入有效的邮箱' },
                    ]}
                  >
                    <Input prefix={<MailOutlined />} placeholder="邮箱地址" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[
                      { required: true, message: '请输入密码' },
                      { min: 6, message: '密码至少6个字符' },
                    ]}
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="密码"
                    />
                  </Form.Item>
                  <Form.Item
                    name="displayName"
                    rules={[{ required: true, message: '请输入姓名' }]}
                  >
                    <Input placeholder="姓名" />
                  </Form.Item>
                  <Form.Item
                    name="department"
                    rules={[{ required: true, message: '请选择部门' }]}
                  >
                    <Select placeholder="选择部门">
                      {departments.map((dept) => (
                        <Select.Option key={dept} value={dept}>
                          {dept}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      block
                      loading={loading}
                    >
                      注 册
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default LoginPage;
