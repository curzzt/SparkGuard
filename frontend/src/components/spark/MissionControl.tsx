import { useEffect, useMemo, useState } from "react";
import { CalendarOff, Flame, Zap } from "lucide-react";
import Button from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import CountUp from "@/components/ui/CountUp";
import ProgressRing from "@/components/ui/ProgressRing";
import Skeleton from "@/components/ui/Skeleton";
import StatusBadge from "@/components/ui/StatusBadge";
import Switch from "@/components/ui/Switch";
import { toast } from "@/components/ui/toast";
import type { SparkSettings, TodayStatus } from "@/types/spark";

interface MissionControlProps {
  settings?: SparkSettings;
  status?: TodayStatus;
  loading?: boolean;
  onToggleEnabled: (enabled: boolean) => Promise<unknown>;
  onRunNow: () => Promise<unknown>;
  onSkipToday: () => Promise<unknown>;
  runLoading?: boolean;
}

function nextRunDate(executeTime: string, skipToday: boolean): Date {
  const [h, m] = executeTime.split(":").map((v) => Number.parseInt(v, 10) || 0);
  const next = new Date();
  next.setHours(h, m, 0, 0);
  if (skipToday || next.getTime() <= Date.now()) {
    next.setDate(next.getDate() + 1);
  }
  return next;
}

