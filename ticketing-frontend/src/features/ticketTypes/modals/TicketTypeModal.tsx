import { useState } from "react";
import Modal from "../../../components/ui/Modal";
import TicketTypeForm, { type TicketTypeFormPayload } from "../forms/TicketTypeForm";
import styles from "./TicketTypeModal.module.css";

import {
  createTicketTypeRequest,
  updateTicketTypeRequest,
} from "../api/ticketTypesApi";
import {
  assignTicketTypeToSaleGroupRequest,
  removeTicketTypeFromSaleGroupRequest,
} from "../../saleGroups/api/saleGroupsApi";
import { getApiErrorMessage } from "../../../api/errors";
import type { EntityId } from "../../../types/api";
import type { SaleGroup, TicketType, TicketTypeCreate, TicketTypeUpdate } from "../../../types/domain";

function isTicketTypeEditable(ticketType: TicketType | null, isAdmin = false): boolean {
  if (!ticketType) return true;
  return ticketType.status === "draft" || isAdmin;
}

export default function TicketTypeModal({
  isOpen,
  onClose,
  mode = "create",
  eventId,
  sessionId = null,
  initialData = null,
  onSuccess,
  saleGroups = [],
  isAdmin = false,
  stockOnly = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  mode?: "create" | "edit";
  eventId: EntityId;
  sessionId?: EntityId | null;
  initialData?: TicketType | null;
  onSuccess?: (() => void | Promise<void>) | undefined;
  saleGroups?: SaleGroup[];
  isAdmin?: boolean;
  stockOnly?: boolean;
}) {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  

  const isEdit = mode === "edit";
  const readOnly = isEdit && !stockOnly && !isTicketTypeEditable(initialData, isAdmin);

  const handleSubmit = async (payload: TicketTypeFormPayload) => {
    try {
      setLoading(true);
      setErrorMsg("");

      const { sale_group_id, sale_order, ...ticketPayload } = payload;

      let savedTicket;

      if (isEdit && initialData) {
        const updatePayload: TicketTypeUpdate = stockOnly
          ? { stock: ticketPayload.stock }
          : ticketPayload;
        savedTicket = await updateTicketTypeRequest(
          initialData.id,
          updatePayload
        );

        if (!stockOnly && sale_group_id) {
          await assignTicketTypeToSaleGroupRequest(eventId, initialData.id, {
            sale_group_id,
            sale_order: Number(sale_order),
          });
        } else if (!stockOnly && initialData.sale_group_id) {
          await removeTicketTypeFromSaleGroupRequest(eventId, initialData.id);
        }
      } else {
        const createPayload: TicketTypeCreate = {
          session_id: sessionId,
          name: ticketPayload.name || "",
          description: ticketPayload.description ?? null,
          price: ticketPayload.price ?? 0,
          currency: ticketPayload.currency || "EUR",
          stock: ticketPayload.stock,
          max_per_purchase: ticketPayload.max_per_purchase ?? 10,
          display_order: ticketPayload.display_order ?? null,
          is_active: ticketPayload.is_active ?? true,
        };
        savedTicket = await createTicketTypeRequest(eventId, createPayload);

        if (sale_group_id) {
          await assignTicketTypeToSaleGroupRequest(eventId, savedTicket.id, {
            sale_group_id,
            sale_order: Number(sale_order),
          });
        }
      }

      await onSuccess?.();
      onClose();
    } catch (error) {
      console.error("Error guardando ticket type:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo guardar el tipo de entrada"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? "Editar tipo de entrada" : "Crear tipo de entrada"}
    >
      {readOnly ? (
        <p className={styles.warning}>
          Este tipo de entrada no se puede editar en su estado actual.
        </p>
      ) : null}

      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      <TicketTypeForm
        key={initialData?.id || "create-ticket-type"}
        initialData={initialData}
        saleGroups={saleGroups}
        onSubmit={handleSubmit}
        loading={loading}
        submitLabel={stockOnly ? "Guardar stock" : isEdit ? "Guardar cambios" : "Crear tipo de entrada"}
        readOnly={readOnly}
        isAdmin={isAdmin}
        stockOnly={stockOnly}
      />
    </Modal>
  );
}
