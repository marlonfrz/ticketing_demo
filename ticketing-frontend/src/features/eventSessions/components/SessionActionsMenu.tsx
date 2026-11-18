import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import IconButton from "../../../components/ui/IconButton";
import styles from "./SessionActionsMenu.module.css";

type SessionActionsMenuProps = {
  onOpenDetail: () => void;
  onDelete?: () => void;
  actionLoading?: boolean;
};

export default function SessionActionsMenu({
  onOpenDetail,
  onDelete,
  actionLoading = false,
}: SessionActionsMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const runAction = (action: () => void) => {
    setIsOpen(false);
    action();
  };

  return (
    <div className={styles.menuContainer} ref={menuRef}>
      <IconButton
        type="button"
        className={styles.menuTrigger}
        label="Opciones de la sesión"
        variant="ghost"
        size="small"
        aria-label="Opciones de la sesión"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
        disabled={actionLoading}
      >
        <Image src="/icons/ellipsis.svg" alt="" width={22} height={22} />
      </IconButton>

      {isOpen ? (
        <div className={styles.menu} role="menu">
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            onClick={() => runAction(onOpenDetail)}
            disabled={actionLoading}
          >
            Detalle y edición
          </button>
          {onDelete ? (
            <button
              type="button"
              className={`${styles.menuItem} ${styles.dangerItem}`}
              role="menuitem"
              onClick={() => runAction(onDelete)}
              disabled={actionLoading}
            >
              Borrar sesión
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
