import { cn } from "./cn";

const statusMeta: Record<string, { label: string; cls: string }> = {
  success: { label: "成功", cls: "text-volt border-volt/40 bg-volt/10 shadow-[0_0_12px_rgba(34,211,238,0.18)]" },
  failed: { label: "失败", cls: "text-flare border-flare/40 bg-flare/10 shadow-[0_0_12px_rgba(251,37,118,0.18)]" },
  unsupported: { label: "不支持", cls: "text-ember border-ember/40 bg-ember/10" },
  skipped: { label: "已跳过", cls: "text-ink-dim border-line-bright bg-white/[0.04]" },
  pending: { label: "待执行", cls: "text-ink-mid border-line-bright bg-white/[0.04]" },
  running: { label: "执行中", cls: "text-spark-soft border-spark/40 bg-spark/10 shadow-glow-spark" },
  completed: { label: "已完成", cls: "text-volt border-volt/40 bg-volt/10" },
  partial: { label: "部分完成", cls: "text-ember border-ember/40 bg-ember/10" },
  auth_expired: { label: "授权失效", cls: "text-flare border-flare/40 bg-flare/10" },
  no_target: { label: "无对象", cls: "text-ink-dim border-line-bright bg-white/[0.04]" },
};

interface StatusBadgeProps {
  status?: string | null;
  pulse?: boolean;
  className?: string;
}

export default function StatusBadge({ status, pulse = false, className }: StatusBadgeProps) {
  if (!status) return <span className="text-ink-dim">-</span>;
  const meta = statusMeta[status] || { label: status, cls: "text-ink-mid border-line-bright bg-white/[0.04]" };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        meta.cls,
        className
      )}
    >
      {pulse && <span className="pulse-dot" style={{ width: 6, height: 6 }} />}
      {meta.label}
    </span>
  );
}
