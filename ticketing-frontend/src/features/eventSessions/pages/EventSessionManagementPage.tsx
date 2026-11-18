"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type ChangeEvent, type SubmitEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import Modal from "../../../components/ui/Modal";
import useAuth from "../../../hooks/useAuth";
import { getManageEventByIdRequest } from "../../events/api/eventsApi";
import { updateEventSessionRequest } from "../api/eventSessionsApi";
import SessionDetailInfo from "../components/SessionDetailInfo";
import SessionForm, {
  buildSessionForm,
  buildSessionPayload,
  buildInitialSessionForm,
  onlyInteger,
} from "../components/SessionForm";
import SaleGroupsSection from "../../saleGroups/components/SaleGroupsSection";
import TicketTypesSection from "../../ticketTypes/components/TicketTypesSection";
import ValidationStationsSection from "../../validationStations/components/ValidationStationsSection";
import ComplimentaryTicketsSection from "../../complimentaryTickets/components/ComplimentaryTicketsSection";
import { getApiErrorMessage } from "../../../api/errors";
import { routeTo } from "../../../routes/paths";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { EventSession, ManagedEvent } from "../../../types/domain";

import styles from "./EventSessionManagementPage.module.css";

function canEditSession(event: ManagedEvent, session: EventSession | null): boolean {
  if (!session) return false;
  const eventAllowsSessionActions = ![
    "in_review",
    "archived",
    "disabled",
    "finished",
    "cancelled",
  ].includes(event.status);

  return (
    eventAllowsSessionActions &&
    ["not_reviewed", "draft", "cancelled"].includes(session.status)
  );
}

export default function EventSessionManagementPage() {
  const params = useParams<{
    eventId: string;
    sessionId: string;
  }>();
  const eventId = params?.eventId;
  const sessionId = params?.sessionId;
  const { user, isAdmin } = useAuth();
  const [event, setEvent] = useState<ManagedEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [showEditModal, setShowEditModal] = useState(false);
  const [form, setForm] = useState(buildInitialSessionForm);
  const [saving, setSaving] = useState(false);
  const [structureRefreshKey, setStructureRefreshKey] = useState(0);
  const scrollRestoreTimerRef = useRef<number | null>(null);

  const loadEvent = useCallback(async ({ showLoading = true } = {}) => {
    if (!eventId) return;

    try {
      if (showLoading) setLoading(true);
      setErrorMsg("");
      const data = await getManageEventByIdRequest(eventId);
      setEvent(data);
    } catch (error) {
      console.error("Error cargando detalle de la sesión:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo cargar la sesión"));
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [eventId]);

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

  const selectedSession = useMemo(
    () => event?.sessions?.find((session) => session.id === sessionId) ?? null,
    [event, sessionId]
  );

  const isOwner = useMemo(
    () => Boolean(user && event && user.id === event.promoter_id),
    [user, event]
  );
  const canManage = isAdmin || isOwner;
  const canEdit = Boolean(canManage && event && canEditSession(event, selectedSession));
  const canShowComplimentaryTickets = Boolean(
    canManage &&
      event &&
      selectedSession &&
      ["published", "sold_out", "finished"].includes(event.status) &&
      ["published", "sold_out", "finished"].includes(selectedSession.status) &&
      selectedSession.tickets_activated_at
  );

  const openEditModal = () => {
    if (!selectedSession) return;
    setForm(buildSessionForm(selectedSession));
    setShowEditModal(true);
  };

  const closeEditModal = () => {
    setShowEditModal(false);
    setForm(buildInitialSessionForm());
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((current) => ({
      ...current,
      [name]: name === "capacity" ? onlyInteger(value) : value,
    }));
  };

  const handleUpdate = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (saving || !selectedSession) return;

    try {
      setSaving(true);
      await updateEventSessionRequest(
        selectedSession.id,
        buildSessionPayload(form) as ApiSchema<"EventSessionUpdate">
      );
      closeEditModal();
      await reloadEventPreservingScroll();
    } catch (error) {
      console.error("Error editando sesión:", error);
      alert(getApiErrorMessage(error, "No se pudo editar la sesión"));
    } finally {
      setSaving(false);
    }
  };

  const handleTicketStructureChanged = useCallback(async () => {
    const scrollTop = window.scrollY;
    setStructureRefreshKey((current) => current + 1);
    await loadEvent({ showLoading: false });
    restoreScrollPosition(scrollTop);
  }, [loadEvent, restoreScrollPosition]);

  return (
    <PageContainer title="Gestión de sesión">
      {eventId ? (
        <Link className={styles.backLink} href={routeTo.eventManage(eventId)}>
          Volver al evento
        </Link>
      ) : null}

      {loading ? <p>Cargando sesión...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {!loading && !errorMsg && event && !selectedSession ? (
        <p className={styles.error}>No se encontró la sesión solicitada.</p>
      ) : null}

      {!loading && !errorMsg && event && selectedSession ? (
        <>
          <SessionDetailInfo
            session={selectedSession}
            actions={
              canEdit ? (
                <Button
                  variant="primary"
                  type="button"
                  onClick={openEditModal}
                >
                  Editar sesión
                </Button>
              ) : null
            }
          />

          <SaleGroupsSection
            event={event}
            canManage={canManage}
            isAdmin={isAdmin}
            selectedSessionId={selectedSession.id}
            selectedSession={selectedSession}
            refreshKey={structureRefreshKey}
            onStructureChanged={handleTicketStructureChanged}
          />

          <TicketTypesSection
            event={event}
            canManage={canManage}
            isAdmin={isAdmin}
            selectedSessionId={selectedSession.id}
            selectedSession={selectedSession}
            refreshKey={structureRefreshKey}
            onStructureChanged={handleTicketStructureChanged}
          />

          <ValidationStationsSection
            selectedSession={selectedSession}
            canManage={canManage}
            isAdmin={isAdmin}
          />

          {canShowComplimentaryTickets ? (
            <ComplimentaryTicketsSection
              event={event}
              selectedSession={selectedSession}
              canManage={canManage}
              onReloadEvent={reloadEventPreservingScroll}
            />
          ) : null}

          <Modal
            isOpen={showEditModal}
            title="Editar sesión"
            onClose={closeEditModal}
          >
            <SessionForm
              form={form}
              loading={saving}
              mode="edit"
              onCancel={closeEditModal}
              onChange={handleChange}
              onSubmit={handleUpdate}
            />
          </Modal>
        </>
      ) : null}
    </PageContainer>
  );
}
