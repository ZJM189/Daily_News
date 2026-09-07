"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

export function Modal({
  title,
  children,
  onClose,
  busy = false,
  drawer = false
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
  drawer?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    const previousOverflow = document.body.style.overflow;
    dialog?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`favoritesDialog ${drawer ? "favoritesDrawer" : ""}`}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <header className="favoritesDialogHeader">
        <h2 id={titleId}>{title}</h2>
        <button
          type="button"
          className="favoriteIconButton"
          title="关闭"
          aria-label="关闭"
          disabled={busy}
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </header>
      {children}
    </dialog>
  );
}
