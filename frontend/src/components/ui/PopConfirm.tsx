import { useEffect, useRef, useState, type ReactNode } from "react";
import Button from "./Button";

interface PopConfirmProps {
  title: string;
  onConfirm: () => void | Promise<void>;
  children: ReactNode;
}

export default function PopConfirm({ title, onConfirm, children }: PopConfirmProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  return (
    <span ref={ref} className="relative inline-flex">
      <span onClick={() => setOpen((v) => !v)}>{children}</span>
      {open && (
        <div className="toast-in glass absolute right-0 top-full z-50 mt-2 w-52 rounded-ctl border border-line-bright p-3">
          <p className="m-0 mb-2.5 text-xs text-ink">{title}</p>
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button
              size="sm"
              variant="danger"
              onClick={async () => {
                setOpen(false);
                await onConfirm();
              }}
            >
              确认
            </Button>
          </div>
        </div>
      )}
    </span>
  );
}
