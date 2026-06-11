import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { cn } from "./cn";

type ToastKind = "success" | "error" | "warning" | "info";

interface ToastItem {
  id: number;
  kind: ToastKind;
  text: string;
}

let pushImpl: ((kind: ToastKind, text: string) => void) | null = null;
let seq = 0;

export const toast = {
  success(text: string) {
    pushImpl?.("success", text);
  },
  error(text: string) {
    pushImpl?.("error", text);
  },
  warning(text: string) {
    pushImpl?.("warning", text);
  },
  info(text: string) {
    pushImpl?.("info", text);
  },
};

const kindMeta: Record<ToastKind, { icon: typeof CheckCircle2; cls: string }> = {
  success: { icon: CheckCircle2, cls: "text-volt border-volt/35 shadow-[0_0_24px_rgba(34,211,238,0.18)]" },
  error: { icon: XCircle, cls: "text-flare border-flare/40 shadow-[0_0_24px_rgba(251,37,118,0.2)]" },
  warning: { icon: AlertTriangle, cls: "text-ember border-ember/40 shadow-[0_0_24px_rgba(255,179,71,0.18)]" },
  info: { icon: Info, cls: "text-ink-mid border-line-bright" },
};

export function Toaster() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    pushImpl = (kind, text) => {
      const id = ++seq;
      setItems((prev) => [...prev.slice(-4), { id, kind, text }]);
      window.setTimeout(() => {
        setItems((prev) => prev.filter((item) => item.id !== id));
      }, 3200);
    };
    return () => {
      pushImpl = null;
    };
  }, []);

  return createPortal(
    <div className="fixed left-1/2 top-5 z-[1000] flex -translate-x-1/2 flex-col items-center gap-2" role="status">
      {items.map((item) => {
        const meta = kindMeta[item.kind];
        const Icon = meta.icon;
        return (
          <div
            key={item.id}
            className={cn(
              "toast-in glass flex items-center gap-2.5 rounded-ctl border px-4 py-2.5 text-sm text-ink",
              meta.cls
            )}
          >
            <Icon size={16} strokeWidth={1.5} aria-hidden />
            <span>{item.text}</span>
          </div>
        );
      })}
    </div>,
    document.body
  );
}
