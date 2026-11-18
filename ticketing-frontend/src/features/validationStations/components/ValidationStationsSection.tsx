import { type SubmitEvent, useCallback, useEffect, useState } from "react";
import Button from "../../../components/ui/Button";
import ButtonLink from "../../../components/ui/ButtonLink";
import ConfirmDialog from "../../../components/ui/ConfirmDialog";
import { routeTo } from "../../../routes/paths";
import {
  createValidationQuotaRequest,
  createValidationStationRequest,
  getValidationSessionManagementRequest,
  regenerateValidationStationLinkRequest,
  revokeValidationStationRequest,
} from "../api/validationStationsApi";

import styles from "./ValidationStationsSection.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { EventSession, ValidationManagement, ValidationStation } from "../../../types/domain";

const STATUS_LABELS: Readonly<Record<string, string>> = {
  pending_activation: "Pendiente de activar",
  active: "Activo",
  revoked: "Revocado",
  finished: "Finalizado",
  pending: "Pendiente",
  approved: "Aprobado",
  rejected: "Rechazado",
};

const SESSION_VALIDATION_STATUSES = [
  "draft",
  "published",
  "sold_out",
  "unpublished",
  "finished",
];
const SESSION_VALIDATION_REQUEST_STATUSES = ["draft", "published", "sold_out", "unpublished"];

function getStatusLabel(status: string): string {
  return STATUS_LABELS[status] || status;
}

