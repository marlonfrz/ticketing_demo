import { useCallback, useEffect, useState } from "react";
import {
  deleteTicketTypeRequest,
  getTicketTypesByEventRequest,
} from "../api/ticketTypesApi";
import { getSaleGroupsByEventRequest } from "../../saleGroups/api/saleGroupsApi";
import ConfirmDialog from "../../../components/ui/ConfirmDialog";
import Button from "../../../components/ui/Button";
import TicketTypeCard from "./TicketTypeCard";
import TicketTypeModal from "../modals/TicketTypeModal";

import styles from "./TicketTypesSection.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { EntityId } from "../../../types/api";
import type { EventSession, ManagedEvent, SaleGroup, TicketType } from "../../../types/domain";

type TicketTypesSectionProps = {
  event: ManagedEvent;
  canManage: boolean;
  isAdmin?: boolean;
  refreshKey?: number;
  selectedSessionId?: EntityId | null;
  selectedSession?: EventSession | null;
  onStructureChanged?: () => void | Promise<void>;
};

function eventAllowsSessionStructureChanges(event: ManagedEvent): boolean {
  return !["archived", "disabled", "finished", "cancelled"].includes(event.status);
}

export default function TicketTypesSection({
  event,
  canManage,
  isAdmin = false,
  refreshKey = 0,
  selectedSessionId = null,
  selectedSession = null,
  onStructureChanged,
}: TicketTypesSectionProps) {
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTicketType, setEditingTicketType] = useState<TicketType | null>(null);
  const [saleGroups, setSaleGroups] = useState<SaleGroup[]>([]);
  const [ticketTypeToDelete, setTicketTypeToDelete] = useState<TicketType | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadTicketTypes = useCallback(async () => {
    if (!event?.id) return;

    try {
      setLoading(true);
      setErrorMsg("");

      const [ticketTypesData, saleGroupsData] = await Promise.all([
        getTicketTypesByEventRequest(event.id, selectedSessionId),
        getSaleGroupsByEventRequest(event.id, selectedSessionId),
      ]);

      setTicketTypes(ticketTypesData);
      setSaleGroups(saleGroupsData);
    } catch (error) {
      console.error("Error cargando ticket types:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudieron cargar los tipos de entrada"));
    } finally {
      setLoading(false);
    }
  }, [event?.id, selectedSessionId]);

  useEffect(() => {
    if (event?.id) {
      loadTicketTypes();
    }
  }, [event?.id, loadTicketTypes, refreshKey, selectedSessionId]);

  const handleDelete = async () => {
    if (!ticketTypeToDelete) return;

    try {
      setDeleteLoading(true);
      await deleteTicketTypeRequest(ticketTypeToDelete.id);
      setTicketTypeToDelete(null);
      await onStructureChanged?.();
    } catch (error) {
      console.error("Error borrando ticket type:", error);
      alert(getApiErrorMessage(error, "No se pudo borrar el tipo de entrada"));
    } finally {
      setDeleteLoading(false);
    }
  };

  const canChangeTickets =
    canManage &&
    eventAllowsSessionStructureChanges(event) &&
    Boolean(selectedSession && ["not_reviewed", "draft", "cancelled"].includes(selectedSession.status));
  const canEditStock =
    canManage &&
    ["published", "sold_out", "unpublished"].includes(event.status) &&
    Boolean(selectedSession && ["published", "sold_out", "unpublished"].includes(selectedSession.status));
  const canManageTicketCards = canChangeTickets || canEditStock;

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h3 className={styles.title}>Tipos de entrada</h3>

        {canChangeTickets ? (
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
          >
            Crear tipo de entrada
          </Button>
        ) : null}
      </div>

      {loading ? <p>Cargando tipos de entrada...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {canManage && selectedSession?.status === "in_review" ? (
        <p className={styles.warning}>
          Los tipos de entrada no se pueden modificar mientras la sesión está en revisión.
        </p>
      ) : null}

      {canManage && ["published", "sold_out", "unpublished"].includes(selectedSession?.status ?? "") ? (
        <p className={styles.warning}>
          La sesión ya salió del borrador. Puedes ajustar stock, pero no crear ni borrar tipos.
        </p>
      ) : null}

      {canManage && selectedSession?.status === "finished" ? (
        <p className={styles.warning}>
          Esta sesión está finalizada. Puedes consultar las entradas, pero no modificarlas.
        </p>
      ) : null}

      {!loading && !errorMsg && ticketTypes.length === 0 ? (
        <p>No hay tipos de entrada todavía.</p>
      ) : null}

      <div className={styles.list}>
        {ticketTypes.map((ticketType) => (
          <TicketTypeCard
            key={ticketType.id}
            ticketType={ticketType}
            canManage={canManageTicketCards}
            canDeleteTickets={canChangeTickets}
            stockOnly={canEditStock && !canChangeTickets}
            isAdmin={isAdmin}
            onEdit={() => setEditingTicketType(ticketType)}
            onDelete={() => setTicketTypeToDelete(ticketType)}
          />
        ))}
      </div>

      <TicketTypeModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        mode="create"
        eventId={event.id}
        sessionId={selectedSessionId}
        initialData={null}
        saleGroups={saleGroups}
        isAdmin={isAdmin}
        stockOnly={canEditStock && !canChangeTickets}
        onSuccess={onStructureChanged}
      />

      <TicketTypeModal
        isOpen={!!editingTicketType}
        onClose={() => setEditingTicketType(null)}
        mode="edit"
        eventId={event.id}
        sessionId={selectedSessionId}
        initialData={editingTicketType}
        saleGroups={saleGroups}
        isAdmin={isAdmin}
        stockOnly={canEditStock && !canChangeTickets}
        onSuccess={onStructureChanged}
      />

      <ConfirmDialog
        isOpen={!!ticketTypeToDelete}
        title="Borrar tipo de entrada"
        message={`Vas a borrar "${ticketTypeToDelete?.name}". Solo se permite si no tiene ventas ni entradas generadas.`}
        confirmLabel="Borrar"
        tone="danger"
        loading={deleteLoading}
        onCancel={() => setTicketTypeToDelete(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
