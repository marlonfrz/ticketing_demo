"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import styles from "./NavDropdown.module.css";

export type NavDropdownItem = {
  label: string;
  href: string;
  badge?: number;
};

type NavDropdownProps = {
  label: string;
  items: NavDropdownItem[];
};

const routeMatches = (pathname: string, route: string) =>
  pathname === route ||
  (route !== "/" && pathname.startsWith(`${route}/`));

export default function NavDropdown({ label, items }: NavDropdownProps) {
  const pathname = usePathname() ?? "";
  const containerRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const activeRoute = items
    .filter((item) => routeMatches(pathname, item.href))
    .sort((left, right) => right.href.length - left.href.length)[0]?.href;

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

  return (
    <div className={styles.dropdown} ref={containerRef}>
      <button
        type="button"
        className={[styles.trigger, activeRoute ? styles.activeTrigger : ""]
          .filter(Boolean)
          .join(" ")}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        onClick={() => setIsOpen((current) => !current)}
      >
        {label}
        <span className={styles.chevron} aria-hidden="true" />
      </button>

      {isOpen ? (
        <div className={styles.menu} role="menu">
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              role="menuitem"
              className={[
                styles.menuItem,
                item.href === activeRoute ? styles.activeItem : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => setIsOpen(false)}
            >
              <span>{item.label}</span>
              {item.badge && item.badge > 0 ? (
                <span className={styles.badge}>{item.badge}</span>
              ) : null}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
