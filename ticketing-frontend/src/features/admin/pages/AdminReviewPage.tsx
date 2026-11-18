import Link from "next/link";
import { redirect } from "next/navigation";
import { useEffect, useState } from "react";
import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import styles from "./AdminReviewPage.module.css";

import {
  approveEventReviewRequest,
  approveEventSessionReviewRequest,
  cancelEventReviewRequest,
  getAdminDashboardRequest,
  getEventReviewQueueRequest,
  requestEventChangesRequest,
  requestEventSessionChangesRequest,
  type ReviewActionPayload,
} from "../api/adminApi";
import { getEventStatusLabel } from "../../../utils/statusLabels";
import { ROUTES, routeTo } from "../../../routes/paths";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { AdminEvent } from "../../../types/domain";

type ReviewActionOptions = {
  includeReason?: boolean;
  requiresReason?: boolean;
};

type FeeForm = {
  platform_fee_type: string;
  platform_fee_value: string | number;
};

type ReviewAction = (
  id: EntityId,
  payload?: ReviewActionPayload
) => Promise<unknown>;

function getReviewKey(item: AdminEvent): string {
  return `${item.review_entity_type || "event"}:${item.review_entity_id || item.id}`;
}

function getReviewActionId(item: AdminEvent): EntityId {
  return item.review_entity_id || item.id;
}

function getReviewActions(item: AdminEvent) {
  if (item.review_entity_type === "session") {
    return {
      approve: approveEventSessionReviewRequest,
      requestChanges: requestEventSessionChangesRequest,
      approveMessage: "¿Aprobar esta sesión y pasarla a borrador?",
      changesMessage: "¿Devolver esta sesión al promotor para corregirla y revisarla de nuevo?",
      canSendReason: true,
      canCancel: false,
    };
  }

  return {
    approve: approveEventReviewRequest,
    requestChanges: requestEventChangesRequest,
    cancel: cancelEventReviewRequest,
    approveMessage: "¿Aprobar este evento y pasarlo a borrador?",
    changesMessage: "¿Devolver este evento al promotor para cambios?",
    cancelMessage: "¿Cancelar este evento?",
    canSendReason: false,
    canCancel: true,
  };
}

