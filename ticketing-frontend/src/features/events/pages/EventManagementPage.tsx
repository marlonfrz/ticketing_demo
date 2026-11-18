"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PageContainer from "../../../components/ui/PageContainer";
import ConfirmDialog from "../../../components/ui/ConfirmDialog";
import useAuth from "../../../hooks/useAuth";
import { getManageEventByIdRequest } from "../api/eventsApi";
import EventDetailInfo from "../components/EventDetailInfo";
import {
  deleteEventRequest,
  publishEventRequest,
  unpublishEventRequest,
} from "../../promoter/api/promoterApi";
import {
  EventActionsMenu,
  PublishEventButton,
  UnpublishEventButton,
} from "../components/EventManagementActions";
import EventModal from "../../promoter/modals/EventModal";
import SaleGroupsSection from "../../saleGroups/components/SaleGroupsSection";
import EventSessionsSection from "../../eventSessions/components/EventSessionsSection";
import { updateEventFeeRequest } from "../../admin/api/adminApi";
import PublicRelationsSection from "../../publicRelations/components/PublicRelationsSection";
import { ROUTES, routeTo } from "../../../routes/paths";
import { getApiErrorMessage } from "../../../api/errors";
import { selectEventSessionId } from "../utils/sessionSelection";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { ManagedEvent } from "../../../types/domain";

import styles from "./EventManagementPage.module.css";

type ConfirmAction = {
  title: string;
  message: string;
  confirmLabel: string;
  tone?: "default" | "danger";
  run: () => Promise<unknown>;
  errorMessage: string;
  redirectTo?: string;
};

