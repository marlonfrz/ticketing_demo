import { useRouter } from "next/navigation";
import { type ChangeEvent, type SubmitEvent, useState } from "react";

import Button from "../../../components/ui/Button";
import Modal from "../../../components/ui/Modal";
import ConfirmDialog from "../../../components/ui/ConfirmDialog";
import {
  approveEventSessionReviewRequest,
  requestEventSessionChangesRequest,
} from "../../admin/api/adminApi";
import {
  createEventSessionRequest,
  deleteEventSessionRequest,
  duplicateEventSessionRequest,
  publishAllEventSessionsRequest,
  submitEventSessionReviewRequest,
  submitAllEventSessionsReviewRequest,
} from "../api/eventSessionsApi";
import { getEventStatusLabel } from "../../../utils/statusLabels";
import { getApiErrorMessage } from "../../../api/errors";
import { routeTo } from "../../../routes/paths";
import type { EntityId } from "../../../types/api";
import type { Event, EventSession } from "../../../types/domain";
import SessionActionsMenu from "./SessionActionsMenu";
import SessionForm, {
  buildInitialSessionForm,
  buildSessionPayload,
  onlyInteger,
} from "./SessionForm";

import styles from "./EventSessionsSection.module.css";

type ConfirmAction = {
  title: string;
  message: string;
  confirmLabel: string;
  tone?: "default" | "danger";
  run: () => Promise<unknown>;
  errorMessage: string;
};

type CancelReviewState = {
  session: EventSession;
  reason: string;
};

type EventSessionsSectionProps = {
  event: Event;
  selectedSessionId: EntityId | null;
  onSelectSession: (sessionId: EntityId) => void;
  canManage: boolean;
  isAdmin?: boolean;
  onChanged?: () => void | Promise<void>;
};

