import type { ReactNode } from "react";
import IconButton from "./IconButton";
import styles from "./Modal.module.css";

type ModalProps = {
  isOpen: boolean;
  onClose?: (() => void) | undefined;
  title: string;
  children: ReactNode;
};

export default function Modal({ isOpen, onClose, title, children }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>{title}</h2>
          <IconButton
            className={styles.closeButton}
            label="Cerrar modal"
            variant="ghost"
            size="small"
            onClick={onClose}
            disabled={!onClose}
          >
            ×
          </IconButton>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}
