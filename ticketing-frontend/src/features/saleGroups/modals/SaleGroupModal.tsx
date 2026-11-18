import { useState } from "react";
import Modal from "../../../components/ui/Modal";
import SaleGroupForm from "../forms/SaleGroupForm";
import styles from "./SaleGroupModal.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { EntityId } from "../../../types/api";
import type { SaleGroup, SaleGroupCreate, SaleGroupUpdate } from "../../../types/domain";
import type { SaleGroupFormPayload } from "../forms/SaleGroupForm";

import {
  createSaleGroupRequest,
  updateSaleGroupRequest,
} from "../api/saleGroupsApi";

function isSaleGroupEditable(group: SaleGroup | null, isAdmin = false): boolean {
  if (!group) return true;
  return group.status === "draft" || isAdmin;
}

export default function SaleGroupModal({
  isOpen,
  onClose,
  mode = "create",
  eventId,
  sessionId = null,
  initialData = null,
  onSuccess,
  isAdmin = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  mode?: "create" | "edit";
  eventId: EntityId;
  sessionId?: EntityId | null;
  initialData?: SaleGroup | null;
  onSuccess?: (() => void | Promise<void>) | undefined;
  isAdmin?: boolean;
}) {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const isEdit = mode === "edit";
  const readOnly = isEdit && !isSaleGroupEditable(initialData, isAdmin);

  const handleSubmit = async (payload: SaleGroupFormPayload) => {
    try {
      setLoading(true);
      setErrorMsg("");

      if (isEdit && initialData) {
        const updatePayload: SaleGroupUpdate = { ...payload };
        await updateSaleGroupRequest(eventId, initialData.id, updatePayload);
      } else {
        const createPayload: SaleGroupCreate = {
          ...payload,
          session_id: sessionId,
        };
        await createSaleGroupRequest(eventId, createPayload);
      }

      await onSuccess?.();
      onClose();
    } catch (error) {
      console.error("Error guardando grupo de venta:", error);
      setErrorMsg(
        getApiErrorMessage(error, "No se pudo guardar el grupo de venta")
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? "Editar grupo de venta" : "Crear grupo de venta"}
    >
      {readOnly ? (
        <p className={styles.warning}>
          Este grupo no se puede editar en su estado actual.
        </p>
      ) : null}

      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      <SaleGroupForm
        key={initialData?.id || "create-sale-group"}
        initialData={initialData}
        onSubmit={handleSubmit}
        loading={loading}
        submitLabel={isEdit ? "Guardar cambios" : "Crear grupo"}
        readOnly={readOnly}
        isAdmin={isAdmin}
      />
    </Modal>
  );
}
