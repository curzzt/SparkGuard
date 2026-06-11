import { cn } from "./cn";

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  size?: "sm" | "md";
  label?: string;
}

export default function Switch({ checked, onChange, disabled, size = "md", label }: SwitchProps) {
  const dims = size === "md" ? "h-6 w-11" : "h-5 w-9";
  const knob = size === "md" ? "h-4.5 w-4.5" : "h-3.5 w-3.5";
  const shift = size === "md" ? "translate-x-[22px]" : "translate-x-[18px]";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex shrink-0 cursor-pointer items-center rounded-full border transition-all duration-250 ease-hud disabled:cursor-not-allowed disabled:opacity-40",
        dims,
        checked
          ? "border-spark/70 bg-gradient-to-r from-spark/80 to-ember/70 shadow-glow-spark"
          : "border-line-bright bg-white/[0.06]"
      )}
    >
      <span
        className={cn(
          "absolute left-[3px] rounded-full bg-white shadow-md transition-transform duration-250 ease-hud",
          knob,
          checked ? shift : "translate-x-0"
        )}
      />
    </button>
  );
}
