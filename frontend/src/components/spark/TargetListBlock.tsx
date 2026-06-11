import { useState } from "react";
import { Flame, Import, Pencil, Plus, Trash2, Users } from "lucide-react";
import { batchDisableTargets, createTarget, deleteTarget, updateTarget } from "@/api/spark";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import { cn } from "@/components/ui/cn";
import GlassCard from "@/components/ui/GlassCard";
import PopConfirm from "@/components/ui/PopConfirm";
import { SkeletonRows } from "@/components/ui/Skeleton";
import StatusBadge from "@/components/ui/StatusBadge";
import Switch from "@/components/ui/Switch";
import { toast } from "@/components/ui/toast";
import type { SparkTarget } from "@/types/spark";
import RecentContactsImportModal from "./RecentContactsImportModal";
import TargetFormModal from "./TargetFormModal";

interface TargetListBlockProps {
  targets: SparkTarget[];
  loading?: boolean;
  accountBound?: boolean;
  onChanged: () => void;
  onBatchEnable: (ids: number[]) => Promise<unknown>;
}

function EmptyTargets({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-12">
      <svg width="120" height="120" viewBox="0 0 120 120" fill="none" aria-hidden>
        <circle cx="60" cy="60" r="46" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="4 6" />
        <circle cx="60" cy="60" r="34" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
        <path
          d="M60 38c4 8 14 12 14 24a14 14 0 1 1-28 0c0-6 3-9 6-13 1 4 3 6 5 7-1-7 0-13 3-18z"
          stroke="#ff6b35"
          strokeWidth="1.5"
          strokeLinejoin="round"
          fill="rgba(255,107,53,0.08)"
        />
        <circle cx="60" cy="14" r="2" fill="#22d3ee" opacity="0.8" />
        <circle cx="98" cy="78" r="1.5" fill="#ff6b35" opacity="0.8" />
        <circle cx="22" cy="70" r="1.5" fill="#ffb347" opacity="0.7" />
      </svg>
      <div className="text-center">
        <p className="m-0 text-sm font-medium text-ink">还没有续火花对象</p>
        <p className="m-0 mt-1 text-xs text-ink-dim">添加对象后，到点即可自动续航</p>
      </div>
      <Button variant="primary" icon={<Plus size={15} strokeWidth={1.5} />} onClick={onAdd}>
        新增第一个对象
      </Button>
    </div>
  );
}

