"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import useAuth from "../../hooks/useAuth";
import {
  getAdminDashboardRequest,
  getValidationQuotaRequestsAdminRequest,
} from "../../features/admin/api/adminApi";
import { ROUTES, ROUTE_PREFIXES } from "../../routes/paths";
import NavDropdown, { type NavDropdownItem } from "./NavDropdown";
import UserMenu from "./UserMenu";

import styles from "./Navbar.module.css";

export default function Navbar() {
  const pathname = usePathname() ?? "";
  const router = useRouter();
  const { isAuthenticated, canAccessPromoter, isAdmin, logout, user } = useAuth();
  const [pendingReviews, setPendingReviews] = useState(0);
  const [pendingValidationRequests, setPendingValidationRequests] = useState(0);

  useEffect(() => {
    if (!isAdmin) {
      return undefined;
    }

    let cancelled = false;

    const loadPendingReviews = async () => {
      try {
        const [dashboard, validationRequests] = await Promise.all([
          getAdminDashboardRequest(),
          getValidationQuotaRequestsAdminRequest("pending"),
        ]);
        if (!cancelled) {
          setPendingReviews(Number(dashboard.pending_event_reviews || 0));
          setPendingValidationRequests(validationRequests.length);
        }
      } catch (error) {
        console.error("Error cargando contador de revisiones:", error);
      }
    };

    const handlePendingReviewsChanged = (
      event: WindowEventMap["admin-review-count-changed"]
    ) => {
      const { pendingReviews = 0 } = event.detail;
      setPendingReviews(Number(pendingReviews));
    };
    const handlePendingValidationChanged = (
      event: WindowEventMap["admin-validation-count-changed"]
    ) => {
      const { pendingValidationRequests = 0 } = event.detail;
      setPendingValidationRequests(
        Number(pendingValidationRequests)
      );
    };

    loadPendingReviews();
    window.addEventListener(
      "admin-review-count-changed",
      handlePendingReviewsChanged
    );
    window.addEventListener(
      "admin-validation-count-changed",
      handlePendingValidationChanged
    );

    return () => {
      cancelled = true;
      window.removeEventListener(
        "admin-review-count-changed",
        handlePendingReviewsChanged
      );
      window.removeEventListener(
        "admin-validation-count-changed",
        handlePendingValidationChanged
      );
    };
  }, [isAdmin]);

  const visiblePendingReviews = isAdmin ? pendingReviews : 0;
  const visiblePendingValidationRequests = isAdmin
    ? pendingValidationRequests
    : 0;
  const helpItems: NavDropdownItem[] = [
    { label: "Atención al cliente", href: ROUTES.help },
    { label: "Preguntas frecuentes", href: ROUTES.faq },
  ];
  const managementItems: NavDropdownItem[] = [
    ...(canAccessPromoter
      ? [{ label: "Área de promotor", href: ROUTES.promoter }]
      : []),
    ...(isAdmin
      ? [
          {
            label: "Revisión de eventos",
            href: ROUTES.adminReviews,
            badge: visiblePendingReviews,
          },
          { label: "Administración", href: ROUTES.adminUsers },
          {
            label: "Solicitudes de validadores",
            href: ROUTES.adminValidationRequests,
            badge: visiblePendingValidationRequests,
          },
        ]
      : []),
  ];

  const handleLogout = async () => {
    await logout();
    router.push(ROUTES.home);
  };

  const getNavLinkClass = (route: string) =>
    [
      styles.navLink,
      pathname === route ||
      (route !== ROUTES.home && pathname.startsWith(`${route}/`))
        ? styles.activeLink
        : "",
    ]
      .filter(Boolean)
      .join(" ");

  if (pathname.startsWith(ROUTE_PREFIXES.validator)) {
    return null;
  }

  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        <Link href={ROUTES.home} className={styles.brand} aria-label="Ticketing Demo - Inicio">
          <span className={styles.brandMark} aria-hidden="true">T</span>
          <span className={styles.brandName}>Ticketing Demo</span>
        </Link>

        <div className={styles.navigation}>
          <Link href={ROUTES.home} className={getNavLinkClass(ROUTES.home)}>
            Eventos
          </Link>
          {!canAccessPromoter && !isAdmin ? (
            <Link
              href={ROUTES.organize}
              className={getNavLinkClass(ROUTES.organize)}
            >
              Organizar
            </Link>
          ) : null}
          <NavDropdown label="Ayuda" items={helpItems} />
          {managementItems.length > 0 ? (
            <NavDropdown label="Gestión" items={managementItems} />
          ) : null}
        </div>

        <div className={styles.right}>
          {isAuthenticated ? (
            <UserMenu
              userName={user?.full_name || "Cuenta"}
              onLogout={handleLogout}
            />
          ) : (
            <div className={styles.authLinks}>
              <Link href={ROUTES.login} className={styles.loginLink}>Entrar</Link>
              <Link href={ROUTES.register} className={styles.registerLink}>Crear cuenta</Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
