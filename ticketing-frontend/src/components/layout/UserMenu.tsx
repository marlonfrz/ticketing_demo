import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ROUTES } from "../../routes/paths";

import styles from "./UserMenu.module.css";

type UserMenuProps = {
  userName: string;
  onLogout: () => void | Promise<void>;
};

export default function UserMenu({ userName, onLogout }: UserMenuProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return undefined;

    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };

    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [isOpen]);

  const handleLogout = async () => {
    setIsOpen(false);
    await onLogout();
  };

  return (
    <div className={styles.container} ref={containerRef}>
      <button
        className={styles.trigger}
        type="button"
        aria-expanded={isOpen}
        aria-controls="user-navigation-menu"
        onClick={() => setIsOpen((current) => !current)}
      >
        <Image
          className={styles.icon}
          src="/icons/person.svg"
          alt=""
          width={22}
          height={22}
          unoptimized
        />
        <span className={styles.userName}>{userName}</span>
        <span className={styles.chevron} aria-hidden="true" />
      </button>

      {isOpen ? (
        <nav
          id="user-navigation-menu"
          className={styles.dropdown}
          aria-label="Opciones de usuario"
        >
          <Link
            className={styles.menuItem}
            href={ROUTES.profile}
            onClick={() => setIsOpen(false)}
          >
            Perfil
          </Link>
          <Link
            className={styles.menuItem}
            href={ROUTES.myTickets}
            onClick={() => setIsOpen(false)}
          >
            Mis entradas
          </Link>
          <button
            className={styles.logoutItem}
            type="button"
            onClick={handleLogout}
          >
            Cerrar sesión
          </button>
        </nav>
      ) : null}
    </div>
  );
}
