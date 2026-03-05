import {
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { useAppStore } from "../contexts/AppContext";
import type { Reservation } from "../types";

const RESERVATION_STATUS_TEXT: Record<Reservation["status"], string> = {
  pending: "待审核",
  approved: "已通过",
  rejected: "已拒绝",
  cancelled: "已取消",
};
const RESERVATION_STATUS_COLOR: Record<Reservation["status"], string> = {
  pending: "gold",
  approved: "green",
  rejected: "red",
  cancelled: "default",
};

interface ReservationRow extends Reservation {
  labName: string;
  applicant: string;
}

export function ReservationPage() {
  const {
    currentUser,
    users,
    labs,
    reservations,
    createReservation,
    updateReservationStatus,
  } = useAppStore();
  const [form] = Form.useForm();
  const [conflictOpen, setConflictOpen] = useState(false);
  const [conflictContent, setConflictContent] = useState<string[]>([]);

  const rows = useMemo<ReservationRow[]>(
    () =>
      reservations.map((r) => ({
        ...r,
        labName: labs.find((l) => l.id === r.labId)?.name ?? "未知实验室",
        applicant: users.find((u) => u.id === r.userId)?.name ?? "未知用户",
      })),
    [reservations, labs, users],
  );

  const myReservations = useMemo(
    () => rows.filter((row) => (currentUser?.role === "admin" ? true : row.userId === currentUser?.id)),
    [rows, currentUser],
  );

  const pendingCount = rows.filter((item) => item.status === "pending").length;
  const approvedCount = rows.filter((item) => item.status === "approved").length;

  const columns: ColumnsType<ReservationRow> = [
    { title: "实验室", dataIndex: "labName", key: "labName", width: 140 },
    { title: "申请人", dataIndex: "applicant", key: "applicant", width: 120 },
    { title: "用途", dataIndex: "purpose", key: "purpose", width: 200 },
    {
      title: "预约时间",
      key: "time",
      width: 230,
      render: (_, row) =>
        `${dayjs(row.startTime).format("MM-DD HH:mm")} ~ ${dayjs(row.endTime).format("MM-DD HH:mm")}`,
    },
    {
      title: "状态",
      key: "status",
      width: 100,
      render: (_, row) => (
        <Tag color={RESERVATION_STATUS_COLOR[row.status]}>{RESERVATION_STATUS_TEXT[row.status]}</Tag>
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 210,
      render: (_, row) => {
        const canApprove = currentUser?.role === "admin" || currentUser?.role === "manager";
        if (row.status !== "pending") {
          return "-";
        }
        return (
          <Space>
            <Button
              size="small"
              type="primary"
              disabled={!canApprove}
              onClick={() => {
                updateReservationStatus(row.id, "approved");
                message.success("预约已通过");
              }}
            >
              通过
            </Button>
            <Button
              size="small"
              danger
              disabled={!canApprove}
              onClick={() => {
                updateReservationStatus(row.id, "rejected");
                message.warning("预约已拒绝");
              }}
            >
              拒绝
            </Button>
            {row.userId === currentUser?.id ? (
              <Button
                size="small"
                onClick={() => {
                  updateReservationStatus(row.id, "cancelled");
                }}
              >
                取消
              </Button>
            ) : null}
          </Space>
        );
      },
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }} size="middle">
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Typography.Text type="secondary">待审核预约</Typography.Text>
            <Typography.Title level={3} style={{ margin: 0 }}>
              {pendingCount}
            </Typography.Title>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Typography.Text type="secondary">已通过预约</Typography.Text>
            <Typography.Title level={3} style={{ margin: 0 }}>
              {approvedCount}
            </Typography.Title>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Typography.Text type="secondary">可预约实验室</Typography.Text>
            <Typography.Title level={3} style={{ margin: 0 }}>
              {labs.length}
            </Typography.Title>
          </Card>
        </Col>
      </Row>

      <Card title="发起实验室预约">
        <Form
          layout="vertical"
          form={form}
          onFinish={(vals) => {
            const result = createReservation({
              labId: vals.labId,
              purpose: vals.purpose,
              startTime: vals.timeRange[0].toISOString(),
              endTime: vals.timeRange[1].toISOString(),
            });
            if (result.ok) {
              message.success("预约提交成功，等待审核");
              form.resetFields();
              return;
            }

            if (result.conflicts && result.conflicts.length > 0) {
              setConflictContent(
                result.conflicts.map((item) => {
                  const time = `${dayjs(item.reservation.startTime).format("MM-DD HH:mm")}~${dayjs(
                    item.reservation.endTime,
                  ).format("HH:mm")}`;
                  return `${item.lab?.name ?? "未知实验室"} · ${time} · 申请人 ${item.user?.name ?? "未知"}`;
                }),
              );
              setConflictOpen(true);
            }
            message.error(result.message);
          }}
        >
          <Row gutter={12}>
            <Col xs={24} md={8}>
              <Form.Item label="实验室" name="labId" rules={[{ required: true, message: "请选择实验室" }]}>
                <Select placeholder="请选择">
                  {labs.map((lab) => (
                    <Select.Option key={lab.id} value={lab.id}>
                      {lab.name} ({lab.location})
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={10}>
              <Form.Item
                label="预约时间"
                name="timeRange"
                rules={[{ required: true, message: "请选择时间范围" }]}
              >
                <DatePicker.RangePicker showTime style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item label="&nbsp;">
                <Button htmlType="submit" type="primary" block>
                  提交预约
                </Button>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="用途说明" name="purpose" rules={[{ required: true, message: "请填写用途说明" }]}>
            <Input.TextArea rows={3} placeholder="例如：样品测试、课程实验、设备标定等" />
          </Form.Item>
        </Form>
      </Card>

      <Card title="预约列表（含时间管理）">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={myReservations}
          scroll={{ x: 1100 }}
          pagination={{ pageSize: 8 }}
        />
      </Card>

      <Modal
        title="检测到时间冲突"
        open={conflictOpen}
        onCancel={() => setConflictOpen(false)}
        onOk={() => setConflictOpen(false)}
      >
        <Typography.Paragraph>
          以下时段已被占用，请调整预约时间后重试：
        </Typography.Paragraph>
        <ul>
          {conflictContent.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </Modal>
    </Space>
  );
}
