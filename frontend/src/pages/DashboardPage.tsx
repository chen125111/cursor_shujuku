import { Card, Col, List, Progress, Row, Space, Statistic, Tag, Typography } from "antd";
import dayjs from "dayjs";
import { useMemo } from "react";
import { useAppStore } from "../contexts/AppContext";

const EQUIPMENT_STATUS_TEXT: Record<string, string> = {
  available: "可用",
  in_use: "使用中",
  maintenance: "维护中",
  offline: "离线",
};

const RESERVATION_STATUS_COLOR: Record<string, string> = {
  pending: "gold",
  approved: "green",
  rejected: "red",
  cancelled: "default",
};

const RESERVATION_STATUS_TEXT: Record<string, string> = {
  pending: "待审核",
  approved: "已通过",
  rejected: "已拒绝",
  cancelled: "已取消",
};

export function DashboardPage() {
  const { equipments, reservations, inventoryItems, labs } = useAppStore();

  const lowStockCount = useMemo(
    () => inventoryItems.filter((item) => item.stock <= item.threshold).length,
    [inventoryItems],
  );
  const upcomingReservations = useMemo(
    () =>
      [...reservations]
        .sort((a, b) => dayjs(a.startTime).valueOf() - dayjs(b.startTime).valueOf())
        .slice(0, 5),
    [reservations],
  );

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="设备总数" value={equipments.length} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="实验室房间" value={labs.length} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="今日预约" value={reservations.length} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="库存预警" value={lowStockCount} valueStyle={{ color: lowStockCount ? "#cf1322" : "#3f8600" }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="设备状态监控">
            <List
              dataSource={equipments}
              renderItem={(eq) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <Space>
                        <Typography.Text>{eq.name}</Typography.Text>
                        <Tag>{EQUIPMENT_STATUS_TEXT[eq.status]}</Tag>
                      </Space>
                    }
                    description={`${eq.location} · 责任人 ${eq.responsible}`}
                  />
                  <Progress percent={eq.utilization} size="small" style={{ width: 120 }} />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="近期预约">
            <List
              dataSource={upcomingReservations}
              renderItem={(item) => {
                const lab = labs.find((l) => l.id === item.labId);
                return (
                  <List.Item>
                    <List.Item.Meta
                      title={`${lab?.name ?? "未知实验室"} · ${item.purpose}`}
                      description={`${dayjs(item.startTime).format("MM-DD HH:mm")} ~ ${dayjs(item.endTime).format("HH:mm")}`}
                    />
                    <Tag color={RESERVATION_STATUS_COLOR[item.status]}>
                      {RESERVATION_STATUS_TEXT[item.status]}
                    </Tag>
                  </List.Item>
                );
              }}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
