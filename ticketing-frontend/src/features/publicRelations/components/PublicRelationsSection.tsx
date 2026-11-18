import { useCallback, useEffect, useState } from "react";
import Button from "../../../components/ui/Button";
import { getPublicRelationsSummaryRequest } from "../api/publicRelationsApi";

import styles from "./PublicRelationsSection.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema } from "../../../types/api";
import type { ManagedEvent } from "../../../types/domain";

function buildAbsoluteUrl(path: string): string {
  return `${window.location.origin}${path}`;
}

function formatDate(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

export default function PublicRelationsSection({ event, canManage }: { event: ManagedEvent; canManage: boolean }) {
  const [items, setItems] = useState<ApiSchema<"PublicRelationsSummaryResponse">[]>([]);
  const [openId, setOpenId] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState("");

  const registrationUrl = event?.id ? `/events/${event.id}/rrpp` : "";

  const loadData = useCallback(async () => {
    if (!event?.id || !canManage) return;

    try {
      setLoading(true);
      setErrorMsg("");
      const data = await getPublicRelationsSummaryRequest(event.id);
      setItems(data);
    } catch (error) {
      console.error("Error cargando RRPP:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo cargar la informacion de RRPP"));
    } finally {
      setLoading(false);
    }
  }, [canManage, event?.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const copyText = async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
      window.setTimeout(() => setCopied(""), 1800);
    } catch {
      setCopied("No se pudo copiar");
    }
  };

  if (!canManage || !event?.id) return null;

  return (
    <section className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>RRPP</h3>
          <p className={styles.subtitle}>
            Enlaces de relaciones publicas para atribuir ventas pagadas de este evento.
          </p>
        </div>
        <Button
          variant="primary"
          type="button"
          onClick={() => copyText(buildAbsoluteUrl(registrationUrl), "Enlace de registro copiado")}
        >
          Copiar enlace de registro
        </Button>
      </div>

      <div className={styles.linkBox}>
        <span>Registro RRPP</span>
        <code>{buildAbsoluteUrl(registrationUrl)}</code>
      </div>

      {copied ? <p className={styles.success}>{copied}</p> : null}
      {loading ? <p>Cargando RRPP...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {!loading && !errorMsg && items.length === 0 ? (
        <p className={styles.empty}>Todavia no hay RRPP registrados para este evento.</p>
      ) : null}

      <div className={styles.list}>
        {items.map((item) => {
          const isOpen = openId === item.id;
          const salesUrl = buildAbsoluteUrl(item.sales_url);

          return (
            <article className={styles.card} key={item.id}>
              <button
                className={styles.cardHeader}
                type="button"
                onClick={() => setOpenId(isOpen ? "" : item.id)}
              >
                <span>
                  <strong>{item.full_name}</strong>
                  <small>{item.phone}</small>
                </span>
                <span className={styles.salesCount}>
                  {item.total_sold} entradas
                </span>
              </button>

              {isOpen ? (
                <div className={styles.detail}>
                  <div className={styles.detailGrid}>
                    <p><strong>Email:</strong> {item.email || "-"}</p>
                    <p><strong>Red social:</strong> {item.social_handle || "-"}</p>
                    <p><strong>Estado:</strong> {item.status}</p>
                    <p><strong>Alta:</strong> {formatDate(item.created_at)}</p>
                  </div>

                  <div className={styles.linkRow}>
                    <code>{salesUrl}</code>
                    <Button
                      variant="primary"
                      size="small"
                      type="button"
                      onClick={() => copyText(salesUrl, `Enlace de ${item.full_name} copiado`)}
                    >
                      Copiar enlace
                    </Button>
                  </div>

                  <h4 className={styles.detailTitle}>Resumen total</h4>
                  {(item.by_ticket_type || []).length > 0 ? (
                    <div className={styles.breakdown}>
                      {item.by_ticket_type.map((entry) => (
                        <div className={styles.breakdownRow} key={entry.ticket_type_id}>
                          <span>{entry.ticket_type_name}</span>
                          <strong>{entry.quantity}</strong>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className={styles.empty}>Aun no tiene ventas atribuidas.</p>
                  )}

                  {(item.by_session || []).length > 0 ? (
                    <>
                      <h4 className={styles.detailTitle}>Por sesion</h4>
                      <div className={styles.sessions}>
                        {item.by_session.map((session) => (
                          <div className={styles.sessionBox} key={session.session_id}>
                            <div>
                              <strong>{session.location_name}</strong>
                              <span>{formatDate(session.starts_at)}</span>
                            </div>
                            <b>{session.quantity}</b>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : null}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
