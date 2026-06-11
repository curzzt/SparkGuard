import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "./cn";

type Variant = "primary" | "outline" | "ghost" | "danger" | "link" | "volt";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  block?: boolean;
}

const variantCls: Record<Variant, string> = {
  primary:
    "border-transparent bg-gradient-to-r from-spark to-flare text-white shadow-[0_4px_18px_rgba(255,107,53,0.35)] hover:brightness-110 hover:shadow-[0_6px_26px_rgba(251,37,118,0.45)] hover:-translate-y-px active:translate-y-0",
  volt:
    "border-volt/40 bg-volt/10 text-volt-soft hover:bg-volt/20 hover:border-volt/70 hover:shadow-glow-volt",
  outline:
    "border-line-bright bg-white/[0.04] text-ink hover:border-spark/60 hover:text-spark-soft hover:bg-spark/10",
  ghost: "border-transparent bg-transparent text-ink-mid hover:text-ink hover:bg-white/[0.06]",
  danger:
    "border-flare/40 bg-flare/10 text-flare hover:bg-flare/20 hover:border-flare/70 hover:shadow-[0_0_18px_rgba(251,37,118,0.3)]",
  link: "border-transparent bg-transparent px-1 text-spark-soft hover:text-spark underline-offset-4 hover:underline",
};

const sizeCls: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-12 px-6 text-base gap-2",
};

export default function Button({
  variant = "outline",
  size = "md",
  loading = false,
  icon,
  block = false,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={cn(
        "inline-flex min-h-0 cursor-pointer select-none items-center justify-center whitespace-nowrap rounded-ctl border font-medium transition-all duration-150 ease-hud disabled:cursor-not-allowed disabled:opacity-40",
        variantCls[variant],
        sizeCls[size],
        block && "w-full",
        className
      )}
      {...rest}
    >
      {loading ? <Loader2 size={15} strokeWidth={1.5} className="animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}
