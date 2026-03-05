import {
  AppstoreOutlined,
  CalendarOutlined,
  DashboardOutlined,
  LogoutOutlined,
  MenuOutlined,
  SettingOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Avatar, Button, Drawer, Grid, Layout, Menu, Space, Typography } from "antd";
import type { MenuProps } from "antd";
import { useMemo, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAppStore } from "../contexts/AppContext";

const { Header, Sider, Content } = Layout;

type MenuItem = Required<MenuProps>["items"][number];

const menuItems: MenuItem[] = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: <Link to="/dashboard">概览</Link> },
  { key: "/users", icon: <TeamOutlined />, label: <Link to="/users">用户管理</Link> },
  { key: "/equipments", icon: <SettingOutlined />, label: <Link to="/equipments">设备管理</Link> },
  { key: "/reservations", icon: <CalendarOutlined />, label: <Link to="/reservations">预约系统</Link> },
  { key: "/inventory", icon: <AppstoreOutlined />, label: <Link to="/inventory">库存管理</Link> },
];

export function AppLayout() {
  const { currentUser, logout } = useAppStore();
  const location = useLocation();
  const navigate = useNavigate();
  const screens = Grid.useBreakpoint();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const selectedKeys = useMemo(() => {
    const target = menuItems
      .map((item) => item?.key as string)
      .find((key) => location.pathname.startsWith(key));
    return [target ?? "/dashboard"];
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {screens.md ? (
        <Sider width={230} theme="light" breakpoint="md">
          <div className="logo-title">实验室管理系统</div>
          <Menu mode="inline" items={menuItems} selectedKeys={selectedKeys} style={{ borderInlineEnd: "none" }} />
        </Sider>
      ) : null}

      <Layout>
        <Header className="app-header">
          <Space>
            {!screens.md ? (
              <Button
                icon={<MenuOutlined />}
                onClick={() => setMobileMenuOpen(true)}
                aria-label="打开菜单"
              />
            ) : null}
            <Typography.Title level={5} style={{ margin: 0 }}>
              {currentUser?.role === "admin" ? "管理员控制台" : "实验室业务台"}
            </Typography.Title>
          </Space>

          <Space>
            <Avatar>{currentUser?.name.slice(0, 1)}</Avatar>
            <Typography.Text>{currentUser?.name}</Typography.Text>
            <Button icon={<LogoutOutlined />} onClick={handleLogout}>
              退出
            </Button>
          </Space>
        </Header>

        <Content style={{ padding: 16 }}>
          <Outlet />
        </Content>
      </Layout>

      <Drawer
        title="菜单"
        placement="left"
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        styles={{ body: { padding: 0 } }}
      >
        <Menu
          mode="inline"
          items={menuItems}
          selectedKeys={selectedKeys}
          onClick={() => setMobileMenuOpen(false)}
        />
      </Drawer>
    </Layout>
  );
}
