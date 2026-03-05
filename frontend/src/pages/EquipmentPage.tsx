import {
  Button,
  Card,
  Col,
  DatePicker,
  Drawer,
  Form,
  Input,
  InputNumber,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { useAppStore } from "../contexts/AppContext";
import type { Equipment, MaintenanceRecord } from "../types";

const STATUS_TEXT: Record<Equipment["status"], string> = {
  available: "可用",
  in_use: "使用中",
  maintenance: "维护中",
  offline: "离线",
};

const STATUS_COLOR: Record<Equipment["status"], string> = {
  available: "green",
  in_use: "blue",
  maintenance: "orange",
  offline: "default",
};

export function EquipmentPage() {
  const {
    equipments,
    maintenanceRecords,
    currentUser,
    addEquipment,
    updateEquipmentStatus,
    addMaintenanceRecord,
  } = useAppStore();
  const [openAdd, setOpenAdd] = useState(false);
  const [selectedEquipmentId, setSelectedEquipmentId] = useState<string | null>(null);
  const [form] = Form.useForm();
  const [maintenanceForm] = Form.useForm();

  const selectedEquipment = useMemo(
    () => equipments.find((eq) => eq.id === selectedEquipmentId) ?? null,
    [equipments, selectedEquipmentId],
  );
  const selectedRecords = useMemo(
    () => maintenanceRecords.filter((record) => record.equipmentId === selectedEquipmentId),
    [maintenanceRecords, selectedEquipmentId],
  );

  const statusStats = useMemo(() => {
    const available = equipments.filter((eq) => eq.status === "available").length;
    const inUse = equipments.filter((eq) => eq.status === "in_use").length;
    const maintenance = equipments.filter((eq) => eq.status === "maintenance").length;
    return { available, inUse, maintenance };
  }, [equipments]);

  const equipmentColumns: ColumnsType<Equipment> = [
    { title: "设备名称", dataIndex: "name", key: "name", width: 170 },
    { title: "分类", dataIndex: "category", key: "category", width: 120 },
    { title: "位置", dataIndex: "location", key: "location", width: 120 },
    {
      title: "状态",
      key: "status",
      width: 150,
      render: (_, row) => (
        <Select<Equipment["status"]>
          value={row.status}
          style={{ width: 130 }}
          onChange={(value) => updateEquipmentStatus(row.id, value)}
        >
          <Select.Option value="available">可用</Select.Option>
          <Select.Option value="in_use">使用中</Select.Option>
          <Select.Option value="maintenance">维护中</Select.Option>
          <Select.Option value="offline">离线</Select.Option>
        </Select>
      ),
    },
    {
      title: "利用率",
      key: "utilization",
      width: 180,
      render: (_, row) => <Progress percent={row.utilization} size="small" />,
    },
    {
      title: "维护周期",
      key: "maintenance",
      width: 220,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text type="secondary">
            上次：{row.lastMaintenance ? dayjs(row.lastMaintenance).format("YYYY-MM-DD") : "-"}
          </Typography.Text>
          <Typography.Text type="secondary">
            下次：{row.nextMaintenance ? dayjs(row.nextMaintenance).format("YYYY-MM-DD") : "-"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 130,
      render: (_, row) => (
        <Button size="small" onClick={() => setSelectedEquipmentId(row.id)}>
          维护记录
        </Button>
      ),
    },
  ];

  const maintenanceColumns: ColumnsType<MaintenanceRecord> = [
    {
      title: "日期",
      dataIndex: "date",
      key: "date",
      render: (v: string) => dayjs(v).format("YYYY-MM-DD"),
    },
    { title: "类型", dataIndex: "type", key: "type" },
    { title: "技术员", dataIndex: "technician", key: "technician" },
    { title: "描述", dataIndex: "description", key: "description" },
    {
      title: "费用(元)",
      dataIndex: "cost",
      key: "cost",
      render: (v?: number) => (v ? v.toFixed(2) : "-"),
    },
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="可用设备" value={statusStats.available} suffix={`/ ${equipments.length}`} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="使用中" value={statusStats.inUse} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="维护中" value={statusStats.maintenance} />
          </Card>
        </Col>
      </Row>

      <Card
        title="设备列表与状态监控"
        extra={
          <Button type="primary" onClick={() => setOpenAdd(true)}>
            新增设备
          </Button>
        }
      >
        <Table
          rowKey="id"
          columns={equipmentColumns}
          dataSource={equipments}
          pagination={{ pageSize: 8 }}
          scroll={{ x: 900 }}
        />
      </Card>

      <Drawer
        title={selectedEquipment ? `${selectedEquipment.name} · 维护记录` : "维护记录"}
        width={760}
        open={Boolean(selectedEquipment)}
        onClose={() => setSelectedEquipmentId(null)}
      >
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Card size="small">
            <Form
              layout="vertical"
              form={maintenanceForm}
              onFinish={(vals) => {
                if (!selectedEquipment) {
                  return;
                }
                addMaintenanceRecord({
                  equipmentId: selectedEquipment.id,
                  date: vals.date.toISOString(),
                  type: vals.type,
                  description: vals.description,
                  technician: vals.technician,
                  cost: vals.cost,
                });
                updateEquipmentStatus(selectedEquipment.id, "available");
                message.success("维护记录已新增");
                maintenanceForm.resetFields();
              }}
            >
              <Row gutter={12}>
                <Col xs={24} md={12}>
                  <Form.Item name="date" label="维护日期" rules={[{ required: true, message: "请选择日期" }]}>
                    <DatePicker style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="type" label="维护类型" rules={[{ required: true, message: "请输入类型" }]}>
                    <Input placeholder="例行保养/故障维修" />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={12}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="technician"
                    label="技术员"
                    initialValue={currentUser?.name}
                    rules={[{ required: true, message: "请输入技术员" }]}
                  >
                    <Input />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="cost" label="费用">
                    <InputNumber min={0} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item name="description" label="维护说明" rules={[{ required: true, message: "请输入说明" }]}>
                <Input.TextArea rows={3} />
              </Form.Item>
              <Button type="primary" htmlType="submit">
                新增维护记录
              </Button>
            </Form>
          </Card>
          <Table
            rowKey="id"
            columns={maintenanceColumns}
            dataSource={selectedRecords}
            pagination={{ pageSize: 6 }}
            locale={{ emptyText: "暂无记录" }}
          />
        </Space>
      </Drawer>

      <Drawer
        title="新增设备"
        open={openAdd}
        onClose={() => setOpenAdd(false)}
        width={460}
        destroyOnClose
      >
        <Form
          layout="vertical"
          form={form}
          onFinish={(vals) => {
            addEquipment({
              name: vals.name,
              category: vals.category,
              location: vals.location,
              status: vals.status,
              utilization: vals.utilization,
              responsible: vals.responsible,
            });
            message.success("新增设备成功");
            form.resetFields();
            setOpenAdd(false);
          }}
          initialValues={{ status: "available", utilization: 30, responsible: currentUser?.name }}
        >
          <Form.Item label="设备名称" name="name" rules={[{ required: true, message: "请输入设备名称" }]}>
            <Input />
          </Form.Item>
          <Form.Item label="分类" name="category" rules={[{ required: true, message: "请输入分类" }]}>
            <Input />
          </Form.Item>
          <Form.Item label="位置" name="location" rules={[{ required: true, message: "请输入位置" }]}>
            <Input />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true, message: "请选择状态" }]}>
            <Select>
              {(Object.keys(STATUS_TEXT) as Equipment["status"][]).map((status) => (
                <Select.Option key={status} value={status}>
                  <Space>
                    <Tag color={STATUS_COLOR[status]}>{STATUS_TEXT[status]}</Tag>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="预计利用率(%)" name="utilization" rules={[{ required: true, message: "请输入利用率" }]}>
            <InputNumber min={0} max={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="责任人" name="responsible" rules={[{ required: true, message: "请输入责任人" }]}>
            <Input />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            保存
          </Button>
        </Form>
      </Drawer>
    </Space>
  );
}
