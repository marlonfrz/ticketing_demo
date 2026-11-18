import { useState } from "react";
import Modal from "../../../components/ui/Modal";
import ConfirmDialog from "../../../components/ui/ConfirmDialog";
import EventForm, { type EventFormSubmission } from "../components/EventForm";
import {
  createEventRequest,
  updateEventRequest,
  uploadEventImageRequest,
} from "../api/promoterApi";

import styles from "./EventModal.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { EntityId } from "../../../types/api";
import type { EventCreate, EventUpdate, ManagedEvent } from "../../../types/domain";

function isEventEditable(event: ManagedEvent | null, isAdmin = false): boolean {
  if (!event) return true;
  if (isAdmin) return true;
  return event.status === "not_reviewed";
}

export default function EventModal({
  isOpen,
  onClose,
  mode = "create",
  initialData = null,
  onSuccess,
  isAdmin = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  mode?: "create" | "edit";
  initialData?: ManagedEvent | null;
  onSuccess?: () => void | Promise<void>;
  isAdmin?: boolean;
}) {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [createdEventId, setCreatedEventId] = useState<EntityId | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);

  const isEdit = mode === "edit";
  const readOnly = isEdit && !isEventEditable(initialData, isAdmin);

  const closeImmediately = () => {
    setCreatedEventId(null);
    setErrorMsg("");
    setIsDirty(false);
    setShowDiscardConfirm(false);
    onClose();
  };

  const requestClose = () => {
    if (loading) return;
    if (isDirty) {
      setShowDiscardConfirm(true);
      return;
    }
    closeImmediately();
  };

  const handleSubmit = async ({ eventData, imageFile }: EventFormSubmission) => {
    try {
      setLoading(true);
      setErrorMsg("");

      let savedEventId: EntityId;
      if (readOnly && initialData) {
        savedEventId = initialData.id;
      } else if (isEdit && initialData) {
        const { initial_session: _initialSession, ...updateData } = eventData;
        const typedUpdateData: EventUpdate = updateData;
        const savedEvent = await updateEventRequest(initialData.id, typedUpdateData);
        savedEventId = savedEvent.id;
      } else if (createdEventId) {
        const { initial_session: _initialSession, ...updateData } = eventData;
        const typedUpdateData: EventUpdate = updateData;
        const savedEvent = await updateEventRequest(createdEventId, typedUpdateData);
        savedEventId = savedEvent.id;
      } else {
        if (!eventData.initial_session) {
          throw new Error("Initial session is required when creating an event");
        }
        const createData: EventCreate = {
          ...eventData,
          initial_session: eventData.initial_session,
          status: "not_reviewed",
        };
        const savedEvent = await createEventRequest(createData);
        setCreatedEventId(savedEvent.id);
        savedEventId = savedEvent.id;
      }

      if (imageFile) {
        try {
          await uploadEventImageRequest(savedEventId, imageFile);
        } catch (imageError) {
          console.error("Error subiendo la imagen del evento:", imageError);
          await onSuccess?.();
          setErrorMsg(
            `El evento se guardó correctamente, pero la imagen no se pudo subir: ${getApiErrorMessage(
              imageError,
              "error desconocido"
            )}. Selecciona otra imagen y vuelve a guardar.`
          );
          return;
        }
      }

      setCreatedEventId(null);
      await onSuccess?.();
      closeImmediately();
    } catch (error) {
      console.error("Error guardando evento:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo guardar el evento"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={loading ? undefined : requestClose}
        title={isEdit ? "Editar evento" : "Crear evento"}
      >
        {readOnly ? (
          <p className={styles.warning}>
            Los datos de este evento no se pueden editar en su estado actual,
            pero puedes actualizar su imagen.
          </p>
        ) : null}

        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

        <EventForm
          key={initialData?.id || "create"}
          initialData={initialData}
          onSubmit={handleSubmit}
          loading={loading}
          submitLabel={isEdit ? "Guardar cambios" : "Crear evento"}
          readOnly={readOnly}
          onDirtyChange={setIsDirty}
        />
      </Modal>
      <ConfirmDialog
        isOpen={showDiscardConfirm}
        title="Cambios sin guardar"
        message="Has modificado el formulario. Si lo cierras, perderas los cambios que no hayas guardado."
        confirmLabel="Descartar cambios"
        cancelLabel="Seguir editando"
        tone="danger"
        onCancel={() => setShowDiscardConfirm(false)}
        onConfirm={closeImmediately}
      />
    </>
  );
}
