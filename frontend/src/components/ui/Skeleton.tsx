import { cn } from "./cn";

interface SkeletonProps {
  className?: string;
}

export default function Skeleton({ className }: SkeletonProps) {
  return <div className={cn("skeleton", className)} aria-hidden />;
}

export function SkeletonRows({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-3", className)} aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-10" style={{ width: `${100 - i * 8}%` }} />
      ))}
    </div>
  );
}
