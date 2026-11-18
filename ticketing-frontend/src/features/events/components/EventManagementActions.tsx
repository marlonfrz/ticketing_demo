import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import Button from "../../../components/ui/Button";
import IconButton from "../../../components/ui/IconButton";
import styles from "./EventManagementActions.module.css";

type EventActionsMenuProps = {
  onEdit: () => void;
  onDelete?: () => void;
  editLabel?: string;
  actionLoading?: boolean;
};

export function EventActionsMenu({
  onEdit,
  onDelete,
  editLabel = "Editar evento",
  actionLoading = false,
}: EventActionsMenuProps) {
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
        label="Opciones del evento"
        variant="ghost"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
        disabled={actionLoading}
      >
        <Image src="/icons/ellipsis.svg" alt="" width={24} height={24} />
      </IconButton>

      {isOpen ? (
        <div className={styles.menu} role="menu">
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            onClick={() => runAction(onEdit)}
            disabled={actionLoading}
          >
            {editLabel}
          </button>
          {onDelete ? (
            <button
              type="button"
              className={`${styles.menuItem} ${styles.dangerItem}`}
              role="menuitem"
              onClick={() => runAction(onDelete)}
              disabled={actionLoading}
            >
              Borrar evento
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

type PublishEventButtonProps = {
  onClick: () => void;
  loading?: boolean;
  isRepublish?: boolean;
};

export function PublishEventButton({
  onClick,
  loading = false,
  isRepublish = false,
}: PublishEventButtonProps) {
  return (
    <Button
      type="button"
      className={styles.mainAction}
      variant="primarySoft"
      onClick={onClick}
      disabled={loading}
    >
      {loading
        ? "Publicando..."
        : isRepublish
          ? "Republicar evento"
          : "Publicar evento"}
    </Button>
  );
}

type UnpublishEventButtonProps = {
  onClick: () => void;
  loading?: boolean;
};

export function UnpublishEventButton({
  onClick,
  loading = false,
}: UnpublishEventButtonProps) {
  return (
    <Button
      type="button"
      className={styles.mainAction}
      variant="warning"
      onClick={onClick}
      disabled={loading}
    >
      {loading ? "Despublicando..." : "Despublicar evento"}
    </Button>
  );
}
