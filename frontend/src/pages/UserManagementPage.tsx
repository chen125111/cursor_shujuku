import {
  Card,
  Checkbox,
  Divider,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { PERMISSION_OPTIONS } from "../constants";
import { useAppStore } from "../contexts/AppContext";
import type { Role, User } from "../types";

const ROLE_TEXT: Record<Role, string> = {
  admin: "管理员",
  manager: "主管",
  user: "普通用户",
};

const ROLE_COLOR: Record<Role, string> = {
  admin: "red",
  manager: "gold",
  user: "blue",
};

export function UserManagementPage() {
  const {
    users,
    rolePermissions,
    currentUser,
    updateRolePermissions,
    updateUserRole,
    updateUserStatus,
  } = useAppStore();

  const editable = currentUser?.role === "admin";

  const columns: ColumnsType<User> = [
    {
      title: "姓名",
      dataIndex: "name",
      key: "name",
      width: 120,
    },
    {
      title: "邮箱",
      dataIndex: "email",
      key: "email",
      width: 200,
    },
    {
      title: "角色",
      key: "role",
      width: 180,
      render: (_, record) =>
        editable ? (
          <Select<Role> value={record.role} style={{ width: 130 }} onChange={(v) => updateUserRole(record.id, v)}>
            <Select.Option value="admin">管理员</Select.Option>
            <Select.Option value="manager">主管</Select.Option>
            <Select.Option value="user">普通用户</Select.Option>
          </Select>
        ) : (
          <Tag color={ROLE_COLOR[record.role]}>{ROLE_TEXT[record.role]}</Tag>
        ),
    },
    {
      title: "状态",
      key: "status",
      width: 140,
      render: (_, record) => (
        <Space>
          <Switch
            checked={record.status === "active"}
            checkedChildren="启用"
            unCheckedChildren="禁用"
            disabled={!editable || record.id === currentUser?.id}
            onChange={(checked) => updateUserStatus(record.id, checked ? "active" : "disabled")}
          />
        </Space>
      ),
    },
    {
      title: "创建时间",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 180,
      render: (val: string) => dayjs(val).format("YYYY-MM-DD HH:mm"),
    },
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Card
        title="用户列表"
        extra={
          <Typography.Text type={editable ? "success" : "secondary"}>
            {editable ? "你当前拥有用户与权限管理权限" : "当前账号仅可查看，管理员可编辑"}
          </Typography.Text>
        }
      >
        <Table rowKey="id" columns={columns} dataSource={users} scroll={{ x: 800 }} pagination={{ pageSize: 8 }} />
      </Card>

      <Card title="角色权限管理">
        {(["admin", "manager", "user"] as Role[]).map((role, index) => (
          <div key={role}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Space align="center">
                <Tag color={ROLE_COLOR[role]}>{ROLE_TEXT[role]}</Tag>
                <Typography.Text type="secondary">
                  已配置 {rolePermissions[role].length} 项权限
                </Typography.Text>
              </Space>
              <Checkbox.Group
                style={{ width: "100%" }}
                value={rolePermissions[role]}
                disabled={!editable}
                onChange={(vals) => {
                  updateRolePermissions(role, vals as string[]);
                  message.success(`${ROLE_TEXT[role]}权限已更新`);
                }}
              >
                <Space direction="vertical" size={6}>
                  {PERMISSION_OPTIONS.map((permission) => (
                    <Checkbox value={permission} key={permission}>
                      {permission}
                    </Checkbox>
                  ))}
                </Space>
              </Checkbox.Group>
            </Space>
            {index < 2 ? <Divider /> : null}
          </div>
        ))}
      </Card>
    </Space>
  );
}