export default function AdminReviewPage() {
  const { isAdmin, authLoading } = useAuth();
  const [dashboard, setDashboard] = useState<ApiSchema<"AdminDashboardResponse"> | null>(null);
  const [events, setEvents] = useState<AdminEvent[]>([]);
  const [feeForms, setFeeForms] = useState<Record<string, FeeForm>>({});
  const [reviewReasons, setReviewReasons] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const [dashboardData, eventsData] = await Promise.all([
        getAdminDashboardRequest(),
        getEventReviewQueueRequest(),
      ]);
      setDashboard(dashboardData);
      setEvents(eventsData);
      window.dispatchEvent(
        new CustomEvent("admin-review-count-changed", {
          detail: {
            pendingReviews:
              dashboardData?.pending_event_reviews ?? eventsData.length,
          },
        })
      );
      setFeeForms(
        Object.fromEntries(
          eventsData.map((event) => [
            getReviewKey(event),
            {
              platform_fee_type: event.platform_fee_type || "percentage",
              platform_fee_value: event.platform_fee_value || "",
            },
          ])
        )
      );
      setReviewReasons((current) => ({
        ...Object.fromEntries(eventsData.map((event) => [getReviewKey(event), ""])),
        ...current,
      }));
    } catch (error) {
      console.error("Error cargando revisión admin:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudieron cargar los eventos a revisar"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadData();
    }
  }, [isAdmin]);

  const updateFeeForm = (
    reviewKey: string,
    field: keyof FeeForm,
    value: string
  ) => {
    setFeeForms((current) => ({
      ...current,
      [reviewKey]: {
        ...(current[reviewKey] || {
          platform_fee_type: "percentage",
          platform_fee_value: "",
        }),
        [field]: value,
      },
    }));
  };

  const updateReviewReason = (reviewKey: string, value: string) => {
    setReviewReasons((current) => ({
      ...current,
      [reviewKey]: value,
    }));
  };

  const runAction = async (
    action: ReviewAction,
    reviewItem: AdminEvent,
    message: string,
    payload: ReviewActionPayload | undefined = undefined,
    options: ReviewActionOptions = {}
  ) => {
    if (actionLoadingId) return;

    const reviewKey = getReviewKey(reviewItem);
    const reason = (reviewReasons[reviewKey] || "").trim();

    if (options.requiresReason && !reason) {
      alert("Indica un motivo para que el promotor sepa que debe corregir.");
      return;
    }

    const confirmed = window.confirm(message);
    if (!confirmed) return;

    const actionId = getReviewActionId(reviewItem);
    const finalPayload = options.includeReason
      ? { ...(payload || {}), reason }
      : payload;

    try {
      setActionLoadingId(reviewKey);
      await action(actionId, finalPayload);
      await loadData();
    } catch (error) {
      console.error("Error actualizando revisión:", error);
      alert(getApiErrorMessage(error, "No se pudo actualizar la revisión"));
    } finally {
      setActionLoadingId(null);
    }
  };

  if (authLoading) {
    return (
      <PageContainer title="Revisión admin">
        <p>Cargando...</p>
      </PageContainer>
    );
  }

  if (!isAdmin) {
    redirect(ROUTES.home);
  }

  return (
    <PageContainer title="Eventos a revisar">
      <div className={styles.summary}>
        <strong>{dashboard?.pending_event_reviews ?? events.length}</strong>
        <span> revisiones pendientes</span>
      </div>

      {loading ? <p>Cargando eventos...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {!loading && !errorMsg && events.length === 0 ? (
        <p>No hay eventos pendientes de revisión.</p>
      ) : null}

      <div className={styles.list}>
        {events.map((event) => {
          const reviewKey = getReviewKey(event);
          const reviewActions = getReviewActions(event);
          const feeForm = feeForms[reviewKey] || {
            platform_fee_type: "percentage",
            platform_fee_value: "",
          };
          const isActionLoading = actionLoadingId === reviewKey;
          const isAnyActionLoading = Boolean(actionLoadingId);
          const session = event.session;
          const reason = reviewReasons[reviewKey] || "";

          return (
            <article key={reviewKey} className={styles.card}>
              <div>
                <h3 className={styles.title}>{event.title}</h3>
                <p className={styles.badge}>
                  {session ? "Sesión pendiente" : "Evento pendiente"}
                </p>
                <p className={styles.text}>
                  {session ? session.location_name : event.location_name}
                </p>
                <p className={styles.text}>
                  Inicio: {new Date(session?.starts_at || event.starts_at).toLocaleString()}
                </p>
                <p className={styles.text}>
                  Estado: {getEventStatusLabel(session?.status || event.status)}
                </p>
                {session?.title ? (
                  <p className={styles.text}>Título sesión: {session.title}</p>
                ) : null}
                {session ? (
                  <p className={styles.text}>Aforo sesión: {session.capacity}</p>
                ) : null}
                {event.promoter ? (
                  <div className={styles.promoterBox}>
                    <span className={styles.promoterLabel}>Promotor</span>
                    <strong>{event.promoter.full_name}</strong>
                    <span>{event.promoter.email}</span>
                  </div>
                ) : (
                  <p className={styles.text}>Promotor: {event.promoter_id}</p>
                )}
                <Link href={routeTo.eventManage(event.id)}>Ver evento</Link>
              </div>

              <div className={styles.actions}>
                <label className={styles.field}>
                  Tarifa
                  <select
                  className={styles.input}
                  value={feeForm.platform_fee_type}
                  disabled={isAnyActionLoading}
                  onChange={(e) =>
                      updateFeeForm(
                        reviewKey,
                        "platform_fee_type",
                        e.target.value
                      )
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
                    disabled={isAnyActionLoading}
                    onChange={(e) =>
                      updateFeeForm(
                        reviewKey,
                        "platform_fee_value",
                        e.target.value
                      )
                    }
                  />
                </label>

                <Button
                  variant="primary"
                  disabled={isAnyActionLoading}
                  onClick={() =>
                    runAction(
                      reviewActions.approve,
                      event,
                      reviewActions.approveMessage,
                      {
                        platform_fee_type: feeForm.platform_fee_type,
                        platform_fee_value: Number(
                          feeForm.platform_fee_value || 0
                        ),
                      }
                    )
                  }
                >
                  {isActionLoading ? "Procesando..." : "Aprobar"}
                </Button>
                {reviewActions.canSendReason ? (
                  <label className={styles.reasonField}>
                    Motivo para el promotor
                    <textarea
                      className={styles.reasonInput}
                      value={reason}
                      disabled={isAnyActionLoading}
                      maxLength={1000}
                      rows={3}
                      placeholder="Ej. Falta información del lugar o el aforo no coincide con los tickets."
                      onChange={(e) => updateReviewReason(reviewKey, e.target.value)}
                    />
                  </label>
                ) : null}
                <Button
                  disabled={isAnyActionLoading}
                  onClick={() =>
                    runAction(
                      reviewActions.requestChanges,
                      event,
                      reviewActions.changesMessage,
                      undefined,
                      {
                        includeReason: reviewActions.canSendReason,
                        requiresReason: reviewActions.canSendReason,
                      }
                    )
                  }
                >
                  {session ? "Devolver para nueva revisión" : "Pedir cambios"}
                </Button>
                {reviewActions.canCancel && reviewActions.cancel ? (
                  <Button
                    variant="danger"
                    disabled={isAnyActionLoading}
                    onClick={() =>
                      runAction(
                        reviewActions.cancel,
                        event,
                        reviewActions.cancelMessage,
                        undefined,
                        {
                          includeReason: reviewActions.canSendReason,
                          requiresReason: reviewActions.canSendReason,
                        }
                      )
                    }
                  >
                    Cancelar
                  </Button>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
    </PageContainer>
  );
}

