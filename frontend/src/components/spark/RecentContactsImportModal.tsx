import { useEffect, useMemo, useState } from "react";
import { RefreshCw, UserRoundPlus } from "lucide-react";
import { getDouyinRecentContacts } from "@/api/douyin";
import { createTarget } from "@/api/spark";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import { cn } from "@/components/ui/cn";
import Modal from "@/components/ui/Modal";
import { SkeletonRows } from "@/components/ui/Skeleton";
import { toast } from "@/components/ui/toast";
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
      const selectable = data.items.map((c) => c.display_name).filter((name) => !existingLabels.has(name));
      setSelected(selectable);
      if (!data.items.length) {
        toast.warning("未获取到最近联系人");
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "获取最近联系人失败");
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

  const toggleName = (name: string) => {
    setSelected((prev) => (prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]));
  };

  const handleImport = async () => {
    const names = selected.filter((name) => !existingLabels.has(name));
    if (!names.length) {
      toast.warning("请选择要导入的联系人");
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
      toast.success(`已导入 ${ok} 个续火花对象`);
      onImported();
    } catch (e) {
      if (ok > 0) {
        toast.warning(`部分导入成功（${ok} 个），后续失败：${e instanceof Error ? e.message : "未知错误"}`);
        onImported();
      } else {
        toast.error(e instanceof Error ? e.message : "导入失败");
      }
    } finally {
      setImporting(false);
    }
  };

  return (
    <Modal
      open={open}
      title="导入最近联系的好友"
      onClose={onCancel}
      width={560}
      footer={
        <>
          <Button size="sm" loading={loading} icon={<RefreshCw size={14} strokeWidth={1.5} />} onClick={() => void fetchContacts()}>
            重新获取
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel}>
            取消
          </Button>
          <Button
            size="sm"
            variant="primary"
            loading={importing}
            icon={<UserRoundPlus size={14} strokeWidth={1.5} />}
            onClick={() => void handleImport()}
          >
            导入选中（{selected.filter((n) => !existingLabels.has(n)).length}）
          </Button>
        </>
      }
    >
      {loading ? (
        <SkeletonRows rows={5} />
      ) : contacts.length === 0 ? (
        <p className="m-0 py-10 text-center text-sm text-ink-dim">暂无最近联系人，可点击「重新获取」</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
          {contacts.map((contact) => {
            const exists = existingLabels.has(contact.display_name);
            const checked = selected.includes(contact.display_name);
            return (
              <li
                key={contact.display_name}
                onClick={() => !exists && toggleName(contact.display_name)}
                className={cn(
                  "flex items-center justify-between gap-3 rounded-ctl border px-3.5 py-2.5 transition-all duration-150 ease-hud",
                  exists
                    ? "border-line bg-white/[0.02] opacity-50"
                    : "cursor-pointer border-line bg-white/[0.03] hover:border-spark/40 hover:bg-spark/[0.06]",
                  checked && !exists && "border-spark/50 bg-spark/[0.08]"
                )}
              >
                <span className="flex items-center gap-3">
                  <Checkbox
                    checked={checked && !exists}
                    disabled={exists}
                    onChange={() => toggleName(contact.display_name)}
                    label={`选择 ${contact.display_name}`}
                  />
                  <span className="text-sm text-ink">{contact.display_name}</span>
                </span>
                <span className={cn("text-xs", exists ? "text-ink-dim" : "text-volt-soft")}>
                  {exists ? "已存在" : "可导入"}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Modal>
  );
}
