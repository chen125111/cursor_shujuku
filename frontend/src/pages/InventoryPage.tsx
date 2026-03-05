import {
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
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
import type { InventoryItem, InventoryLog } from "../types";

interface MovementFormValues {
  itemId: string;
  type: "in" | "out";
  quantity: number;
  remark?: string;
}

export function InventoryPage() {
  const { inventoryItems, inventoryLogs, addInventoryItem, stockMovement } = useAppStore();
  const [itemForm] = Form.useForm();
  const [movementForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  const lowStockItems = useMemo(
    () => inventoryItems.filter((item) => item.stock <= item.threshold),
    [inventoryItems],
  );
  const totalStock = useMemo(
    () => inventoryItems.reduce((sum, item) => sum + item.stock, 0),
    [inventoryItems],
  );

  const itemColumns: ColumnsType<InventoryItem> = [
    { title: "物品名称", dataIndex: "name", key: "name", width: 160 },
    { title: "分类", dataIndex: "category", key: "category", width: 120 },
    { title: "库位", dataIndex: "location", key: "location", width: 120 },
    {
      title: "库存",
      key: "stock",
      width: 180,
      render: (_, row) => (
        <Space>
          <Typography.Text strong={row.stock <= row.threshold}>{`${row.stock} ${row.unit}`}</Typography.Text>
          {row.stock <= row.threshold ? <Tag color="red">预警</Tag> : <Tag color="green">正常</Tag>}
        </Space>
      ),
    },
    {
      title: "阈值",
      key: "threshold",
      width: 120,
      render: (_, row) => `${row.threshold} ${row.unit}`,
    },
    {
      title: "更新时间",
      dataIndex: "lastUpdated",
      key: "lastUpdated",
      width: 170,
      render: (val: string) => dayjs(val).format("YYYY-MM-DD HH:mm"),
    },
  ];

  const logColumns: ColumnsType<InventoryLog> = [
    {
      title: "时间",
      dataIndex: "time",
      key: "time",
      width: 180,
      render: (val: string) => dayjs(val).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "物品",
      key: "item",
      width: 160,
      render: (_, row) => inventoryItems.find((item) => item.id === row.itemId)?.name ?? "未知物品",
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 100,
      render: (type: "in" | "out") => <Tag color={type === "in" ? "green" : "orange"}>{type === "in" ? "入库" : "出库"}</Tag>,
    },
    { title: "数量", dataIndex: "quantity", key: "quantity", width: 100 },
    { title: "操作人", dataIndex: "operator", key: "operator", width: 120 },
    { title: "备注", dataIndex: "remark", key: "remark", width: 200 },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }} size="middle">
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="库存品类" value={inventoryItems.length} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="总库存数量" value={totalStock} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="库存预警项" value={lowStockItems.length} valueStyle={{ color: lowStockItems.length ? "#cf1322" : "#3f8600" }} />
          </Card>
        </Col>
      </Row>

      <Card title="物品入库 / 出库">
        <Form
          form={movementForm}
          layout="vertical"
          onFinish={(values: MovementFormValues) => {
            const result = stockMovement(values);
            if (!result.ok) {
              message.error(result.message);
              return;
            }
            message.success(values.type === "in" ? "入库成功" : "出库成功");
            movementForm.resetFields();
          }}
          initialValues={{ type: "in", quantity: 1 }}
        >
          <Row gutter={12}>
            <Col xs={24} md={8}>
              <Form.Item label="物品" name="itemId" rules={[{ required: true, message: "请选择物品" }]}>
                <Select placeholder="请选择物品">
                  {inventoryItems.map((item) => (
                    <Select.Option key={item.id} value={item.id}>
                      {item.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item label="类型" name="type" rules={[{ required: true, message: "请选择类型" }]}>
                <Select>
                  <Select.Option value="in">入库</Select.Option>
                  <Select.Option value="out">出库</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item label="数量" name="quantity" rules={[{ required: true, message: "请输入数量" }]}>
                <InputNumber min={1} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={4}>
              <Form.Item label="&nbsp;">
                <Button type="primary" htmlType="submit" block>
                  提交
                </Button>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="备注" name="remark">
            <Input />
          </Form.Item>
        </Form>
      </Card>

      <Card title="新增库存物品" extra={<Button onClick={() => setCreating((v) => !v)}>{creating ? "收起" : "展开"}</Button>}>
        {creating ? (
          <Form
            form={itemForm}
            layout="vertical"
            onFinish={(values) => {
              addInventoryItem({
                name: values.name,
                category: values.category,
                unit: values.unit,
                threshold: values.threshold,
                location: values.location,
                stock: values.stock,
              });
              message.success("新增库存物品成功");
              itemForm.resetFields();
              setCreating(false);
            }}
            initialValues={{ stock: 0, threshold: 10 }}
          >
            <Row gutter={12}>
              <Col xs={24} md={12}>
                <Form.Item label="名称" name="name" rules={[{ required: true, message: "请输入名称" }]}>
                  <Input />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="分类" name="category" rules={[{ required: true, message: "请输入分类" }]}>
                  <Input />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={12}>
              <Col xs={24} md={8}>
                <Form.Item label="单位" name="unit" rules={[{ required: true, message: "请输入单位" }]}>
                  <Input />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="初始库存" name="stock" rules={[{ required: true, message: "请输入库存" }]}>
                  <InputNumber min={0} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="预警阈值" name="threshold" rules={[{ required: true, message: "请输入阈值" }]}>
                  <InputNumber min={0} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="库位" name="location" rules={[{ required: true, message: "请输入库位" }]}>
              <Input />
            </Form.Item>
            <Button type="primary" htmlType="submit">
              保存物品
            </Button>
          </Form>
        ) : (
          <Typography.Text type="secondary">点击“展开”可新增库存条目。</Typography.Text>
        )}
      </Card>

      <Card title="库存列表（含预警）">
        <Table
          rowKey="id"
          columns={itemColumns}
          dataSource={inventoryItems}
          scroll={{ x: 900 }}
          pagination={{ pageSize: 8 }}
        />
      </Card>

      <Card title="出入库记录">
        <Table
          rowKey="id"
          columns={logColumns}
          dataSource={inventoryLogs}
          scroll={{ x: 950 }}
          pagination={{ pageSize: 8 }}
        />
      </Card>
    </Space>
  );
}
