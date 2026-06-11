import { cn } from "./cn";

export default function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-block h-9 w-9 animate-spin rounded-full border-2 border-spark/20 border-t-spark shadow-glow-spark",
        className
      )}
      role="status"
      aria-label="加载中"
    />
  );
}

export function FullScreenSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner />
    </div>
  );
}
