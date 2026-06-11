import { forwardRef, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from "react";
import { cn } from "./cn";

const fieldCls =
  "w-full rounded-ctl border border-line-bright bg-white/[0.04] px-3.5 text-sm text-ink placeholder:text-ink-dim transition-all duration-150 ease-hud hover:border-white/25 focus:border-spark/70 focus:bg-spark/[0.06] focus:shadow-[0_0_0_3px_rgba(255,107,53,0.15),0_0_18px_rgba(255,107,53,0.12)] focus:outline-none disabled:cursor-not-allowed disabled:opacity-40";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return <input ref={ref} className={cn(fieldCls, "h-11", className)} {...rest} />;
  }
);

export const TextArea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function TextArea({ className, ...rest }, ref) {
    return <textarea ref={ref} className={cn(fieldCls, "min-h-[88px] py-2.5 leading-relaxed", className)} {...rest} />;
  }
);

interface FieldProps {
  label: string;
  hint?: string;
  error?: string | null;
  children: ReactNode;
}

export function Field({ label, hint, error, children }: FieldProps) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium tracking-wide text-ink-mid">{label}</span>
      {children}
      {error ? (
        <span className="mt-1.5 block text-xs text-flare">{error}</span>
      ) : hint ? (
        <span className="mt-1.5 block text-xs text-ink-dim">{hint}</span>
      ) : null}
    </label>
  );
}