function formatSession(session: EventSession): string {
  return new Date(session.starts_at).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function sortSessionsForDisplay(sessions: EventSession[]): EventSession[] {
  return [...sessions].sort((a, b) => {
    const aFinished = a.status === "finished" ? 1 : 0;
    const bFinished = b.status === "finished" ? 1 : 0;

    if (aFinished !== bFinished) {
      return aFinished - bFinished;
    }

    return new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime();
  });
}

export default function EventSessionsSection({
  event,
  selectedSessionId,
  onSelectSession,
  canManage,
  isAdmin = false,
  onChanged,
}: EventSessionsSectionProps) {
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(buildInitialSessionForm);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);
  const [cancelReview, setCancelReview] = useState<CancelReviewState | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);

  const sessions = event.sessions || [];
  const orderedSessions = sortSessionsForDisplay(sessions);
  const selectedSession =
    sessions.find((session) => session.id === selectedSessionId) || null;
  const eventAllowsSessionActions = ![
    "in_review",
    "archived",
    "disabled",
    "finished",
    "cancelled",
  ].includes(event.status);
  const canCreateSession = canManage && eventAllowsSessionActions;
  const hasSessionsPendingReview = sessions.some(
    (session) => ["not_reviewed", "cancelled"].includes(session.status)
  );
  const hasApprovedSessionsReadyToPublish = sessions.some((session) =>
    session.status === "draft"
  );
  const canDuplicateSelected = canManage && selectedSession;
  const canSubmitAllReviews =
    canManage && eventAllowsSessionActions && hasSessionsPendingReview;
  const canPublishAllSessions =
    canManage &&
    isAdmin &&
    event.status === "published" &&
    hasApprovedSessionsReadyToPublish;

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((current) => ({
      ...current,
      [name]: name === "capacity" ? onlyInteger(value) : value,
    }));
  };

  const handleCreate = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    try {
      setLoading(true);
      await createEventSessionRequest(
        event.id,
        buildSessionPayload(form)
      );
      setShowForm(false);
      setForm(buildInitialSessionForm());
      await onChanged?.();
    } catch (error) {
      console.error("Error creando sesión:", error);
      alert(getApiErrorMessage(error, "No se pudo crear la sesión"));
    } finally {
      setLoading(false);
    }
  };

  const openSessionDetail = (session: EventSession) => {
    onSelectSession(session.id);
    router.push(routeTo.eventSessionManage(event.id, session.id));
  };

  const cancelForm = () => {
    setShowForm(false);
    setForm(buildInitialSessionForm());
  };

  const handleDuplicate = async (sessionId: EntityId) => {
    if (loading) return;

    try {
      setLoading(true);
      await duplicateEventSessionRequest(sessionId);
      await onChanged?.();
    } catch (error) {
      console.error("Error duplicando sesión:", error);
      alert(getApiErrorMessage(error, "No se pudo duplicar la sesión"));
    } finally {
      setLoading(false);
    }
  };

  const requestDuplicate = (session: EventSession) => {
    const isEmpty = Number(session.ticket_types_count || 0) === 0;

    if (!isEmpty) {
      handleDuplicate(session.id);
      return;
    }

    setConfirmAction({
      title: "Duplicar sesión sin tickets",
      message:
        "Vas a duplicar una sesión que no tiene tickets creados. La nueva sesión se creará sin entradas y tendrás que crearlas manualmente. ¿Estás seguro?",
      confirmLabel: "Duplicar sesión",
      run: () => duplicateEventSessionRequest(session.id),
      errorMessage: "No se pudo duplicar la sesión",
    });
  };

  const requestDelete = (session: EventSession) => {
    setConfirmAction({
      title: "Borrar sesión",
      message:
        "Vas a borrar esta sesión. Solo se permite cuando el evento y la sesión están en draft y no tienen entradas vendidas o generadas.",
      confirmLabel: "Borrar sesión",
      tone: "danger",
      run: () => deleteEventSessionRequest(session.id),
      errorMessage: "No se pudo borrar la sesión",
    });
  };

  const requestPublishAll = () => {
    setConfirmAction({
      title: "Publicar sesiones aprobadas",
      message:
        "Vas a publicar las sesiones aprobadas junto con sus tickets.",
      confirmLabel: "Publicar sesiones aprobadas",
      run: () => publishAllEventSessionsRequest(event.id),
      errorMessage: "No se pudieron publicar las sesiones",
    });
  };

  const requestSubmitReview = (session: EventSession) => {
    setConfirmAction({
      title: "Enviar sesión a revisión",
      message:
        "Vas a enviar esta sesión a revisión. Un administrador revisará fecha, ubicación, entradas y grupos de venta.",
      confirmLabel: "Enviar a revisión",
      run: () => submitEventSessionReviewRequest(session.id),
      errorMessage: "No se pudo enviar la sesión a revisión",
    });
  };

  const requestApproveReview = (session: EventSession) => {
    setConfirmAction({
      title: "Aprobar sesión",
      message:
        "Vas a aprobar esta sesión. Pasará a estado aprobado y podrá publicarse cuando corresponda.",
      confirmLabel: "Aprobar sesión",
      run: () => approveEventSessionReviewRequest(session.id),
      errorMessage: "No se pudo aprobar la sesión",
    });
  };

  const requestChangesReview = (session: EventSession) => {
    setCancelReview({ session, reason: "" });
  };

  const closeCancelReview = () => {
    if (confirmLoading) return;
    setCancelReview(null);
  };

  const handleCancelReview = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!cancelReview || confirmLoading) return;

    const reason = cancelReview.reason.trim();
    if (!reason) {
      alert("Indica un motivo para devolver la sesión.");
      return;
    }

    try {
      setConfirmLoading(true);
      await requestEventSessionChangesRequest(cancelReview.session.id, { reason });
      setCancelReview(null);
      await onChanged?.();
    } catch (error) {
      console.error("Error devolviendo revisión de sesión:", error);
      alert(getApiErrorMessage(error, "No se pudo devolver la sesión"));
    } finally {
      setConfirmLoading(false);
    }
  };

  const requestSubmitAllReviews = () => {
    setConfirmAction({
      title: "Enviar todas a revisión",
      message:
        "Vas a enviar a revisión todas las sesiones no revisadas o pendientes de cambios. Cada sesión llegará a admin como una revisión independiente.",
      confirmLabel: "Enviar todas",
      run: () => submitAllEventSessionsReviewRequest(event.id),
      errorMessage: "No se pudieron enviar las sesiones a revisión",
    });
  };

  const runConfirmedAction = async () => {
    if (!confirmAction || confirmLoading) return;

    try {
      setConfirmLoading(true);
      await confirmAction.run();
      setConfirmAction(null);
      await onChanged?.();
    } catch (error) {
      console.error("Error ejecutando acción de sesión:", error);
      alert(getApiErrorMessage(error, confirmAction.errorMessage));
    } finally {
      setConfirmLoading(false);
    }
  };

  return (
    <section className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Sesiones del evento</h3>
          <p className={styles.subtitle}>
            Cada sesión tiene su fecha, lugar, aforo, tickets y ventas.
          </p>
        </div>

        {canCreateSession ? (
          <Button
            variant="primary"
            onClick={() => {
              setShowForm(true);
              setForm(buildInitialSessionForm());
            }}
            disabled={loading}
          >
            Crear sesión
          </Button>
        ) : null}
      </div>

      <div className={styles.sessionGrid}>
        {orderedSessions.map((session) => {
          const canDeleteSession =
            canManage && event.status === "draft" && session.status === "draft";
          const canSubmitSessionReview =
            canManage &&
            eventAllowsSessionActions &&
            ["not_reviewed", "cancelled"].includes(session.status);
          const canReviewSession =
            canManage && isAdmin && session.status === "in_review";

          return (
            <article
              key={session.id}
              className={`${styles.sessionCard} ${
                selectedSessionId === session.id ? styles.selected : ""
              } ${session.status === "finished" ? styles.finishedSession : ""}`}
            >
              <div className={styles.cardHeader}>
                <strong>{session.location_name}</strong>
                <SessionActionsMenu
                  actionLoading={loading || confirmLoading}
                  onOpenDetail={() => openSessionDetail(session)}
                  {...(canDeleteSession
                    ? { onDelete: () => requestDelete(session) }
                    : {})}
                />
              </div>

              <button
                className={styles.cardContentButton}
                type="button"
                onClick={() => onSelectSession(session.id)}
              >
                <span>{formatSession(session)}</span>
                <small>{getEventStatusLabel(session.status)}</small>
                <em>Aforo {session.capacity}</em>
                <span className={styles.metaLine}>
                  {session.ticket_types_count || 0} tipos de entrada -{" "}
                  {session.sold_tickets_count || 0} vendidas
                </span>
              </button>

              {canSubmitSessionReview || canReviewSession ? (
                <div className={styles.cardReviewAction}>
                  <span>
                    {canReviewSession
                      ? "Sesión en revisión"
                      : "Sesión pendiente de revisión"}
                  </span>
                  <div className={styles.cardReviewButtons}>
                    {canReviewSession ? (
                      <>
                        <Button
                          variant="primarySoft"
                          size="small"
                          type="button"
                          disabled={loading || confirmLoading}
                          onClick={() => requestApproveReview(session)}
                        >
                          Aprobar
                        </Button>
                        <Button
                          variant="primarySoft"
                          size="small"
                          type="button"
                          disabled={loading || confirmLoading}
                          onClick={() => requestChangesReview(session)}
                        >
                          Pedir cambios
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="primarySoft"
                        size="small"
                        type="button"
                        disabled={loading || confirmLoading}
                        onClick={() => requestSubmitReview(session)}
                      >
                        Enviar a revisión
                      </Button>
                    )}
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      {canManage && sessions.length > 0 ? (
        <div className={styles.actions}>
          {canDuplicateSelected ? (
            <Button
              type="button"
              disabled={loading}
              onClick={() => requestDuplicate(selectedSession)}
            >
              Duplicar sesión seleccionada
            </Button>
          ) : null}
          {canSubmitAllReviews ? (
            <Button
              variant="primarySoft"
              type="button"
              disabled={loading}
              onClick={requestSubmitAllReviews}
            >
              Enviar todas a revisión
            </Button>
          ) : null}
          {canPublishAllSessions ? (
            <Button
              variant="primarySoft"
              type="button"
              disabled={loading}
              onClick={requestPublishAll}
            >
              Publicar sesiones aprobadas
            </Button>
          ) : null}
        </div>
      ) : null}

      <Modal isOpen={showForm} title="Crear sesión" onClose={cancelForm}>
        <SessionForm
          form={form}
          loading={loading}
          mode="create"
          onCancel={cancelForm}
          onChange={handleChange}
          onSubmit={handleCreate}
        />
      </Modal>

      <Modal
        isOpen={!!cancelReview}
        title="Pedir cambios"
        onClose={closeCancelReview}
      >
        <form className={styles.cancelReviewForm} onSubmit={handleCancelReview}>
          <label className={styles.cancelReviewField}>
            Motivo para el promotor
            <textarea
              className={styles.cancelReviewInput}
              value={cancelReview?.reason ?? ""}
              rows={4}
              maxLength={1000}
              disabled={confirmLoading}
              placeholder="Explica qué debe corregirse antes de volver a revisión."
              onChange={(event) =>
                setCancelReview((current) =>
                  current ? { ...current, reason: event.target.value } : current
                )
              }
            />
          </label>
          <div className={styles.cancelReviewActions}>
            <Button
              type="button"
              disabled={confirmLoading}
              onClick={closeCancelReview}
            >
              Volver
            </Button>
            <Button
              variant="primarySoft"
              type="submit"
              disabled={confirmLoading}
            >
              {confirmLoading ? "Enviando..." : "Devolver sesión"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!confirmAction}
        title={confirmAction?.title}
        message={confirmAction?.message ?? ""}
        confirmLabel={confirmAction?.confirmLabel}
        tone={confirmAction?.tone}
        loading={confirmLoading}
        onCancel={() => setConfirmAction(null)}
        onConfirm={runConfirmedAction}
      />
    </section>
  );
}