export default function EventManagementPage() {
  const eventId = useParams<{ eventId: string }>()?.eventId;
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, isAdmin } = useAuth();
  const requestedSessionId = searchParams?.get("session_id") ?? null;

  const [event, setEvent] = useState<ManagedEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [showEditModal, setShowEditModal] = useState(false);
  const [structureRefreshKey, setStructureRefreshKey] = useState(0);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [feeLoading, setFeeLoading] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<EntityId | null>(null);
  const scrollRestoreTimerRef = useRef<number | null>(null);

  const loadEvent = useCallback(async ({ showLoading = true } = {}) => {
    if (!eventId) return;
    try {
      if (showLoading) setLoading(true);
      setErrorMsg("");
      const data = await getManageEventByIdRequest(eventId);
      const sessions = data.sessions ?? [];

      setEvent(data);
      setSelectedSessionId((current) =>
        selectEventSessionId(sessions, {
          includeUnpublished: true,
          requestedSessionId,
          currentSessionId: current,
        })
      );
    } catch (error) {
      console.error("Error cargando detalle del evento:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo cargar el evento"));
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [eventId, requestedSessionId]);

  const restoreScrollPosition = useCallback((scrollTop: number) => {
    const restore = () => window.scrollTo({ top: scrollTop, behavior: "auto" });
    window.requestAnimationFrame(() => window.requestAnimationFrame(restore));

    if (scrollRestoreTimerRef.current !== null) {
      window.clearTimeout(scrollRestoreTimerRef.current);
    }
    scrollRestoreTimerRef.current = window.setTimeout(restore, 250);
  }, []);

  const reloadEventPreservingScroll = useCallback(async () => {
    const scrollTop = window.scrollY;
    await loadEvent({ showLoading: false });
    restoreScrollPosition(scrollTop);
  }, [loadEvent, restoreScrollPosition]);

  useEffect(() => {
    if (eventId) void loadEvent({ showLoading: true });
  }, [eventId, loadEvent]);

  useEffect(
    () => () => {
      if (scrollRestoreTimerRef.current !== null) {
        window.clearTimeout(scrollRestoreTimerRef.current);
      }
    },
    []
  );

  const runConfirmedAction = async () => {
    if (!confirmAction) return;
    try {
      setConfirmLoading(true);
      await confirmAction.run();
      if (confirmAction.redirectTo) {
        router.replace(confirmAction.redirectTo);
        return;
      }
      await reloadEventPreservingScroll();
      setConfirmAction(null);
    } catch (error) {
      alert(getApiErrorMessage(error, confirmAction.errorMessage));
    } finally {
      setConfirmLoading(false);
    }
  };

  const requestPublishEvent = () => {
    if (!event) return;
    setConfirmAction({
      title: event.status === "unpublished" ? "Republicar evento" : "Publicar evento",
      message:
        "¿Estás seguro de publicar este evento? Se verán publicadas las sesiones que ya hayan sido revisadas y aprobadas.",
      confirmLabel: event.status === "unpublished" ? "Republicar evento" : "Publicar evento",
      run: () => publishEventRequest(event.id),
      errorMessage: "No se pudo publicar el evento",
    });
  };

  const requestUnpublishEvent = () => {
    if (!event) return;
    setConfirmAction({
      title: "Despublicar evento",
      message:
        "¿Estás seguro de despublicar este evento? El evento dejará de estar visible para nuevas compras.",
      confirmLabel: "Despublicar evento",
      run: () => unpublishEventRequest(event.id),
      errorMessage: "No se pudo despublicar el evento",
    });
  };

  const handleDeleteEvent = () => {
    if (!event) return;
    setConfirmAction({
      title: "Borrar evento",
      message:
        "Vas a borrar este evento. Dejará de aparecer en tu listado y esta acción no se puede deshacer.",
      confirmLabel: "Borrar evento",
      tone: "danger",
      run: () => deleteEventRequest(event.id),
      redirectTo: isAdmin
        ? routeTo.adminPromoterEvents(event.promoter_id)
        : ROUTES.promoter,
      errorMessage: "No se pudo borrar el evento",
    });
  };

  const handleUpdateFee = async (payload: ApiSchema<"AdminEventFeeRequest">) => {
    if (feeLoading || !event) return;
    try {
      setFeeLoading(true);
      await updateEventFeeRequest(event.id, payload);
      await reloadEventPreservingScroll();
    } catch (error) {
      console.error("Error actualizando tarifa:", error);
      alert(getApiErrorMessage(error, "No se pudo actualizar la tarifa"));
    } finally {
      setFeeLoading(false);
    }
  };

  const handleTicketStructureChanged = useCallback(async () => {
    const scrollTop = window.scrollY;
    setStructureRefreshKey((current) => current + 1);
    await loadEvent({ showLoading: false });
    restoreScrollPosition(scrollTop);
  }, [loadEvent, restoreScrollPosition]);

  const isOwner = useMemo(
    () => Boolean(user && event && user.id === event.promoter_id),
    [user, event]
  );
  const canManage = isAdmin || isOwner;
  const isEditable = isAdmin || event?.status === "not_reviewed";
  const canPublishEvent = Boolean(
    isAdmin && event && ["draft", "unpublished"].includes(event.status)
  );
  const canUnpublishEvent = Boolean(
    isAdmin && event && ["published", "sold_out"].includes(event.status)
  );
  const canDeleteEvent = Boolean(
    event &&
      !["published", "sold_out", "finished", "archived", "disabled"].includes(
        event.status
      ) &&
      (isAdmin || ["not_reviewed", "in_review"].includes(event.status))
  );
  const selectedSession = useMemo(
    () => event?.sessions?.find((session) => session.id === selectedSessionId) ?? null,
    [event, selectedSessionId]
  );
  const canShowPublicRelations = Boolean(
    canManage &&
      event &&
      ["draft", "published", "unpublished", "sold_out", "finished"].includes(
        event.status
      )
  );

  return (
    <PageContainer title="Gestión del evento">
      {loading ? <p>Cargando evento...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {!loading && !errorMsg && event ? (
        <>
          <EventDetailInfo
            event={event}
            selectedSession={selectedSession}
            isManageView
            isAdmin={isAdmin}
            onUpdateFee={handleUpdateFee}
            feeLoading={feeLoading}
            headerActions={
              canManage ? (
                <EventActionsMenu
                  editLabel={isEditable ? "Editar evento" : "Ver formulario"}
                  actionLoading={confirmLoading}
                  onEdit={() => setShowEditModal(true)}
                  {...(canDeleteEvent ? { onDelete: handleDeleteEvent } : {})}
                />
              ) : null
            }
            footerActions={
              canPublishEvent || canUnpublishEvent ? (
                <>
                {canPublishEvent ? (
                  <PublishEventButton
                    onClick={requestPublishEvent}
                    loading={confirmLoading}
                    isRepublish={event.status === "unpublished"}
                  />
                ) : null}
                {canUnpublishEvent ? (
                  <UnpublishEventButton
                    onClick={requestUnpublishEvent}
                    loading={confirmLoading}
                  />
                ) : null}
                </>
              ) : null
            }
          />
          <EventSessionsSection
            event={event}
            selectedSessionId={selectedSessionId}
            onSelectSession={setSelectedSessionId}
            canManage={canManage}
            isAdmin={isAdmin}
            onChanged={reloadEventPreservingScroll}
          />
          <SaleGroupsSection
            event={event}
            canManage={canManage}
            isAdmin={isAdmin}
            variant="summary"
            selectedSessionId={selectedSessionId}
            selectedSession={selectedSession}
            refreshKey={structureRefreshKey}
            onStructureChanged={handleTicketStructureChanged}
          />
          {canShowPublicRelations ? (
            <PublicRelationsSection event={event} canManage={canManage} />
          ) : null}
          <EventModal
            isOpen={showEditModal}
            onClose={() => setShowEditModal(false)}
            mode="edit"
            initialData={event}
            isAdmin={isAdmin}
            onSuccess={reloadEventPreservingScroll}
          />
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
        </>
      ) : null}
    </PageContainer>
  );
}