async function copyText(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

export default function ValidationStationsSection({
  selectedSession,
  canManage,
  isAdmin,
}: { selectedSession: EventSession | null; canManage: boolean; isAdmin: boolean }) {
  const [management, setManagement] = useState<ValidationManagement | null>(null);
  const [requestCount, setRequestCount] = useState(1);
  const [requestNote, setRequestNote] = useState("");
  const [stationForm, setStationForm] = useState({
    name: "",
    responsible_name: "",
    notes: "",
  });
  const [issuedLinksByStation, setIssuedLinksByStation] = useState<Record<EntityId, ApiSchema<"ValidationStationLinkResponse">>>({});
  const [copiedStationId, setCopiedStationId] = useState<EntityId | null>(null);
  const [confirmStation, setConfirmStation] = useState<ValidationStation | null>(null);
  const [showExtraQuotaRequest, setShowExtraQuotaRequest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const loadManagement = useCallback(async () => {
    if (
      !selectedSession?.id ||
      !SESSION_VALIDATION_STATUSES.includes(selectedSession.status)
    ) {
      setManagement(null);
      return;
    }
    const scope = isAdmin ? "admin" : "promoter";

    try {
      setLoading(true);
      setErrorMsg("");
      setManagement(
        await getValidationSessionManagementRequest(selectedSession.id, scope)
      );
    } catch (error) {
      console.error("Error cargando puestos de validacion:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudieron cargar los puestos de validacion"));
    } finally {
      setLoading(false);
    }
  }, [isAdmin, selectedSession?.id, selectedSession?.status]);

  useEffect(() => {
    setIssuedLinksByStation({});
    setCopiedStationId(null);
    setShowExtraQuotaRequest(false);
    void loadManagement();
  }, [loadManagement]);

  useEffect(() => {
    const approvedQuota = management?.approved_quota;
    if (Number(approvedQuota || 0) > 0) {
      setRequestCount(Number(approvedQuota));
    }
  }, [management?.approved_quota]);

  const sessionAllowsQuota =
    selectedSession && SESSION_VALIDATION_STATUSES.includes(selectedSession.status);

  if (!canManage || !selectedSession || !sessionAllowsQuota) return null;

  const submitQuotaRequest = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loading) return;

    try {
      setLoading(true);
      setErrorMsg("");
      const scope = isAdmin ? "admin" : "promoter";
      await createValidationQuotaRequest(selectedSession.id, {
        requested_count: Number(requestCount),
        promoter_note: requestNote || null,
      }, scope);
      setRequestNote("");
      setShowExtraQuotaRequest(false);
      await loadManagement();
    } catch (error) {
      console.error("Error solicitando puestos:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo enviar la solicitud de puestos"));
    } finally {
      setLoading(false);
    }
  };

  const createStation = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loading) return;

    try {
      setLoading(true);
      setErrorMsg("");
      const scope = isAdmin ? "admin" : "promoter";
      const result = await createValidationStationRequest(selectedSession.id, {
        name: stationForm.name,
        responsible_name: stationForm.responsible_name || null,
        notes: stationForm.notes || null,
      }, scope);
      setIssuedLinksByStation((current) => ({
        ...current,
        [result.station.id]: result,
      }));
      setStationForm({ name: "", responsible_name: "", notes: "" });
      await loadManagement();
    } catch (error) {
      console.error("Error creando puesto:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo crear el puesto"));
    } finally {
      setLoading(false);
    }
  };

  const regenerateLink = async (stationId: EntityId) => {
    if (loading) return;

    try {
      setLoading(true);
      setErrorMsg("");
      const scope = isAdmin ? "admin" : "promoter";
      const result = await regenerateValidationStationLinkRequest(stationId, scope);
      setIssuedLinksByStation((current) => ({
        ...current,
        [result.station.id]: result,
      }));
      await loadManagement();
    } catch (error) {
      console.error("Error regenerando enlace:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo regenerar el enlace"));
    } finally {
      setLoading(false);
    }
  };

  const revokeStation = async () => {
    if (!confirmStation || loading) return;

    try {
      setLoading(true);
      setErrorMsg("");
      const scope = isAdmin ? "admin" : "promoter";
      await revokeValidationStationRequest(confirmStation.id, scope);
      setConfirmStation(null);
      await loadManagement();
    } catch (error) {
      console.error("Error revocando puesto:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo revocar el puesto"));
    } finally {
      setLoading(false);
    }
  };

  const copyIssuedLink = async (stationId: EntityId, activationUrl: string) => {
    if (!activationUrl) return;

    try {
      await copyText(activationUrl);
      setCopiedStationId(stationId);
      window.setTimeout(() => {
        setCopiedStationId((current) => (current === stationId ? null : current));
      }, 1800);
    } catch (error) {
      console.error("Error copiando enlace:", error);
      setErrorMsg("No se pudo copiar el enlace. Seleccionalo manualmente.");
    }
  };

  const latestRequest = management?.latest_request;
  const approvedQuota = Number(management?.approved_quota || 0);
  const occupiedSlots = Number(management?.occupied_slots || 0);
  const availableSlots = Number(management?.available_slots || 0);
  const hasPendingRequest = latestRequest?.status === "pending";
  const hasApprovedQuota = approvedQuota > 0;
  const hasStations = Boolean(management?.stations?.length);
  const canRequestQuota =
    SESSION_VALIDATION_REQUEST_STATUSES.includes(selectedSession.status) &&
    (isAdmin || !hasPendingRequest);
  const canCreateStations =
    SESSION_VALIDATION_REQUEST_STATUSES.includes(selectedSession.status) &&
    availableSlots > 0;
  const showMainQuotaForm =
    canRequestQuota && (isAdmin || !hasApprovedQuota);
  const showExtraQuotaForm =
    canRequestQuota && !isAdmin && hasApprovedQuota;
  const latestAdminMessage =
    !isAdmin &&
    latestRequest?.admin_note &&
    ["approved", "rejected"].includes(latestRequest.status)
      ? latestRequest.admin_note
      : "";

  const renderQuotaForm = (isExtraRequest = false) => (
    <form className={styles.inlineForm} onSubmit={submitQuotaRequest}>
      <label className={styles.field}>
        {isAdmin ? "Puestos a habilitar" : "Puestos necesarios"}
        <input
          className={styles.input}
          type="number"
          min="1"
          max="100"
          value={requestCount}
          onChange={(event) => setRequestCount(Number(event.target.value))}
          required
        />
      </label>
      <label className={styles.wideField}>
        {isAdmin ? "Nota interna" : "Nota para admin"}
        <input
          className={styles.input}
          value={requestNote}
          onChange={(event) => setRequestNote(event.target.value)}
          placeholder={
            isExtraRequest
              ? "Ejemplo: necesito 4 puestos en total"
              : "Opcional"
          }
        />
      </label>
      <Button variant="primary" type="submit" disabled={loading}>
        {isAdmin ? "Habilitar cupo" : "Solicitar puestos"}
      </Button>
    </form>
  );

  return (
    <section className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Puestos de validacion</h3>
          <p className={styles.subtitle}>
            Accesos temporales para canjear entradas de esta sesion.
          </p>
        </div>
        <div className={styles.counter}>
          <span>
            {occupiedSlots} / {approvedQuota} puestos
          </span>
          <span>{management?.validated_count || 0} validadas</span>
        </div>
      </div>

      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {latestRequest ? (
        <p className={styles.notice}>
          Ultima solicitud: {latestRequest.requested_count} puestos,{" "}
          <strong>{getStatusLabel(latestRequest.status)}</strong>.
          {isAdmin && latestRequest.status === "pending"
            ? " Puedes revisarla desde el apartado admin."
            : ""}
        </p>
      ) : null}

      {latestAdminMessage ? (
        <div className={styles.adminMessage}>
          <strong>Respuesta del admin</strong>
          <p>{latestAdminMessage}</p>
        </div>
      ) : null}

      {!isAdmin && hasPendingRequest ? (
        <p className={styles.helperText}>
          Tu solicitud esta pendiente de revision. Cuando se apruebe, podras
          crear los puestos dentro del cupo autorizado.
        </p>
      ) : null}

      {!isAdmin && hasApprovedQuota ? (
        <p className={styles.helperText}>
          Tienes {availableSlots} puestos disponibles de {approvedQuota} aprobados.
          {hasStations
            ? " Puedes gestionar los enlaces desde las tarjetas de abajo."
            : " Crea los puestos necesarios para generar sus enlaces."}
        </p>
      ) : null}

      {showMainQuotaForm ? renderQuotaForm(false) : null}

      {showExtraQuotaForm ? (
        <details
          className={styles.extraRequest}
          open={showExtraQuotaRequest}
          onToggle={(event) =>
            setShowExtraQuotaRequest(event.currentTarget.open)
          }
        >
          <summary>Solicitar mas validadores</summary>
          <p>
            Indica el numero total exacto de puestos que necesitas para esta
            sesion. La solicitud volvera a quedar pendiente de revision.
          </p>
          {renderQuotaForm(true)}
        </details>
      ) : null}

      {canCreateStations ? (
        <form className={styles.stationForm} onSubmit={createStation}>
          <h4 className={styles.formTitle}>Crear puesto</h4>
          <label className={styles.field}>
            Nombre del puesto
            <input
              className={styles.input}
              value={stationForm.name}
              onChange={(event) =>
                setStationForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              placeholder="Puerta 1"
              required
            />
          </label>
          <label className={styles.field}>
            Responsable
            <input
              className={styles.input}
              value={stationForm.responsible_name}
              onChange={(event) =>
                setStationForm((current) => ({
                  ...current,
                  responsible_name: event.target.value,
                }))
              }
              placeholder="Opcional"
            />
          </label>
          <label className={styles.wideField}>
            Nota interna
            <input
              className={styles.input}
              value={stationForm.notes}
              onChange={(event) =>
                setStationForm((current) => ({
                  ...current,
                  notes: event.target.value,
                }))
              }
              placeholder="Opcional"
            />
          </label>
          <Button variant="primary" type="submit" disabled={loading}>
            Crear y generar enlace
          </Button>
        </form>
      ) : null}

      <div className={styles.stationList}>
        {management?.stations?.map((station) => {
          const issuedLink = issuedLinksByStation[station.id];

          return (
            <article className={styles.stationCard} key={station.id}>
              <div className={styles.stationSummary}>
                <div>
                  <strong>{station.name}</strong>
                  <span>{getStatusLabel(station.status)}</span>
                  {station.responsible_name ? (
                    <small>Responsable: {station.responsible_name}</small>
                  ) : null}
                </div>
                <strong className={styles.validatedCount}>
                  {station.validated_count || 0} validadas
                </strong>
              </div>

              {issuedLink ? (
                <div className={styles.linkBox}>
                  <strong>Enlace de activacion</strong>
                  <p>
                    Compartelo ahora. Si lo pierdes, genera uno nuevo desde esta card.
                  </p>
                  <div className={styles.linkRow}>
                    <input
                      className={styles.linkInput}
                      value={issuedLink.activation_url}
                      readOnly
                    />
                    <Button
                      type="button"
                      onClick={() =>
                        copyIssuedLink(station.id, issuedLink.activation_url)
                      }
                    >
                      {copiedStationId === station.id ? "Copiado" : "Copiar"}
                    </Button>
                  </div>
                </div>
              ) : null}

              <div className={styles.actions}>
                <ButtonLink
                  href={routeTo.validationStationActivity(station.id)}
                >
                  Ver actividad
                </ButtonLink>
                {station.status !== "finished" ? (
                  <>
                    <Button
                      type="button"
                      disabled={loading}
                      onClick={() => regenerateLink(station.id)}
                    >
                      Generar enlace nuevo
                    </Button>
                    {station.status !== "revoked" ? (
                      <Button
                        variant="danger"
                        type="button"
                        disabled={loading}
                        onClick={() => setConfirmStation(station)}
                      >
                        Revocar
                      </Button>
                    ) : null}
                  </>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>

      {management?.stations?.length === 0 ? (
        <p className={styles.empty}>
          Aun no hay puestos creados para esta sesion.
        </p>
      ) : null}

      <ConfirmDialog
        isOpen={!!confirmStation}
        title="Revocar puesto"
        message={`Vas a cerrar el acceso de ${confirmStation?.name || "este puesto"}. El movil dejara de poder validar inmediatamente.`}
        confirmLabel="Revocar"
        tone="danger"
        loading={loading}
        onCancel={() => setConfirmStation(null)}
        onConfirm={revokeStation}
      />
    </section>
  );
}
