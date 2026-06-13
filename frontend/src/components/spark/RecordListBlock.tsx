import { useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, History } from "lucide-react";
import Button from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import GlassCard from "@/components/ui/GlassCard";
import { SkeletonRows } from "@/components/ui/Skeleton";
import StatusBadge from "@/components/ui/StatusBadge";
import type { SparkRecord } from "@/types/spark";

const PAGE_SIZE = 10;

const railColor: Record<string, string> = {
  success: "#22d3ee",
  failed: "#fb2576",
  unsupported: "#ffb347",
  skipped: "rgba(255,255,255,0.25)",
  auth_expired: "#fb2576",
  no_target: "rgba(255,255,255,0.25)",
};

interface RecordListBlockProps {
  records: SparkRecord[];
  loading?: boolean;
}

export default function RecordListBlock({ records, loading }: RecordListBlockProps) {
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const totalPages = Math.max(Math.ceil(records.length / PAGE_SIZE), 1);
  const pageItems = records.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <GlassCard
      title={
        <>
          <History size={15} strokeWidth={1.5} className="text-spark-soft" />
          执行记录
          <span className="font-hud text-xs font-normal text-ink-dim">近 7 天</span>
        </>
      }
      extra={
        records.length > PAGE_SIZE && (
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="ghost"
              aria-label="上一页"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              icon={<ChevronLeft size={14} strokeWidth={1.5} />}
            />
            <span className="font-hud text-xs text-ink-dim">
              {page}/{totalPages}
            </span>
            <Button
              size="sm"
              variant="ghost"
              aria-label="下一页"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              icon={<ChevronRight size={14} strokeWidth={1.5} />}
            />
          </div>
        )
      }
      className="rise-in"
      style={{ animationDelay: "0.24s" }}
      bodyClassName="p-3"
    >
      {loading ? (
        <SkeletonRows rows={5} className="p-2" />
      ) : records.length === 0 ? (
        <p className="m-0 py-10 text-center text-sm text-ink-dim">暂无执行记录，到点执行或「立即执行」后将在此呈现</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
          {pageItems.map((record) => {
            const expanded = expandedId === record.id;
            const hasDetail = Boolean(record.run_log || record.screenshot_base64);
            return (
              <li
                key={record.id}
                onClick={() => hasDetail && setExpandedId(expanded ? null : record.id)}
                className={cn(
                  "relative flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-ctl border border-line bg-white/[0.02] py-2.5 pl-5 pr-3 transition-all duration-150 ease-hud hover:border-line-bright hover:bg-white/[0.05]",
                  hasDetail && "cursor-pointer",
                  expanded && "border-line-bright bg-white/[0.05]"
                )}
              >
                <span
                  className="absolute bottom-2 left-2 top-2 w-[3px] rounded-full"
                  style={{
                    background: railColor[record.status] || "rgba(255,255,255,0.25)",
                    boxShadow: `0 0 8px ${railColor[record.status] || "transparent"}`,
                  }}
                  aria-hidden
                />
                <span className="font-hud w-44 shrink-0 text-xs text-ink-mid">
                  {record.execute_date} {record.execute_time}
                </span>
                <span className="w-28 shrink-0 truncate text-sm font-medium text-ink">
                  {record.target_nickname || "-"}
                </span>
                <span className="min-w-0 flex-1 truncate text-xs text-ink-dim" title={record.message || undefined}>
                  {record.message || "-"}
                </span>
                <span className="font-hud rounded border border-line px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-ink-dim">
                  {record.channel}
                </span>
                <StatusBadge status={record.status} />
                {hasDetail && (
                  <ChevronDown
                    size={14}
                    strokeWidth={1.5}
                    className={cn("shrink-0 text-ink-dim transition-transform duration-150", expanded && "rotate-180")}
                    aria-hidden
                  />
                )}
                {record.error_message && (
                  <span
                    className={cn("w-full truncate pl-0 text-xs text-flare/80")}
                    title={record.error_message}
                  >
                    {record.error_message}
                  </span>
                )}
                {expanded && (
                  <div className="flex w-full flex-col gap-2">
                    {record.run_log && (
                      <pre className="m-0 mt-1 w-full whitespace-pre-wrap break-words rounded-ctl border border-line bg-black/30 p-3 font-mono text-[11px] leading-relaxed text-ink-mid">
                        {record.run_log}
                      </pre>
                    )}
                    {record.screenshot_base64 && (
                      <a
                        href={`data:image/png;base64,${record.screenshot_base64}`}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="block w-full overflow-hidden rounded-ctl border border-line"
                        title="点击查看大图"
                      >
                        <img
                          src={`data:image/png;base64,${record.screenshot_base64}`}
                          alt="发送结果截图"
                          className="block max-h-80 w-full object-contain bg-black/40"
                        />
                      </a>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </GlassCard>
  );
}
