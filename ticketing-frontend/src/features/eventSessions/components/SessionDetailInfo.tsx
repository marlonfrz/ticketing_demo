import { type ReactNode } from "react";

import { getEventStatusLabel } from "../../../utils/statusLabels";
import { getGoogleMapsSearchUrl } from "../../../utils/maps";
import { formatDateTime } from "../../../utils/dateTime";
import type { EventSession } from "../../../types/domain";

import styles from "./SessionDetailInfo.module.css";

type SessionDetailInfoProps = {
  session: EventSession;
  actions?: ReactNode;
};

export default function SessionDetailInfo({
  session,
  actions,
}: SessionDetailInfoProps) {
  const mapsUrl = getGoogleMapsSearchUrl(session.location_address);

  return (
    <section className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Detalle de sesión</p>
          <h2 className={styles.title}>{session.location_name}</h2>
        </div>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </div>

      <div className={styles.grid}>
        <p className={styles.item}>
          <strong>Estado</strong>
          <span>{getEventStatusLabel(session.status)}</span>
        </p>
        <p className={styles.item}>
          <strong>Inicio</strong>
          <span>{formatDateTime(session.starts_at)}</span>
        </p>
        <p className={styles.item}>
          <strong>Fin</strong>
          <span>{session.ends_at ? formatDateTime(session.ends_at) : "No definido"}</span>
        </p>
        <p className={styles.item}>
          <strong>Aforo</strong>
          <span>{session.capacity}</span>
        </p>
        <p className={styles.itemWide}>
          <strong>Dirección</strong>
          {session.location_address ? (
            mapsUrl ? (
              <a href={mapsUrl} target="_blank" rel="noopener noreferrer">
                {session.location_address}
              </a>
            ) : (
              <span>{session.location_address}</span>
            )
          ) : (
            <span>No definida</span>
          )}
        </p>
        <p className={styles.item}>
          <strong>Tipos de entrada</strong>
          <span>{session.ticket_types_count || 0}</span>
        </p>
        <p className={styles.item}>
          <strong>Entradas vendidas</strong>
          <span>{session.sold_tickets_count || 0}</span>
        </p>
      </div>
    </section>
  );
}