export default function TargetListBlock({
  targets,
  loading,
  accountBound,
  onChanged,
  onBatchEnable,
}: TargetListBlockProps) {
  const [selected, setSelected] = useState<number[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [editing, setEditing] = useState<SparkTarget | null>(null);

  const allSelected = targets.length > 0 && selected.length === targets.length;

  const toggleAll = () => {
    setSelected(allSelected ? [] : targets.map((t) => t.id));
  };

  const toggleOne = (id: number) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]));
  };

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const handleSubmit = async (values: Partial<SparkTarget>) => {
    try {
      if (editing) {
        await updateTarget(editing.id, values);
        toast.success("已更新");
      } else {
        await createTarget(values);
        toast.success("已创建");
      }
      setModalOpen(false);
      setEditing(null);
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "保存失败");
    }
  };

  const handleToggleEnabled = async (target: SparkTarget, checked: boolean) => {
    try {
      await updateTarget(target.id, { enabled: checked });
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "更新失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteTarget(id);
      toast.success("已删除");
      setSelected((prev) => prev.filter((v) => v !== id));
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "删除失败");
    }
  };

  const handleBatchEnable = async () => {
    try {
      await onBatchEnable(selected);
      toast.success("已批量启用");
      setSelected([]);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  const handleBatchDisable = async () => {
    try {
      await batchDisableTargets(selected);
      toast.success("已批量停用");
      setSelected([]);
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  return (
    <GlassCard
      title={
        <>
          <Users size={15} strokeWidth={1.5} className="text-spark-soft" />
          续火花对象
          <span className="font-hud text-xs font-normal text-ink-dim">{targets.length}</span>
        </>
      }
      extra={
        <>
          <Button
            size="sm"
            disabled={!accountBound}
            icon={<Import size={14} strokeWidth={1.5} />}
            onClick={() => setImportOpen(true)}
            title={accountBound ? undefined : "需先关联抖音账号"}
          >
            导入最近好友
          </Button>
          <Button size="sm" variant="primary" icon={<Plus size={14} strokeWidth={1.5} />} onClick={openCreate}>
            新增
          </Button>
        </>
      }
      className="rise-in"
      style={{ animationDelay: "0.08s" }}
      bodyClassName="relative p-3"
    >
      {loading ? (
        <SkeletonRows rows={4} className="p-2" />
      ) : targets.length === 0 ? (
        <EmptyTargets onAdd={openCreate} />
      ) : (
        <>
          <div className="flex items-center gap-3 px-3 py-2 text-[11px] uppercase tracking-wider text-ink-dim">
            <Checkbox checked={allSelected} onChange={toggleAll} label="全选" />
            <span>全选</span>
          </div>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {targets.map((target) => {
              const checked = selected.includes(target.id);
              return (
                <li
                  key={target.id}
                  className={cn(
                    "group rounded-ctl border px-3 py-3 transition-all duration-150 ease-hud",
                    checked
                      ? "border-spark/50 bg-spark/[0.07]"
                      : "border-line bg-white/[0.03] hover:border-line-bright hover:bg-white/[0.05]"
                  )}
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <Checkbox checked={checked} onChange={() => toggleOne(target.id)} label={`选择 ${target.nickname}`} />
                    <Flame
                      size={16}
                      strokeWidth={1.5}
                      className={target.enabled ? "text-spark" : "text-ink-dim"}
                      aria-hidden
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-ink">{target.nickname}</span>
                        {target.remark && <span className="text-xs text-ink-dim">{target.remark}</span>}
                        <StatusBadge status={target.last_status} />
                      </div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-3 text-xs text-ink-dim">
                        <span className="font-hud">{target.receiver_id}</span>
                        {target.custom_template && (
                          <span className="max-w-64 truncate" title={target.custom_template}>
                            模板：{target.custom_template}
                          </span>
                        )}
                      </div>
                    </div>
                    <Switch
                      checked={target.enabled}
                      onChange={(v) => void handleToggleEnabled(target, v)}
                      size="sm"
                      label={`启用 ${target.nickname}`}
                    />
                    <div className="flex items-center gap-1 opacity-60 transition-opacity duration-150 group-hover:opacity-100">
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label="编辑"
                        icon={<Pencil size={14} strokeWidth={1.5} />}
                        onClick={() => {
                          setEditing(target);
                          setModalOpen(true);
                        }}
                      />
                      <PopConfirm title={`确认删除「${target.nickname}」？`} onConfirm={() => handleDelete(target.id)}>
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label="删除"
                          className="hover:text-flare"
                          icon={<Trash2 size={14} strokeWidth={1.5} />}
                        />
                      </PopConfirm>
                    </div>
                  </div>
                  {(target.last_run_at || target.last_error) && (
                    <div className="mt-2 flex flex-wrap gap-4 border-t border-line pt-2 text-xs">
                      {target.last_run_at && (
                        <span className="font-hud text-ink-dim">最近执行 {target.last_run_at}</span>
                      )}
                      {target.last_error && <span className="text-flare/90">失败原因：{target.last_error}</span>}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>

          {selected.length > 0 && (
            <div className="toast-in glass sticky bottom-3 mt-3 flex items-center justify-between gap-3 rounded-ctl border border-spark/40 px-4 py-2.5 shadow-glow-spark">
              <span className="font-hud text-xs text-ink-mid">已选 {selected.length} 项</span>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="volt" onClick={() => void handleBatchEnable()}>
                  批量启用
                </Button>
                <Button size="sm" onClick={() => void handleBatchDisable()}>
                  批量停用
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setSelected([])}>
                  取消
                </Button>
              </div>
            </div>
          )}
        </>
      )}

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
    </GlassCard>
  );
}
