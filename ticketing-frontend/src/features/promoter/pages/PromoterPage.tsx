import { redirect } from "next/navigation";
import { useEffect, useState } from "react";
import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import { getMyEventsRequest } from "../api/promoterApi";
import PromoterEventCard from "../components/PromoterEventCard";
import EventModal from "../modals/EventModal";
import { ROUTES } from "../../../routes/paths";

import styles from "./PromoterPage.module.css";
import type { Event } from "../../../types/domain";
import { getApiErrorMessage } from "../../../api/errors";

export default function PromoterPage() {
  const { canAccessPromoter, authLoading } = useAuth();

  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const loadEvents = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const data = await getMyEventsRequest();
      setEvents(data);
    } catch (error) {
      console.error("Error cargando eventos del promotor:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudieron cargar tus eventos"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (canAccessPromoter) {
      loadEvents();
    }
  }, [canAccessPromoter]);

  if (authLoading) {
    return (
      <PageContainer title="Promotor">
        <p>Cargando...</p>
      </PageContainer>
    );
  }

  if (!canAccessPromoter) {
    redirect(ROUTES.home);
  }

  return (
    <PageContainer title="Panel de promotor">
      <div className={styles.header}>
        <p>Gestiona aquí tus eventos.</p>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          Crear evento
        </Button>
      </div>

      {loading ? <p>Cargando eventos...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {!loading && !errorMsg && events.length === 0 ? (
        <p>No tienes eventos todavía.</p>
      ) : null}

      <div className={styles.grid}>
        {events.map((event) => (
          <PromoterEventCard
            key={event.id}
            event={event}
          />
        ))}
      </div>

      <EventModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        mode="create"
        initialData={null}
        onSuccess={loadEvents}
      />
    </PageContainer>
  );
}
