"use client";

import { useMemo, useState } from "react";

import ButtonLink from "../../../components/ui/ButtonLink";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import { routeTo } from "../../../routes/paths";
import EventDetailInfo from "../components/EventDetailInfo";
import PublicSalesOptionsSection from "../../sales/components/PublicSalesOptionsSection";
import { selectEventSessionId } from "../utils/sessionSelection";
import type { EntityId } from "../../../types/api";
import type { ManagedEvent } from "../../../types/domain";

import styles from "./PublicEventPage.module.css";

type PublicEventPageProps = {
  initialEvent: ManagedEvent;
  initialSessionId?: EntityId | null;
  publicRelationsCode?: string | null;
};

export default function PublicEventPage({
  initialEvent,
  initialSessionId = null,
  publicRelationsCode = null,
}: PublicEventPageProps) {
  const { isAdmin } = useAuth();
  const [selectedSessionId, setSelectedSessionId] = useState<EntityId | null>(() =>
    selectEventSessionId(initialEvent.sessions ?? [], {
      requestedSessionId: initialSessionId,
    })
  );
  const selectedSession = useMemo(
    () =>
      initialEvent.sessions?.find((session) => session.id === selectedSessionId) ??
      null,
    [initialEvent.sessions, selectedSessionId]
  );

  return (
    <PageContainer>
      <div className={styles.header}>
        <h1 className={styles.title}>Detalle del evento</h1>
        {isAdmin ? (
          <ButtonLink variant="primary" size="small" href={routeTo.eventManage(initialEvent.id)}>
            Editar evento
          </ButtonLink>
        ) : null}
      </div>
      <EventDetailInfo event={initialEvent} selectedSession={selectedSession} />
      <PublicSalesOptionsSection
        eventId={initialEvent.id}
        sessions={initialEvent.sessions ?? []}
        selectedSessionId={selectedSessionId}
        onSelectSession={setSelectedSessionId}
        publicRelationsCode={publicRelationsCode}
      />
    </PageContainer>
  );
}
