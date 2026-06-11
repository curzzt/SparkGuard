import { useEffect, useMemo, useState } from "react";
import { Button, Modal, Table, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { getDouyinRecentContacts } from "@/api/douyin";
import { createTarget } from "@/api/spark";
import type { DouyinRecentContact } from "@/types/douyin";
import type { SparkTarget } from "@/types/spark";

interface RecentContactsImportModalProps {
  open: boolean;
  existingTargets: SparkTarget[];
  onCancel: () => void;
  onImported: () => void;
}

export default function RecentContactsImportModal({
  open,
  existingTargets,
  onCancel,
  onImported,
}: RecentContactsImportModalProps) {
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [contacts, setContacts] = useState<DouyinRecentContact[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  const existingLabels = useMemo(() => {
    const set = new Set<string>();
    for (const t of existingTargets) {
      const rid = (t.receiver_id || "").trim();
      const nick = (t.nickname || "").trim();
      if (rid) set.add(rid);
      if (nick) set.add(nick);
    }
    return set;
  }, [existingTargets]);

  const fetchContacts = async () => {
    setLoading(true);
    try {
      const data = await getDouyinRecentContacts(10);
      setContacts(data.items);
      const selectable = data.items
        .map((c) => c.display_name)
        .filter((name) => !existingLabels.has(name));
      setSelected(selectable);
      if (!data.items.length) {
        message.warning("未获取到最近联系人");
      }
    } catch (e) {
      message.error(e instanceof Error ? e.message : "获取最近联系人失败");
      setContacts([]);
      setSelected([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      void fetchContacts();
    } else {
      setContacts([]);
      setSelected([]);
    }
  }, [open]);

  const columns: ColumnsType<DouyinRecentContact> = [
    { title: "私信显示名", dataIndex: "display_name", key: "display_name" },
    {
      title: "状态",
      key: "status",
      render: (_, record) => (existingLabels.has(record.display_name) ? "已存在" : "可导入"),
    },
  ];

  const handleImport = async () => {
    const names = selected.filter((name) => !existingLabels.has(name));
    if (!names.length) {
      message.warning("请选择要导入的联系人");
      return;
    }
    setImporting(true);
    let ok = 0;
    try {
      for (const name of names) {
        await createTarget({
          nickname: name,
          receiver_id: name,
          enabled: true,
        });
        ok += 1;
      }
      message.success(`已导入 ${ok} 个续火花对象`);
      onImported();
    } catch (e) {
      if (ok > 0) {
        message.warning(`部分导入成功（${ok} 个），后续失败：${e instanceof Error ? e.message : "未知错误"}`);
        onImported();
      } else {
        message.error(e instanceof Error ? e.message : "导入失败");
      }
    } finally {
      setImporting(false);
    }
  };

  return (
    <Modal
      title="导入最近联系的好友"
      open={open}
      onCancel={onCancel}
      width={640}
      footer={[
        <Button key="refresh" loading={loading} onClick={() => void fetchContacts()}>
          重新获取
        </Button>,
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="import" type="primary" loading={importing} onClick={() => void handleImport()}>
          导入选中
        </Button>,
      ]}
    >
      <Table
        rowKey="display_name"
        loading={loading}
        columns={columns}
        dataSource={contacts}
        pagination={false}
        rowSelection={{
          selectedRowKeys: selected,
          onChange: (keys) => setSelected(keys as string[]),
          getCheckboxProps: (record) => ({
            disabled: existingLabels.has(record.display_name),
          }),
        }}
      />
    </Modal>
  );
}
