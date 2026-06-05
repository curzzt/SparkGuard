import { Card, Descriptions, Tag } from "antd";
import type { TodayStatus } from "@/types/spark";

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: "default", label: "待执行" },
  running: { color: "processing", label: "执行中" },
  completed: { color: "success", label: "已完成" },
  partial: { color: "warning", label: "部分完成" },
  skipped: { color: "default", label: "已跳过" },
};

interface TodayStatusBlockProps {
  status?: TodayStatus;
  loading?: boolean;
}

export default function TodayStatusBlock({ status, loading }: TodayStatusBlockProps) {
  const jobStatus = status?.job_status || "pending";
  const meta = statusMap[jobStatus] || statusMap.pending;

  return (
    <Card className="block-card" title="今日执行状态" loading={loading}>
      <Descriptions column={2}>
        <Descriptions.Item label="目标">{status?.target_count ?? 0}</Descriptions.Item>
        <Descriptions.Item label="成功">{status?.success_count ?? 0}</Descriptions.Item>
        <Descriptions.Item label="失败">{status?.failed_count ?? 0}</Descriptions.Item>
        <Descriptions.Item label="不支持">{status?.unsupported_count ?? 0}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={meta.color}>{meta.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="最近执行">{status?.last_execute_at || "-"}</Descriptions.Item>
      </Descriptions>
    </Card>
  );
}
