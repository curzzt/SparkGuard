import { useState } from "react";
import { Button, Card, Popconfirm, Space, Switch, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { batchDisableTargets, createTarget, deleteTarget, updateTarget } from "@/api/spark";
import type { SparkTarget } from "@/types/spark";
import TargetFormModal from "./TargetFormModal";
import RecentContactsImportModal from "./RecentContactsImportModal";

interface TargetListBlockProps {
  targets: SparkTarget[];
  loading?: boolean;
  accountBound?: boolean;
  onChanged: () => void;
  onBatchEnable: (ids: number[]) => Promise<unknown>;
}

const statusColor: Record<string, string> = {
  success: "success",
  failed: "error",
  unsupported: "warning",
  pending: "default",
};

export default function TargetListBlock({ targets, loading, accountBound, onChanged, onBatchEnable }: TargetListBlockProps) {
  const [selected, setSelected] = useState<number[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [editing, setEditing] = useState<SparkTarget | null>(null);

  const columns: ColumnsType<SparkTarget> = [
    { title: "昵称", dataIndex: "nickname", key: "nickname" },
    { title: "备注", dataIndex: "remark", key: "remark", render: (v) => v || "-" },
    { title: "接收方 ID", dataIndex: "receiver_id", key: "receiver_id" },
    {
      title: "模板",
      dataIndex: "custom_template",
      key: "custom_template",
      ellipsis: true,
      render: (v) => v || "-",
    },
    {
      title: "启用",
      dataIndex: "enabled",
      key: "enabled",
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          onChange={async (checked) => {
            try {
              await updateTarget(record.id, { enabled: checked });
              onChanged();
            } catch (e) {
              message.error(e instanceof Error ? e.message : "更新失败");
            }
          }}
        />
      ),
    },
    {
      title: "今日",
      key: "today",
      render: (_, record) =>
        record.last_status ? <Tag color={statusColor[record.last_status] || "default"}>{record.last_status}</Tag> : "-",
    },
    {
      title: "操作",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            onClick={() => {
              setEditing(record);
              setModalOpen(true);
            }}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除？"
            onConfirm={async () => {
              try {
                await deleteTarget(record.id);
                message.success("已删除");
                onChanged();
              } catch (e) {
                message.error(e instanceof Error ? e.message : "删除失败");
              }
            }}
          >
            <Button type="link" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleSubmit = async (values: Partial<SparkTarget>) => {
    try {
      if (editing) {
        await updateTarget(editing.id, values);
        message.success("已更新");
      } else {
        await createTarget(values);
        message.success("已创建");
      }
      setModalOpen(false);
      setEditing(null);
      onChanged();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存失败");
    }
  };

  const handleBatchEnable = async () => {
    if (!selected.length) {
      message.warning("请先选择对象");
      return;
    }
    try {
      await onBatchEnable(selected);
      message.success("已批量启用");
      setSelected([]);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  const handleBatchDisable = async () => {
    if (!selected.length) {
      message.warning("请先选择对象");
      return;
    }
    try {
      await batchDisableTargets(selected);
      message.success("已批量停用");
      setSelected([]);
      onChanged();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  return (
    <Card
      className="block-card"
      title="续火花对象列表"
      extra={
        <Space>
          <Button disabled={!accountBound} onClick={() => setImportOpen(true)}>
            导入最近好友
          </Button>
          <Button
            onClick={() => {
              setEditing(null);
              setModalOpen(true);
            }}
          >
            新增
          </Button>
          <Button onClick={handleBatchEnable}>批量启用</Button>
          <Button onClick={handleBatchDisable}>批量停用</Button>
        </Space>
      }
    >
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={targets}
        rowSelection={{
          selectedRowKeys: selected,
          onChange: (keys) => setSelected(keys as number[]),
        }}
        pagination={false}
        expandable={{
          expandedRowRender: (record) => (
            <div>
              <div>最近执行：{record.last_run_at || "-"}</div>
              <div>最近失败原因：{record.last_error || "-"}</div>
            </div>
          ),
        }}
      />
      <RecentContactsImportModal
        open={importOpen}
        existingTargets={targets}
        onCancel={() => setImportOpen(false)}
        onImported={() => {
          setImportOpen(false);
          onChanged();
        }}
      />
      <TargetFormModal
        open={modalOpen}
        initial={editing}
        onCancel={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        onSubmit={handleSubmit}
      />
    </Card>
  );
}
