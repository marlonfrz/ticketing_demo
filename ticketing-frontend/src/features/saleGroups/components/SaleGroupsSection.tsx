import { useCallback, useEffect, useState } from "react";
import { getTicketTypesByEventRequest } from "../../ticketTypes/api/ticketTypesApi";
import {
  deleteSaleGroupRequest,
  getSaleGroupsByEventRequest,
  publishSaleGroupRequest,
} from "../api/saleGroupsApi";
import ConfirmDialog from "../../../components/ui/ConfirmDialog";
import Button from "../../../components/ui/Button";
import SaleGroupCard from "./SaleGroupCard";
import SaleGroupModal from "../modals/SaleGroupModal";
import SaleGroupTicketBoard from "./SaleGroupTicketBoard";

import styles from "./SaleGroupsSection.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { EntityId } from "../../../types/api";
import type { EventSession, ManagedEvent, SaleGroup, TicketType } from "../../../types/domain";

type ConfirmAction = {
  title: string;
  message: string;
  confirmLabel: string;
  tone?: "default" | "danger";
  run: () => Promise<unknown>;
  errorMessage: string;
};

type SaleGroupsSectionProps = {
  event: ManagedEvent;
  canManage: boolean;
  isAdmin: boolean;
  variant?: "full" | "summary";
  refreshKey?: number;
  selectedSessionId?: EntityId | null;
  selectedSession?: EventSession | null;
  onStructureChanged?: () => void | Promise<void>;
};

function eventAllowsSessionStructureChanges(event: ManagedEvent): boolean {
  return !["archived", "disabled", "finished", "cancelled"].includes(event.status);
}

export default function SaleGroupsSection({
  event,
  canManage,
  isAdmin,
  variant = "full",
  refreshKey = 0,
  selectedSessionId = null,
  selectedSession = null,
  onStructureChanged,
}: SaleGroupsSectionProps) {
  const [groups, setGroups] = useState<SaleGroup[]>([]);
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<SaleGroup | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);

  const loadAll = useCallback(async () => {
    if (!event?.id) return;

    try {
      setLoading(true);
      setErrorMsg("");

      const [groupsData, ticketTypesData] = await Promise.all([
        getSaleGroupsByEventRequest(event.id, selectedSessionId),
        getTicketTypesByEventRequest(event.id, selectedSessionId),
      ]);

      setGroups(groupsData);
      setTicketTypes(ticketTypesData);
    } catch (error) {
      console.error("Error cargando grupos de venta:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudieron cargar los grupos de venta"));
    } finally {
      setLoading(false);
    }
  }, [event?.id, selectedSessionId]);

  useEffect(() => {
    if (event?.id) {
      loadAll();
    }
  }, [event?.id, loadAll, refreshKey, selectedSessionId]);

  const runConfirmedAction = async () => {
    if (!confirmAction) return;

    try {
      setConfirmLoading(true);
      await confirmAction.run();
      setConfirmAction(null);
      await onStructureChanged?.();
    } catch (error) {
      console.error("Error ejecutando acción de grupo:", error);
      alert(getApiErrorMessage(error, confirmAction.errorMessage));
    } finally {
      setConfirmLoading(false);
    }
  };

  const canChangeGroups =
    canManage &&
    eventAllowsSessionStructureChanges(event) &&
    Boolean(selectedSession && ["not_reviewed", "draft", "cancelled"].includes(selectedSession.status));
  const canPublishSaleGroups = isAdmin && event?.status === "published";
  const isSummary = variant === "summary";

  return (
    <div className={styles.wrapper}>
      {!isSummary ? (
        <div className={styles.header}>
          <div>
            <h3 className={styles.title}>Grupos de venta</h3>
            <p className={styles.subtitle}>
              Agrupa entradas para ventas en cascada por stock, fechas o ambas.
            </p>
          </div>

          {canChangeGroups ? (
            <Button variant="primary" onClick={() => setShowCreateModal(true)}>
              Crear grupo de venta
            </Button>
          ) : null}
        </div>
      ) : null}

      {loading ? <p>Cargando grupos de venta...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {canManage && !isSummary && selectedSession?.status === "in_review" ? (
        <p className={styles.warning}>
          Los grupos de venta no se pueden modificar mientras la sesión está en revisión.
        </p>
      ) : null}

      {canManage && !isSummary && ["published", "sold_out", "unpublished"].includes(selectedSession?.status ?? "") ? (
        <p className={styles.warning}>
          La sesión ya salió del borrador. Puedes consultar los grupos, pero no crear ni borrar estructura de venta.
        </p>
      ) : null}

      {canManage && !isSummary && selectedSession?.status === "finished" ? (
        <p className={styles.warning}>
          Esta sesión está finalizada. Puedes consultar el resumen.
        </p>
      ) : null}

      {!loading && !errorMsg && !isSummary && groups.length === 0 ? (
        <p>No hay grupos de venta todavía.</p>
      ) : null}

      {!isSummary ? (
        <div className={styles.list}>
          {groups.map((group) => (
            <SaleGroupCard
              key={group.id}
              group={group}
              canManage={canChangeGroups}
              isAdmin={isAdmin}
              canPublishSaleGroups={canPublishSaleGroups}
              onEdit={() => setEditingGroup(group)}
              onDelete={() =>
                setConfirmAction({
                  title: "Borrar grupo de venta",
                  message: `Vas a borrar "${group.name}". Si contiene entradas, el backend solo lo permitira cuando sea seguro.`,
                  confirmLabel: "Borrar",
                  tone: "danger",
                  run: () => deleteSaleGroupRequest(event.id, group.id),
                  errorMessage: "No se pudo borrar el grupo de venta",
                })
              }
              onPublish={() =>
                setConfirmAction({
                  title: "Publicar grupo de venta",
                  message: `Vas a publicar "${group.name}" y sus entradas en borrador.`,
                  confirmLabel: "Publicar",
                  run: () => publishSaleGroupRequest(event.id, group.id),
                  errorMessage: "No se pudo publicar el grupo de venta",
                })
              }
            />
          ))}
        </div>
      ) : null}

      {!errorMsg ? (
        <SaleGroupTicketBoard
          groups={groups}
          ticketTypes={ticketTypes}
          isAdmin={isAdmin}
          showHelp={!isSummary}
        />
      ) : null}

      {!isSummary ? (
        <>
          <SaleGroupModal
            isOpen={showCreateModal}
            onClose={() => setShowCreateModal(false)}
            mode="create"
            eventId={event.id}
            sessionId={selectedSessionId}
            initialData={null}
            isAdmin={isAdmin}
            onSuccess={onStructureChanged}
          />

          <SaleGroupModal
            isOpen={!!editingGroup}
            onClose={() => setEditingGroup(null)}
            mode="edit"
            eventId={event.id}
            sessionId={selectedSessionId}
            initialData={editingGroup}
            isAdmin={isAdmin}
            onSuccess={onStructureChanged}
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
    </div>
  );
}
