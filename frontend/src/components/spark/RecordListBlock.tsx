import { Card, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { SparkRecord } from "@/types/spark";

const statusColor: Record<string, string> = {
  success: "success",
  failed: "error",
  unsupported: "warning",
  skipped: "default",
  auth_expired: "error",
  no_target: "default",
};

interface RecordListBlockProps {
  records: SparkRecord[];
  loading?: boolean;
}

export default function RecordListBlock({ records, loading }: RecordListBlockProps) {
  const columns: ColumnsType<SparkRecord> = [
    { title: "日期", dataIndex: "execute_date", key: "execute_date", width: 120 },
    { title: "时间", dataIndex: "execute_time", key: "execute_time", width: 200 },
    { title: "对象", dataIndex: "target_nickname", key: "target_nickname", render: (v) => v || "-" },
    { title: "消息", dataIndex: "message", key: "message", ellipsis: true, render: (v) => v || "-" },
    { title: "通道", dataIndex: "channel", key: "channel", width: 140 },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (status) => <Tag color={statusColor[status] || "default"}>{status}</Tag>,
    },
    {
      title: "失败原因",
      dataIndex: "error_message",
      key: "error_message",
      ellipsis: true,
      render: (v) => v || "-",
    },
  ];

  return (
    <Card className="block-card" title="最近执行记录（7 天）">
      <Table rowKey="id" loading={loading} columns={columns} dataSource={records} pagination={{ pageSize: 10 }} />
    </Card>
  );
}
