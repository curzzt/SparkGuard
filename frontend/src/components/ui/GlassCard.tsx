import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "./cn";

interface GlassCardProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  title?: ReactNode;
  extra?: ReactNode;
  hud?: boolean;
  flow?: boolean;
  bodyClassName?: string;
}

export default function GlassCard({
  title,
  extra,
  hud = false,
  flow = true,
  className,
  bodyClassName,
  children,
  ...rest
}: GlassCardProps) {
  return (
    <section className={cn("glass", flow && "glass-flow", hud && "hud-corners", className)} {...rest}>
      {(title || extra) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <h2 className="m-0 flex items-center gap-2 text-sm font-semibold tracking-wide text-ink">{title}</h2>
          {extra && <div className="flex items-center gap-2">{extra}</div>}
        </header>
      )}
      <div className={cn("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}
