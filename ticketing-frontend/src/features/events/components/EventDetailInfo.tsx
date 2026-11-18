import { type ReactNode, type SubmitEvent, useEffect, useState } from "react";
import Image from "next/image";

import Button from "../../../components/ui/Button";
import { getEventStatusLabel } from "../../../utils/statusLabels";
import { getMediaUrl } from "../../../utils/media";
import { getNextEventSession } from "../../../utils/eventSessions";
import { getGoogleMapsSearchUrl } from "../../../utils/maps";
import { formatDateTime } from "../../../utils/dateTime";
import styles from "./EventDetailInfo.module.css";
import type { ApiSchema } from "../../../types/api";
import type { EventSession, FinancialSummary, ManagedEvent } from "../../../types/domain";

function formatMoney(value: string | number | null | undefined, currency = "EUR"): string {
  return `${Number(value || 0).toFixed(2)} ${currency}`;
}

function formatFee(type?: string | null, value?: string | number | null): string {
  if (!type || value === null || value === undefined) return "No definida";
  if (type === "percentage") return `${Number(value).toFixed(2)}%`;
  return `${Number(value).toFixed(2)} EUR por entrada`;
}

const APPROVED_EVENT_STATUSES = [
  "draft",
  "published",
  "sold_out",
  "unpublished",
  "finished",
];

type EventDetailInfoProps = {
  event: ManagedEvent;
  selectedSession?: EventSession | null;
  isManageView?: boolean;
  isAdmin?: boolean;
  onUpdateFee?: (payload: ApiSchema<"AdminEventFeeRequest">) => void | Promise<void>;
  feeLoading?: boolean;
  headerActions?: ReactNode;
  footerActions?: ReactNode;
};

