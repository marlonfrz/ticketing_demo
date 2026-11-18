"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ROUTES, ROUTE_PREFIXES } from "../../routes/paths";

import styles from "./Footer.module.css";

export default function Footer() {
  const pathname = usePathname() ?? "";

  if (pathname.startsWith(ROUTE_PREFIXES.validator)) {
    return null;
  }

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.brandBlock}>
          <strong>Ticketing Demo</strong>
          <span>Gestion y venta de entradas para eventos.</span>
        </div>

        <nav className={styles.links} aria-label="Enlaces legales">
          <Link href={ROUTES.about}>Sobre nosotros</Link>
          <Link href={ROUTES.contact}>Contacto</Link>
          <Link href={ROUTES.terms}>Condiciones</Link>
          <Link href={ROUTES.privacy}>Privacidad</Link>
          <Link href={ROUTES.cookies}>Cookies</Link>
          <Link href={ROUTES.legalNotice}>Aviso legal</Link>
        </nav>
      </div>
    </footer>
  );
}
