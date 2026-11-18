import Link from "next/link";
import { redirect, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ButtonLink from "../../../components/ui/ButtonLink";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import { getEventStatusLabel, getUserStatusLabel } from "../../../utils/statusLabels";
import { getAdminPromoterEventsRequest } from "../api/adminApi";
import { ROUTES, routeTo } from "../../../routes/paths";
import styles from "./AdminUsersPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema } from "../../../types/api";

function formatDate(value?: string | null): string {
  if (!value) return "Sin fecha";
  return new Date(value).toLocaleString();
}

export default function AdminPromoterEventsPage() {
  const promoterId = useParams<{ promoterId: string }>()?.promoterId;
  const { isAdmin, authLoading } = useAuth();
  const [data, setData] = useState<ApiSchema<"AdminPromoterEventsResponse"> | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (!isAdmin || !promoterId) return;

    const loadPromoterEvents = async () => {
      try {
        setLoading(true);
        setErrorMsg("");
        const response = await getAdminPromoterEventsRequest(promoterId);
        setData(response);
      } catch (error) {
        console.error("Error cargando eventos del promotor:", error);
        setErrorMsg(getApiErrorMessage(error, "No se pudieron cargar los eventos del promotor"));
      } finally {
        setLoading(false);
      }
    };

    loadPromoterEvents();
  }, [isAdmin, promoterId]);

  if (authLoading) {
    return (
      <PageContainer title="Eventos del promotor">
        <p>Cargando...</p>
      </PageContainer>
    );
  }

  if (!isAdmin) {
    redirect(ROUTES.home);
  }

  return (
    <PageContainer title="Eventos del promotor">
      <div className={styles.navRow}>
        <ButtonLink href={ROUTES.adminUsers}>
          Volver a admin
        </ButtonLink>
      </div>

      {loading ? <p>Cargando eventos...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {!loading && !errorMsg && data ? (
        <>
          <section className={styles.section}>
            <div className={styles.stat}>
              <span>Promotor</span>
              <strong>{data.promoter.full_name}</strong>
              <span className={styles.muted}>{data.promoter.email}</span>
              <span>{getUserStatusLabel(data.promoter.status)}</span>
            </div>
          </section>

          <section className={styles.section}>
            <h3 className={styles.title}>Eventos</h3>

            {data.events.length === 0 ? (
              <p>Este promotor todavia no tiene eventos.</p>
            ) : null}

            <div className={styles.table}>
              {data.events.map((event) => (
                <Link
                  key={event.id}
                  href={routeTo.eventManage(event.id)}
                  className={styles.eventRowLink}
                >
                  <div>
                    <strong>{event.title}</strong>
                    <p className={styles.muted}>{event.location_name || "Sin ubicacion"}</p>
                  </div>
                  <div>
                    <span>{data.promoter.full_name}</span>
                    <p className={styles.muted}>{data.promoter.email}</p>
                  </div>
                  <div>
                    <span>{formatDate(event.starts_at)}</span>
                    <p className={styles.muted}>Creado: {formatDate(event.created_at)}</p>
                  </div>
                  <span>{getEventStatusLabel(event.status)}</span>
                </Link>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </PageContainer>
  );
}
