import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import Button from "./Button";
import { cn } from "./cn";

interface ModalProps {
  open: boolean;
  title: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
  width?: number;
  children: ReactNode;
}

export default function Modal({ open, title, onClose, footer, width = 480, children }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[900] flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="backdrop-in absolute inset-0 bg-void/70 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div
        className={cn("modal-in glass hud-corners relative flex max-h-[88vh] w-full flex-col")}
        style={{ maxWidth: width }}
      >
        <header className="flex items-center justify-between border-b border-line px-5 py-4">
          <h3 className="m-0 text-sm font-semibold tracking-wide text-ink">{title}</h3>
          <Button variant="ghost" size="sm" aria-label="关闭" onClick={onClose} icon={<X size={16} strokeWidth={1.5} />} />
        </header>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {footer && <footer className="flex items-center justify-end gap-2 border-t border-line px-5 py-3.5">{footer}</footer>}
      </div>
    </div>,
    document.body
  );
}
