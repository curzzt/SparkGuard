import { Check } from "lucide-react";
import { cn } from "./cn";

interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
}

export default function Checkbox({ checked, onChange, disabled, label }: CheckboxProps) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        onChange(!checked);
      }}
      className={cn(
        "inline-flex h-4.5 w-4.5 shrink-0 cursor-pointer items-center justify-center rounded border transition-all duration-150 ease-hud disabled:cursor-not-allowed disabled:opacity-30",
        checked ? "border-spark bg-spark shadow-glow-spark" : "border-line-bright bg-white/[0.04] hover:border-spark/60"
      )}
    >
      {checked && <Check size={12} strokeWidth={2.5} className="text-white" aria-hidden />}
    </button>
  );
}
