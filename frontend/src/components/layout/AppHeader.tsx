import { LogOut, ScanLine } from "lucide-react";
import { logout } from "@/api/auth";
import Button from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import { useAuth } from "@/hooks/useAuth";
import type { DouyinAccount } from "@/types/douyin";

interface AppHeaderProps {
  account?: DouyinAccount;
  onAccountClick?: () => void;
  onLogout?: () => void;
}

export default function AppHeader({ account, onAccountClick, onLogout }: AppHeaderProps) {
  const { user, clearAuth } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      clearAuth();
      onLogout?.();
    }
  };

  const bound = account?.bound === true;
  const active = bound && account?.auth_status === "active";

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-void/60 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <span className="spark-dot" aria-hidden />
          <span className="brand-gradient text-lg font-bold tracking-widest">火花续航</span>
          <span className="font-hud hidden text-[11px] uppercase tracking-[0.3em] text-ink-dim sm:inline">
            SparkGuard
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          {onAccountClick && (
            <button
              type="button"
              onClick={onAccountClick}
              aria-label="抖音账号状态"
              className={cn(
                "flex h-9 cursor-pointer items-center gap-2 rounded-full border px-3.5 text-xs font-medium transition-all duration-150 ease-hud",
                active
                  ? "border-volt/40 bg-volt/10 text-volt-soft hover:border-volt/70 hover:shadow-glow-volt"
                  : bound
                    ? "border-ember/40 bg-ember/10 text-ember hover:border-ember/70"
                    : "border-flare/40 bg-flare/10 text-flare hover:border-flare/70"
              )}
            >
              {active ? (
                <span className="pulse-dot" style={{ width: 7, height: 7 }} />
              ) : (
                <span
                  className="inline-block h-[7px] w-[7px] rounded-full"
                  style={{ background: "currentColor", boxShadow: "0 0 8px currentColor" }}
                />
              )}
              {active ? (account?.nickname || "抖音已关联") : bound ? "登录态异常" : "未关联抖音"}
              {!bound && <ScanLine size={13} strokeWidth={1.5} aria-hidden />}
            </button>
          )}

          {user?.phone && (
            <span className="font-hud hidden rounded-full border border-line-bright bg-white/[0.05] px-3.5 py-1.5 text-xs text-ink-mid md:inline">
              {user.phone}
            </span>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => void handleLogout()}
            icon={<LogOut size={14} strokeWidth={1.5} />}
            aria-label="退出登录"
          >
            退出
          </Button>
        </div>
      </div>
    </header>
  );
}