export default function EventDetailInfo({
  event,
  selectedSession = null,
  isManageView = false,
  isAdmin = false,
  onUpdateFee,
  feeLoading = false,
  headerActions,
  footerActions,
}: EventDetailInfoProps) {
  const [feeForm, setFeeForm] = useState({
    platform_fee_type: event.platform_fee_type || "percentage",
    platform_fee_value: event.platform_fee_value || "",
  });

  useEffect(() => {
    queueMicrotask(() => {
      setFeeForm({
        platform_fee_type: event.platform_fee_type || "percentage",
        platform_fee_value: event.platform_fee_value || "",
      });
    });
  }, [event.platform_fee_type, event.platform_fee_value]);

  const summary = event.financial_summary;
  const currency = summary?.currency || "EUR";
  const hasPassedReview = APPROVED_EVENT_STATUSES.includes(event.status);
  const showPromoterManagementInfo = isManageView && !isAdmin;
  const showPromoterFinance = showPromoterManagementInfo && hasPassedReview;
  const showAdminManagementInfo = isManageView && isAdmin;
  const totalSessionCapacity = (event.sessions || []).reduce(
    (total, session) => total + Number(session.capacity || 0),
    0
  );
  const imageUrl = getMediaUrl(event.image_url);
  const showSessionData = !isManageView;
  const displaySession = showSessionData
    ? selectedSession || getNextEventSession(event)
    : null;
  const mapsUrl = getGoogleMapsSearchUrl(displaySession?.location_address);

  const handleFeeSubmit = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    await onUpdateFee?.({
      platform_fee_type: feeForm.platform_fee_type,
      platform_fee_value: Number(feeForm.platform_fee_value || 0),
    });
  };

  return (
    <div className={styles.box}>
      <div className={styles.summaryHeader}>
        {imageUrl ? (
          <Image
            className={styles.eventImage}
            src={imageUrl}
            alt={event.title}
            width={1200}
            height={675}
            sizes="(max-width: 640px) 85vw, 250px"
            quality={92}
            priority
          />
        ) : null}

        <div className={styles.summaryContent}>
          <div className={styles.titleRow}>
            <h2 className={styles.title}>{event.title}</h2>
            {headerActions}
          </div>

          {event.description ? (
            <p className={styles.description}>{event.description}</p>
          ) : null}

          {displaySession ? (
            <>
              <p className={styles.text}>
                <strong>Fecha:</strong>{" "}
                {formatDateTime(displaySession.starts_at)}
              </p>
              <p className={styles.text}>
                <strong>Lugar:</strong> {displaySession.location_name}
              </p>
              {displaySession.location_address ? (
                <p className={styles.text}>
                  <strong>Dirección:</strong>{" "}
                  {mapsUrl ? (
                    <a
                      className={styles.addressLink}
                      href={mapsUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {displaySession.location_address}
                    </a>
                  ) : (
                    displaySession.location_address
                  )}
                </p>
              ) : null}
            </>
          ) : null}
        </div>
      </div>

      {showPromoterFinance && summary ? (
        <div className={styles.promoterFinance}>
          <h3 className={styles.sectionTitle}>Resumen de ventas</h3>
          <FinanceSummaryGrid summary={summary} currency={currency} />

          {summary?.complimentary_tickets_by_type?.length ? (
            <InviteSummary summary={summary} />
          ) : null}
        </div>
      ) : null}

      {showPromoterManagementInfo ? (
        <div className={styles.managementInfo}>
          <h3 className={styles.sectionTitle}>Datos del evento</h3>

          <div className={styles.infoGrid}>
            <p className={styles.infoItem}>
              <strong>Estado</strong>
              <span>{getEventStatusLabel(event.status)}</span>
            </p>

            <p className={styles.infoItem}>
              <strong>Sesiones</strong>
              <span>{event.sessions?.length || 0}</span>
            </p>

            <p className={styles.infoItem}>
              <strong>Aforo total sesiones</strong>
              <span>{totalSessionCapacity}</span>
            </p>

            {hasPassedReview ? (
              <>
                <p className={styles.infoItem}>
                  <strong>Tarifa por entrada</strong>
                  <span>
                    {formatFee(
                      event.platform_fee_type,
                      event.platform_fee_value
                    )}
                  </span>
                </p>
              </>
            ) : null}
          </div>
        </div>
      ) : null}

      {showAdminManagementInfo ? (
        <div className={styles.adminBox}>
          <div className={styles.adminHeader}>
            <h3 className={styles.adminTitle}>Información de gestión</h3>
            {footerActions ? (
              <div className={styles.adminActions}>{footerActions}</div>
            ) : null}
          </div>

          <p className={styles.text}>
            <strong>Estado:</strong> {getEventStatusLabel(event.status)}
          </p>

          <p className={styles.text}>
            <strong>Sesiones:</strong> {event.sessions?.length || 0}
          </p>

          <p className={styles.text}>
            <strong>Aforo total sesiones:</strong> {totalSessionCapacity}
          </p>

          <p className={styles.text}>
            <strong>Tarifa por entrada:</strong>{" "}
            {formatFee(event.platform_fee_type, event.platform_fee_value)}
          </p>

          {isAdmin ? (
            <form className={styles.feeForm} onSubmit={handleFeeSubmit}>
              <label className={styles.field}>
                Tipo de tarifa
                <select
                  className={styles.input}
                  value={feeForm.platform_fee_type}
                  onChange={(e) =>
                    setFeeForm((current) => ({
                      ...current,
                      platform_fee_type: e.target.value,
                    }))
                  }
                >
                  <option value="percentage">Porcentaje</option>
                  <option value="fixed">Fijo por entrada</option>
                </select>
              </label>

              <label className={styles.field}>
                Valor
                <input
                  className={styles.input}
                  type="number"
                  min="0"
                  step="0.01"
                  value={feeForm.platform_fee_value}
                  onChange={(e) =>
                    setFeeForm((current) => ({
                      ...current,
                      platform_fee_value: e.target.value,
                    }))
                  }
                />
              </label>

              <Button variant="primary" type="submit" disabled={feeLoading}>
                {feeLoading ? "Guardando..." : "Guardar tarifa"}
              </Button>
            </form>
          ) : null}

          {summary ? (
            <FinanceSummaryGrid summary={summary} currency={currency} />
          ) : null}

          {summary?.complimentary_tickets_by_type?.length ? (
            <InviteSummary summary={summary} />
          ) : null}

          <p className={styles.text}>
            <strong>Fecha publicación evento:</strong>{" "}
            {event.publish_at
              ? formatDateTime(event.publish_at)
              : "No definida"}
          </p>

        </div>
      ) : null}

      {footerActions && !showAdminManagementInfo ? (
        <div className={styles.footerActions}>{footerActions}</div>
      ) : null}
    </div>
  );
}

function FinanceSummaryGrid({ summary, currency }: { summary: FinancialSummary; currency: string }) {
  return (
    <div className={styles.financeGrid}>
      <div className={styles.metric}>
        <span className={styles.metricLabel}>Entradas vendidas</span>
        <strong>{summary.tickets_sold}</strong>
      </div>
      <div className={styles.metric}>
        <span className={styles.metricLabel}>Recaudado</span>
        <strong>{formatMoney(summary.gross_revenue, currency)}</strong>
      </div>
      <div className={styles.metric}>
        <span className={styles.metricLabel}>Para promotor</span>
        <strong>{formatMoney(summary.promoter_revenue, currency)}</strong>
      </div>
      <div className={styles.metric}>
        <span className={styles.metricLabel}>Para plataforma</span>
        <strong>{formatMoney(summary.platform_revenue, currency)}</strong>
      </div>
      <div className={styles.metric}>
        <span className={styles.metricLabel}>Invitadas</span>
        <strong>{summary.complimentary_tickets_total || 0}</strong>
      </div>
    </div>
  );
}

function InviteSummary({ summary }: { summary: FinancialSummary }) {
  return (
    <div className={styles.inviteSummary}>
      <strong>Invitaciones por tipo:</strong>{" "}
      {(summary.complimentary_tickets_by_type ?? [])
        .map((item) => `${item.ticket_type_name}: ${item.quantity}`)
        .join(", ")}
    </div>
  );
}