function useCountdown(executeTime?: string, enabled?: boolean, skipToday?: boolean) {
  const [text, setText] = useState("--:--:--");

  useEffect(() => {
    if (!executeTime || !enabled) {
      setText("--:--:--");
      return;
    }
    const tick = () => {
      const diff = nextRunDate(executeTime, skipToday === true).getTime() - Date.now();
      const total = Math.max(Math.floor(diff / 1000), 0);
      const hh = String(Math.floor(total / 3600)).padStart(2, "0");
      const mm = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
      const ss = String(total % 60).padStart(2, "0");
      setText(`${hh}:${mm}:${ss}`);
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [executeTime, enabled, skipToday]);

  return text;
}

export default function MissionControl({
  settings,
  status,
  loading,
  onToggleEnabled,
  onRunNow,
  onSkipToday,
  runLoading,
}: MissionControlProps) {
  const [igniteKey, setIgniteKey] = useState(0);
  const countdown = useCountdown(settings?.execute_time, settings?.enabled, settings?.skip_today);

  const handleToggle = async (checked: boolean) => {
    try {
      await onToggleEnabled(checked);
      if (checked) {
        setIgniteKey((k) => k + 1);
        toast.success("自动续航已点火");
      } else {
        toast.info("自动续航已关闭");
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  const handleRunNow = async () => {
    try {
      await onRunNow();
      toast.success("任务已触发");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "执行失败");
    }
  };

  const handleSkipToday = async () => {
    try {
      await onSkipToday();
      toast.success("已跳过今日");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  const enabled = settings?.enabled === true;
  const targetCount = status?.target_count ?? 0;
  const doneCount = (status?.success_count ?? 0) + (status?.failed_count ?? 0) + (status?.unsupported_count ?? 0);
  const jobStatus = status?.job_status || "pending";

  const segments = useMemo(
    () => [
      { value: status?.success_count ?? 0, color: "#22d3ee" },
      { value: status?.failed_count ?? 0, color: "#fb2576" },
      { value: status?.unsupported_count ?? 0, color: "#ffb347" },
    ],
    [status]
  );

  const tiles = [
    { label: "目标", value: targetCount, cls: "text-spark-soft text-glow-spark" },
    { label: "成功", value: status?.success_count ?? 0, cls: "text-volt text-glow-volt" },
    { label: "失败", value: status?.failed_count ?? 0, cls: "text-flare" },
    { label: "不支持", value: status?.unsupported_count ?? 0, cls: "text-ember" },
  ];

  if (loading) {
    return (
      <section className="glass p-6">
        <div className="flex flex-col gap-5 md:flex-row md:items-center">
          <Skeleton className="h-36 flex-1" />
          <Skeleton className="h-36 w-36 rounded-full" />
          <Skeleton className="h-36 flex-1" />
        </div>
      </section>
    );
  }

  return (
    <section className="glass glass-flow hud-corners relative overflow-hidden p-6 md:p-8">
      <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-spark/10 blur-3xl" aria-hidden />
      <div className="relative grid grid-cols-1 items-center gap-8 lg:grid-cols-[1fr_auto_1fr]">
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-3">
            <span className="font-hud text-[11px] uppercase tracking-[0.35em] text-ink-dim">Mission Control</span>
            <StatusBadge status={jobStatus} pulse={jobStatus === "running" || jobStatus === "pending"} />
            {settings?.skip_today && (
              <span className="rounded-full border border-ember/40 bg-ember/10 px-2.5 py-0.5 text-xs text-ember">
                今日已跳过
              </span>
            )}
          </div>

          <div>
            <p className="m-0 mb-1 text-xs text-ink-dim">{enabled ? "距下次自动续航" : "自动续航处于待机状态"}</p>
            <p
              className={cn(
                "font-hud m-0 text-5xl font-bold leading-none md:text-6xl",
                enabled ? "text-ink text-glow-spark" : "text-ink-dim"
              )}
            >
              {countdown}
            </p>
            <p className="font-hud m-0 mt-2 text-xs text-ink-dim">
              每日 {settings?.execute_time || "--:--"} 自动执行 · 上限 {settings?.daily_limit ?? "-"} 人
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div key={igniteKey} className={cn("rounded-full", igniteKey > 0 && enabled && "ignite-wave")}>
              <Switch checked={enabled} onChange={(v) => void handleToggle(v)} label="自动续火花总开关" />
            </div>
            <div className="flex flex-col">
              <span className="flex items-center gap-1.5 text-sm font-semibold text-ink">
                <Flame size={15} strokeWidth={1.5} className={enabled ? "text-spark" : "text-ink-dim"} />
                自动续航引擎
              </span>
              <span className="text-xs text-ink-dim">{enabled ? "已点火 · 到点自动执行" : "已熄火 · 不会自动执行"}</span>
            </div>
          </div>

          <div className="h-1 overflow-hidden rounded-full bg-white/[0.06]">
            <div className={cn("h-full w-full rounded-full", enabled ? "energy-bar" : "bg-white/[0.04]")} />
          </div>
        </div>

        <div className="flex justify-center">
          <ProgressRing segments={segments} total={targetCount} size={172} strokeWidth={9}>
            <span className="font-hud text-3xl font-bold text-ink">
              <CountUp value={doneCount} />
              <span className="text-base text-ink-dim">/{targetCount}</span>
            </span>
            <span className="mt-1 text-[11px] tracking-wider text-ink-dim">今日已处理</span>
          </ProgressRing>
        </div>

        <div className="flex flex-col gap-5">
          <div className="grid grid-cols-4 gap-2.5 lg:grid-cols-2">
            {tiles.map((tile) => (
              <div
                key={tile.label}
                className="rounded-ctl border border-line bg-white/[0.03] px-3 py-2.5 transition-all duration-150 ease-hud hover:border-line-bright hover:bg-white/[0.06]"
              >
                <p className="m-0 text-[11px] text-ink-dim">{tile.label}</p>
                <p className={cn("font-hud m-0 text-2xl font-bold leading-tight", tile.cls)}>
                  <CountUp value={tile.value} />
                </p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="primary"
              loading={runLoading}
              icon={<Zap size={15} strokeWidth={1.5} />}
              onClick={() => void handleRunNow()}
              className={cn("relative overflow-hidden", runLoading && "charge-fill")}
            >
              立即执行
            </Button>
            <Button
              variant="ghost"
              icon={<CalendarOff size={15} strokeWidth={1.5} />}
              disabled={settings?.skip_today}
              onClick={() => void handleSkipToday()}
            >
              跳过今日
            </Button>
          </div>

          <p className="font-hud m-0 text-xs text-ink-dim">最近执行：{status?.last_execute_at || "暂无记录"}</p>
        </div>
      </div>
    </section>
  );
}
